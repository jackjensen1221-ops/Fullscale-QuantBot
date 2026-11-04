import pandas as pd
import yfinance as yf

def generate_signals():
    print("   📰 [Event-Driven Desk]: Scanning catalyst & earnings volume anomalies...")
    signals = []
    # Watchlist of high-beta / catalyst-prone equities
    watchlist = ["NVDA", "TSLA", "META", "NFLX"]
    
    try:
        data = yf.download(watchlist, period="10d", interval="1d", progress=False)['Volume']
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
            
        if data.empty:
            return signals

        for symbol in watchlist:
            if symbol not in data.columns:
                continue
                
            vol_series = data[symbol]
            recent_vol = vol_series.iloc[-1]
            avg_vol = vol_series.iloc[:-1].mean()
            
            # Detect significant volume spike (> 2x average volume) indicating catalyst event
            if avg_vol > 0 and (recent_vol / avg_vol) > 2.0:
                # Check recent price momentum to determine breakout direction
                price_data = yf.download(symbol, period="5d", interval="1d", progress=False)['Close']
                if isinstance(price_data, pd.DataFrame):
                    price_data = price_data.iloc[:, 0]
                    
                if len(price_data) >= 2:
                    returns = price_data.pct_change().iloc[-1]
                    if returns > 0:
                        signals.append({
                            "symbol": symbol,
                            "signal": "BUY",
                            "strategy": "EventDriven-VolumeBreakout",
                            "target_weight": 0.02
                        })
                        print(f"      🎯 Event Catalyst Found ({symbol}): Volume spike detected (+{((recent_vol/avg_vol)-1)*100:.1f}%). Going LONG.")
                    else:
                        signals.append({
                            "symbol": symbol,
                            "signal": "SELL",
                            "strategy": "EventDriven-VolumeBreakout",
                            "target_weight": 0.02
                        })
                        print(f"      🎯 Event Catalyst Found ({symbol}): Volume spike with downward pressure. Going SHORT.")
                        
    except Exception as e:
        print(f"      ⚠️ Event-Driven Error: {e}")
        
    return signals
