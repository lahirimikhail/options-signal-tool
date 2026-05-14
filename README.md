# Options Signal Tool

A Black-Scholes options pricing tool that pulls live market data and generates buy/sell signals based on theoretical vs market price.

## What it does
- Fetches live stock price and calculates 30-day historical volatility
- Computes Black-Scholes theoretical option price
- Compares to market price and outputs BUY / SELL / HOLD signal
- Calculates all Greeks (delta, gamma, vega, theta)
- Scenario analysis — P&L if stock moves ±5%, ±10%, ±15%
- Vol surface — BS theo across 5 strikes around your target

## How to use
1. Install dependencies: `pip install requests numpy scipy`
2. Add your Polygon.io API key on line 8
3. Run: `python options_signal.py`
4. Enter ticker, strike, expiry date and call/put

## Example output
- Ticker: AAPL
- Strike: $300
- Expiry: 2026-09-19
- BS Theo: $15.77
- Signal: BUY / SELL / HOLD based on market price vs theo

## Dependencies
- Polygon.io free API key (polygon.io)
- Python 3.8+
- requests, numpy, scipy
