import pandas as pd
import yfinance as yf

def generate_signals():
    print("   ⚖️ [Market Neutral Desk]: Evaluating sector factor z-scores...")
    signals = []
    universe = ["AAPL", "MSFT", "GOOGL", "AMZN"]
    try:
        data = yf.download(universe, period="30d", interval="1d", progress=False)['Close']
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        returns = data.pct_change().mean()
        
        ranked = returns.sort_values()
        if len(ranked) >= 2:
            shorts_symbol = ranked.index[0]
            long_symbol = ranked.index[-1]
            
            signals.append({"symbol": long_symbol, "signal": "BUY", "strategy": "MarketNeutral-Factor", "target_weight": 0.02})
            signals.append({"symbol": shorts_symbol, "signal": "SELL", "strategy": "MarketNeutral-Factor", "target_weight": 0.02})
    except Exception as e:
        print(f"      ⚠️ Market Neutral Error: {e}")
    return signals
