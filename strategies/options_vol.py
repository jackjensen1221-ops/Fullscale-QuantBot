import numpy as np
import pandas as pd
import yfinance as yf

def generate_signals():
    print("   📉 [Options Vol Desk]: Evaluating realized volatility regimes...")
    signals = []
    # Core benchmark and high-volatility targets for volatility tracking
    assets = ["SPY", "QQQ"]
    
    try:
        data = yf.download(assets, period="3mo", interval="1d", progress=False)['Close']
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
            
        if data.empty:
            return signals

        returns = data.pct_change().dropna()
        
        # Calculate 30-day annualized realized volatility
        rolling_vol = returns.rolling(window=30).std() * np.sqrt(252)
        
        for asset in assets:
            if asset not in rolling_vol.columns:
                continue
                
            vol_series = rolling_vol[asset].dropna()
            if len(vol_series) < 10:
                continue
                
            current_vol = vol_series.iloc[-1]
            mean_vol = vol_series.mean()
            
            # Volatility mean-reversion logic: 
            # If realized vol drops significantly below its historical mean, expect a volatility expansion (Long Volatility proxy)
            # If realized vol spikes way above mean, expect mean reversion contraction.
            z_vol = (current_vol - mean_vol) / vol_series.std() if vol_series.std() > 0 else 0
            
            if z_vol < -1.5:
                # Volatility is unusually compressed; buy exposure anticipating expansion
                signals.append({
                    "symbol": asset,
                    "signal": "BUY",
                    "strategy": "OptionsVol-MeanReversion",
                    "target_weight": 0.015
                })
                print(f"      ⚡ Vol Compression ({asset}): Z-Score {z_vol:.2f}. Allocating Long.")
            elif z_vol > 1.5:
                # Volatility is spiked; fade the spike
                signals.append({
                    "symbol": asset,
                    "signal": "SELL",
                    "strategy": "OptionsVol-MeanReversion",
                    "target_weight": 0.015
                })
                print(f"      ⚡ Vol Spike ({asset}): Z-Score {z_vol:.2f}. Allocating Short/Hedge.")
                
    except Exception as e:
        print(f"      ⚠️ Options Vol Error: {e}")
        
    return signals
