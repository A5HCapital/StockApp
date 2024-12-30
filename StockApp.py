import streamlit as st
import requests
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib.dates import date2num, DateFormatter
from matplotlib.ticker import MaxNLocator

API_KEY = "8uK6hchgdm_LgpL8nUa_PQyQ9ZTYS_5Z"  # Replace with your Polygon.io API key

# Fetch stock data from Polygon.io API
def fetch_stock_data(symbol):
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")

        url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/{start_date_str}/{end_date_str}?adjusted=true&sort=asc&apiKey={API_KEY}"
        response = requests.get(url)

        if response.status_code != 200:
            st.error(f"Error fetching data: {response.status_code}")
            return None, None, None, None

        data = response.json()
        if "results" not in data or not data["results"]:
            st.warning("No data returned for this symbol.")
            return None, None, None, None

        ohlc_data = []
        close_prices = []
        high, low = float('-inf'), float('inf')
        for item in data["results"]:
            date = date2num(datetime.fromtimestamp(item["t"] / 1000))
            open_, high_, low_, close = item["o"], item["h"], item["l"], item["c"]
            ohlc_data.append([date, open_, high_, low_, close])
            close_prices.append(close)
            high = max(high, high_)
            low = min(low, low_)

        return ohlc_data, close_prices, high, low
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return None, None, None, None

# RSI Calculation Function
def rsi(prices, period=14):
    # Ensure there are enough data points
    if len(prices) < period + 1:
        return [None] * len(prices)

    # Calculate daily gains and losses
    gains, losses = [], []
    for i in range(1, len(prices)):
        change = prices[i] - prices[i - 1]
        gains.append(max(change, 0))  # Only positive changes
        losses.append(abs(min(change, 0)))  # Only negative changes

    # Initial average gain and loss
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    # Validate gains/losses lengths before indexing
    if len(gains) < period or len(losses) < period:
        return [None] * len(prices)

    # Calculate RSI
    rsi_values = []
    for i in range(period, len(prices)):
        if i < len(gains):  # Ensure valid index
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        if i < len(losses):  # Ensure valid index
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        rs = avg_gain / avg_loss if avg_loss != 0 else 0
        rsi = 100 - (100 / (1 + rs))
        rsi_values.append(rsi)

    # Pad the initial values with None to match the length of the input prices
    return [None] * period + rsi_values

# Calculate EMA, RSI, and Fibonacci levels
def calculate_indicators(close_prices, high, low):
    def ema(prices, span):
        multiplier = 2 / (span + 1)
        ema_values = [prices[0]]
        for price in prices[1:]:
            ema_values.append((price - ema_values[-1]) * multiplier + ema_values[-1])
        return ema_values

    ema9 = ema(close_prices, 9)
    ema20 = ema(close_prices, 20)
    rsi_values = rsi(close_prices)

    diff = high - low
    fib_levels = {
        "0%": high,
        "23.6%": high - 0.236 * diff,
        "38.2%": high - 0.382 * diff,
        "50%": high - 0.5 * diff,
        "61.8%": high - 0.618 * diff,
        "100%": low,
    }

    return ema9, ema20, rsi_values, fib_levels

# Determine Momentum as Bullish or Bearish
def calculate_momentum_and_projection(close_prices, ema9, ema20):
    momentum_value = close_prices[-1] - close_prices[-10] if len(close_prices) >= 10 else 0
    momentum = "Bullish" if momentum_value > 0 else "Bearish"
    ema_diff = ema9[-1] - ema20[-1]
    projected_price = close_prices[-1] + ema_diff
    return momentum, projected_price

# Plot candlestick chart with RSI
def plot_candlestick(ohlc_data, ema9, ema20, rsi_values, fib_levels, symbol):
    fig, (ax, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True, gridspec_kw={'height_ratios': [3, 1]})

    # Candlestick plotting
    for row in ohlc_data:
        date, open_, high, low, close = row
        color = "green" if close >= open_ else "red"
        ax.plot([date, date], [low, high], color="black")
        ax.plot([date, date], [open_, close], color=color, linewidth=4)

    dates = [row[0] for row in ohlc_data]
    ax.plot(dates, ema9, label="EMA 9", color="blue", linewidth=1.5)
    ax.plot(dates, ema20, label="EMA 20", color="orange", linewidth=1.5)

    # Fibonacci levels
    for (level, price), color in zip(fib_levels.items(), ["red", "green", "blue", "purple", "orange", "black"]):
        ax.axhline(y=price, color=color, linestyle="--", label=f"Fib {level}", alpha=0.7)

    # Format candlestick x-axis
    ax.xaxis.set_major_formatter(DateFormatter('%m/%d/%y'))
    ax.xaxis.set_major_locator(MaxNLocator(6))  # Limit to 6 ticks on x-axis
    ax.tick_params(axis='x', rotation=45)

    ax.set_title(f"{symbol} Candlestick Chart")
    ax.set_ylabel("Price")
    ax.legend()

    # RSI plot
    ax2.plot(dates[-len(rsi_values):], rsi_values, label="RSI", color="purple")
    ax2.axhline(y=70, color="red", linestyle="--", label="Overbought (70)")
    ax2.axhline(y=30, color="green", linestyle="--", label="Oversold (30)")

    ax2.set_title("RSI (Relative Strength Index)")
    ax2.set_xlabel("Date")
    ax2.set_ylabel("RSI Value")
    ax2.legend()

    # Adjust layout to prevent overlap
    plt.tight_layout()

    st.pyplot(fig)

# Streamlit UI
st.title("Stock Market Analysis App")

symbol = st.text_input("Enter Stock Symbol (e.g., AAPL):").upper()
if symbol:
    ohlc_data, close_prices, high, low = fetch_stock_data(symbol)

    if ohlc_data:
        ema9, ema20, rsi_values, fib_levels = calculate_indicators(close_prices, high, low)
        momentum, projected_price = calculate_momentum_and_projection(close_prices, ema9, ema20)

        # Format prices as currency
        current_price = f"${close_prices[-1]:,.2f}"
        projected_price = f"${projected_price:,.2f}"

        # Display metrics in a clean table
        st.subheader(f"Data for {symbol}")
        data = {
            "Metric": ["Current Price", "Projected Price", "Momentum"],
            "Value": [current_price, projected_price, momentum]
        }
        st.dataframe(data)

        # Plot candlestick chart with RSI
        plot_candlestick(ohlc_data, ema9, ema20, rsi_values, fib_levels, symbol)
    else:
        st.warning(f"No data available for {symbol}")
