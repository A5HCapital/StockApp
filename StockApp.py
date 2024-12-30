import ui
import requests
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib.dates import date2num, DateFormatter
import io

API_KEY = "8uK6hchgdm_LgpL8nUa_PQyQ9ZTYS_5Z"  # Your Polygon.io API key

# Helper Functions
def fetch_stock_data(symbol):
    """Fetch stock data using Polygon.io API."""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")

        url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/{start_date_str}/{end_date_str}?adjusted=true&sort=asc&apiKey={API_KEY}"
        print(f"Requesting URL: {url}")

        response = requests.get(url)
        print(f"HTTP Status Code: {response.status_code}")

        if response.status_code != 200:
            print(f"Error: HTTP {response.status_code} - {response.text}")
            return None, None, None, None

        data = response.json()
        if "results" not in data or not data["results"]:
            print("No data returned for this symbol.")
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
        print(f"Error fetching data: {e}")
        return None, None, None, None

def calculate_indicators(close_prices, high, low):
    """Calculate EMA and Fibonacci levels."""
    def ema(prices, span):
        multiplier = 2 / (span + 1)
        ema_values = [prices[0]]
        for price in prices[1:]:
            ema_values.append((price - ema_values[-1]) * multiplier + ema_values[-1])
        return ema_values

    ema9 = ema(close_prices, 9)
    ema20 = ema(close_prices, 20)

    # Calculate Fibonacci levels
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

def plot_candlestick(ohlc_data, ema9, ema20, fib_levels, symbol):
    """Plot candlestick chart with EMA and Fibonacci levels."""
    fig, ax = plt.subplots(figsize=(10, 6))

    # Plot candlesticks
    for row in ohlc_data:
        date, open_, high, low, close = row
        color = "green" if close >= open_ else "red"
        ax.plot([date, date], [low, high], color="black")
        ax.plot([date, date], [open_, close], color=color, linewidth=4)

    # Plot EMA indicators
    dates = [row[0] for row in ohlc_data]
    ax.plot(dates, ema9, label="EMA 9", color="blue", linewidth=1.5)
    ax.plot(dates, ema20, label="EMA 20", color="orange", linewidth=1.5)

    # Plot Fibonacci levels with different colors
    fib_colors = ["red", "green", "blue", "purple", "orange", "black"]
    for (level, price), color in zip(fib_levels.items(), fib_colors):
        ax.axhline(y=price, color=color, linestyle="--", label=f"Fib {level}", alpha=0.7)

    # Format x-axis dates to mm/dd/yy
    ax.xaxis.set_major_formatter(DateFormatter('%m/%d/%y'))

    ax.set_title(f"{symbol} Candlestick Chart with EMA and Fibonacci")
    ax.set_xlabel("Date")
    ax.set_ylabel("Price")
    ax.legend()
    fig.autofmt_xdate()

    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    img_data = buf.read()
    buf.close()
    plt.close(fig)
    return img_data

def project_price(close_prices):
    """Project price using 5-day moving average."""
    if len(close_prices) < 5:
        return "N/A"
    return round(sum(close_prices[-5:]) / 5, 2)

def analyze_momentum(close_prices):
    """Analyze momentum (simple trend analysis)."""
    if len(close_prices) < 2:
        return "N/A"
    return "Bullish" if close_prices[-1] > close_prices[-2] else "Bearish"

def dismiss_keyboard(sender):
    """Dismiss the keyboard."""
    sender.end_editing()

# UI Components
def fetch_and_display(sender):
    symbol = sender.superview['symbol_field'].text.upper()
    if not symbol or not symbol.isalnum():
        sender.superview['result_label'].text = "Invalid stock symbol. Please enter a valid symbol."
        return

    sender.superview['result_label'].text = "Fetching data..."
    ohlc_data, close_prices, high, low = fetch_stock_data(symbol)

    if not ohlc_data:
        sender.superview['result_label'].text = f"No data found for symbol: {symbol}"
        return

    # Calculate indicators
    ema9, ema20, fib_levels = calculate_indicators(close_prices, high, low)

    # Plot candlestick chart
    img_data = plot_candlestick(ohlc_data, ema9, ema20, fib_levels, symbol)

    # Display the chart in the app
    img_view = sender.superview['chart_view']
    img_view.image = ui.Image.from_data(img_data)

    # Analyze data
    current_price = close_prices[-1] if close_prices else "N/A"
    projected_price = project_price(close_prices)
    momentum = analyze_momentum(close_prices)

    # Update the table with Current Price, Projected Price, and Momentum
    table_label = sender.superview['table_label']
    table_label.text = (f"Current Price: {current_price}\n"
                        f"Projected Price: {projected_price}\n"
                        f"Momentum: {momentum}")
    table_label.hidden = False

    # Update the result label
    sender.superview['result_label'].text = f"Data for {symbol} displayed successfully."

# Main UI
view = ui.View()
view.background_color = "white"
view.name = "Stock Market App"

# Stock symbol input
symbol_field = ui.TextField(frame=(10, 10, 300, 40), placeholder="Enter stock symbol (e.g., AAPL)")
symbol_field.name = "symbol_field"
symbol_field.action = dismiss_keyboard  # Attach the dismiss action
view.add_subview(symbol_field)

# Fetch button
fetch_button = ui.Button(frame=(10, 60, 100, 40), title="Fetch Data")
fetch_button.action = fetch_and_display
view.add_subview(fetch_button)

# Result label
result_label = ui.Label(frame=(10, 110, 300, 40), text="", number_of_lines=0)
result_label.name = "result_label"
view.add_subview(result_label)

# Chart view
chart_view = ui.ImageView(frame=(10, 160, 350, 300))
chart_view.name = "chart_view"
view.add_subview(chart_view)

# Table view for Current Price, Projected Price, and Momentum
table_label = ui.Label(frame=(10, 470, 350, 80), text="", number_of_lines=0, alignment=ui.ALIGN_CENTER)
table_label.name = "table_label"
table_label.background_color = "lightgray"  # For visibility
view.add_subview(table_label)

# Present the app
view.present("sheet")
