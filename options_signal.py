import requests
import numpy as np
from scipy.stats import norm
from scipy.optimize import brentq
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

API_KEY = "jX67VzkReHUSLGtTyg950ZROCzTB88A4"  # Replace with your Polygon.io API key


def black_scholes(S, K, T, r, sigma, option_type='call'):
    if T <= 0 or sigma <= 0:
        return max(S - K, 0) if option_type == 'call' else max(K - S, 0)
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    if option_type == 'call':
        return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    else:
        return K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)


def greeks(S, K, T, r, sigma, option_type='call'):
    if T <= 0 or sigma <= 0:
        return {}
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    delta = norm.cdf(d1) if option_type == 'call' else norm.cdf(d1) - 1
    gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
    vega = S * norm.pdf(d1) * np.sqrt(T) / 100
    theta_call = (-(S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T)) - r * K * np.exp(-r * T) * norm.cdf(d2)) / 365
    theta_put = (-(S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T)) + r * K * np.exp(-r * T) * norm.cdf(-d2)) / 365
    theta = theta_call if option_type == 'call' else theta_put
    return {'delta': round(delta, 4), 'gamma': round(gamma, 4),
            'vega': round(vega, 4), 'theta': round(theta, 4)}


def implied_vol(market_price, S, K, T, r, option_type='call'):
    try:
        return round(brentq(
            lambda sigma: black_scholes(S, K, T, r, sigma, option_type) - market_price,
            1e-6, 10.0), 4)
    except:
        return None


def get_stock_data(ticker):
    end = (datetime.today() - timedelta(days=2)).strftime('%Y-%m-%d')
    start = (datetime.today() - timedelta(days=90)).strftime('%Y-%m-%d')
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/{start}/{end}?adjusted=true&sort=asc&limit=90&apiKey={API_KEY}"
    r = requests.get(url)
    data = r.json()
    results = data.get('results', [])
    if not results:
        print(f"ERROR: Could not fetch data for {ticker}. Response: {data}")
        return None, None
    closes = [x['c'] for x in results]
    S = closes[-1]
    log_returns = np.diff(np.log(closes))
    hv = np.std(log_returns[-30:]) * np.sqrt(252)
    return round(S, 2), round(hv, 4)


def get_option_price(ticker, strike, expiry, option_type='call'):
    exp = datetime.strptime(expiry, '%Y-%m-%d').strftime('%y%m%d')
    side = 'C' if option_type == 'call' else 'P'
    strike_fmt = str(int(strike * 1000)).zfill(8)
    option_ticker = f"O:{ticker}{exp}{side}{strike_fmt}"
    end = (datetime.today() - timedelta(days=2)).strftime('%Y-%m-%d')
    start = (datetime.today() - timedelta(days=30)).strftime('%Y-%m-%d')
    url = f"https://api.polygon.io/v2/aggs/ticker/{option_ticker}/range/1/day/{start}/{end}?adjusted=true&sort=desc&limit=5&apiKey={API_KEY}"
    r = requests.get(url)
    data = r.json()
    results = data.get('results', [])
    if not results:
        return None, option_ticker
    return results[0]['c'], option_ticker


def vol_surface(S, T, r, hv, strike, option_type='call'):
    offsets = [-20, -10, 0, 10, 20]
    strikes = [strike + o for o in offsets]
    print(f"\n--- Vol Surface (BS Theo across strikes) ---")
    print(f"{'Strike':<10} {'Theo':>8} {'Delta':>8} {'Vega':>8}")
    print("-" * 38)
    for k in strikes:
        theo = black_scholes(S, k, T, r, hv, option_type)
        g = greeks(S, k, T, r, hv, option_type)
        marker = " <-- your strike" if k == strike else ""
        print(f"${k:<9} ${theo:>7.2f} {g.get('delta', 0):>8.4f} {g.get('vega', 0):>8.4f}{marker}")


def scenario_analysis(S, K, T, r, hv, market_price, option_type='call'):
    moves = [-0.15, -0.10, -0.05, 0, 0.05, 0.10, 0.15]
    print(f"\n--- Scenario Analysis (P&L if stock moves) ---")
    print(f"{'Move':<8} {'New Price':>10} {'Option Val':>12} {'P&L':>10}")
    print("-" * 44)
    for m in moves:
        new_S = S * (1 + m)
        new_val = black_scholes(new_S, K, T - 1/52, r, hv, option_type)  # 1 week later
        pnl = new_val - market_price
        marker = " <-- current" if m == 0 else ""
        print(f"{m:>+6.0%}   ${new_S:>9.2f}   ${new_val:>10.2f}   ${pnl:>+9.2f}{marker}")


def analyze_option(ticker, strike, expiry, option_type='call', r=0.05):
    print(f"\nFetching data for {ticker}...")
    S, hv = get_stock_data(ticker)
    if S is None:
        return

    print(f"{ticker} most recent close: ${S:.2f}")
    print(f"30-day historical vol: {hv:.1%}")

    T = (datetime.strptime(expiry, '%Y-%m-%d') - datetime.today()).days / 365
    if T <= 0:
        print("Expiry has passed — choose a future date.")
        return

    market_price, option_ticker = get_option_price(ticker, strike, expiry, option_type)

    if market_price is None:
        print(f"\nCould not fetch market price automatically.")
        manual = input("Enter market price manually (or press Enter to skip): ").strip()
        market_price = float(manual) if manual else None

    theo = black_scholes(S, strike, T, r, hv, option_type)
    g = greeks(S, strike, T, r, hv, option_type)

    print(f"\n{'='*50}")
    print(f"Option: {ticker} {expiry} ${strike} {option_type.upper()}")
    print(f"{'='*50}")
    print(f"BS Theo (HV={hv:.1%}): ${theo:.2f}")

    if market_price:
        iv = implied_vol(market_price, S, strike, T, r, option_type)
        edge = theo - market_price
        print(f"Market price:       ${market_price:.2f}")
        print(f"Implied Vol:        {iv:.1%}" if iv else "Implied Vol:        N/A")
        print(f"Historical Vol:     {hv:.1%}")

    print(f"\nGreeks:")
    for k, v in g.items():
        print(f"  {k}: {v}")

    if market_price:
        print(f"\n{'='*50}")
        if market_price < theo * 0.97:
            print(f"SIGNAL: BUY  -- option is CHEAP by ${abs(edge):.2f}")
            if iv:
                print(f"  IV ({iv:.1%}) < HV ({hv:.1%}) -- vol appears underpriced")
        elif market_price > theo * 1.03:
            print(f"SIGNAL: SELL -- option is RICH by ${abs(edge):.2f}")
            if iv:
                print(f"  IV ({iv:.1%}) > HV ({hv:.1%}) -- vol appears overpriced")
        else:
            print(f"SIGNAL: HOLD -- option is fairly priced")
        print(f"{'='*50}")

        # Scenario analysis
        scenario_analysis(S, strike, T, r, hv, market_price, option_type)
    else:
        print(f"\nSIGNAL: N/A -- no market price provided, BS theo = ${theo:.2f}")

    # Vol surface
    vol_surface(S, T, r, hv, strike, option_type)
    print()


if __name__ == '__main__':
    ticker = input("Enter ticker (e.g. AAPL): ").upper()
    strike = float(input("Enter strike price: "))
    expiry = input("Enter expiry date (YYYY-MM-DD): ")
    option_type = input("Call or put? (call/put): ").lower()
    analyze_option(ticker, strike, expiry, option_type)