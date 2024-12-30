import streamlit as st
import requests
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib.dates import date2num, DateFormatter

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

# Calculate EMA and Fibonacci levels
def calculate_indicators(close_prices, high, low):
    def ema(prices, span):
        multiplier = 2 / (span + 1)
        ema_values = [prices[0]]
        for price in prices[1:]:
            ema_values.append((price - ema_values[-1]) * multiplier + ema_values[-1])
        return ema_values

    ema9 = ema(close_prices, 9)
    ema20 = ema(close_prices, 20)

    diff = high - low
    fib_levels = {
        "0%": high,
        "23.6%": high - 0.236 * diff,
        "38.2%": high - 0.382 * diff,
        "50%": high - 0.5 * diff,
        "61.8%": high - 0.618 * diff,
        "100%": low,
    }

    return ema9, ema20, fib_levels

# Plot candlestick chart
def plot_candlestick(ohlc_data, ema9, ema20, fib_levels, symbol):
    fig, ax = plt.subplots(figsize=(10, 6))

    for row in ohlc_data:
        date, open_, high, low, close = row
        color = "green" if close >= open_ else "red"
        ax.plot([date, date], [low, high], color="black")
        ax.plot([date, date], [open_, close], color=color, linewidth=4)

    dates = [row[0] for row in ohlc_data]
    ax.plot(dates, ema9, label="EMA 9", color="blue", linewidth=1.5)
    ax.plot(dates, ema20, label="EMA 20", color="orange", linewidth=1.5)

    for (level, price), color in zip(fib_levels.items(), ["red", "green", "blue", "purple", "orange", "black"]):
        ax.axhline(y=price, color=color, linestyle="--", label=f"Fib {level}", alpha=0.7)

    ax.xaxis.set_major_formatter(DateFormatter('%m/%d/%y'))
    ax.set_title(f"{symbol} Candlestick Chart")
    ax.set_xlabel("Date")
    ax.set_ylabel("Price")
    ax.legend()
    st.pyplot(fig)

# Streamlit UI
st.title("Stock Market Analysis App")

symbol = st.text_input("Enter Stock Symbol (e.g., AAPL):").upper()
if symbol:
    ohlc_data, close_prices, high, low = fetch_stock_data(symbol)

    if ohlc_data:
        ema9, ema20, fib_levels = calculate_indicators(close_prices, high, low)
        st.subheader(f"Data for {symbol}")
        st.write(f"Current Price: {close_prices[-1]}")
        plot_candlestick(ohlc_data, ema9, ema20, fib_levels, symbol)
    else:
        st.warning(f"No data available for {symbol}")
