import yfinance as yf

def generate_signals():
    print("   🌍 [Global Macro Desk]: Scanning Treasury yield proxies...")
    signals = []
    try:
        df = yf.download("TLT", period="30d", interval="1d", progress=False)
        if not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            current_close = float(df['Close'].iloc[-1])
            sma_20 = float(df['Close'].rolling(window=20).mean().iloc[-1])
            
            if current_close > sma_20:
                signals.append({"symbol": "TLT", "signal": "BUY", "strategy": "GlobalMacro-Rates", "target_weight": 0.025})
            else:
                signals.append({"symbol": "TLT", "signal": "SELL", "strategy": "GlobalMacro-Rates", "target_weight": 0.025})
    except Exception as e:
        print(f"      ⚠️ Global Macro Error: {e}")
    return signals
