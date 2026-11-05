import os
import json
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

class ResearchEngine:
    def __init__(self):
        self.intel_file = "market_intel.json"

    def run_daily_research(self):
        print("🧠 [Research Engine]: Gathering daily market intelligence & regime data...")
        
        intel = {
            "timestamp": datetime.utcnow().isoformat(),
            "market_regime": self._analyze_market_regime(),
            "catalysts": self._scan_volume_catalysts(),
            "volatility_state": self._analyze_volatility_regime()
        }

        # Save research brief to disk for strategy desks to consume
        with open(self.intel_file, "w") as f:
            json.dump(intel, f, indent=4)
            
        print(f"✅ [Research Engine]: Market intelligence compiled and saved to {self.intel_file}.")
        return intel

    def _analyze_market_regime(self):
        """Determines broader market trend (Risk-On vs Risk-Off) using SPY & TLT."""
        try:
            data = yf.download(["SPY", "TLT"], period="3mo", interval="1d", progress=False)['Close']
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
                
            spy_return = (data['SPY'].iloc[-1] / data['SPY'].iloc[-20]) - 1
            tlt_return = (data['TLT'].iloc[-1] / data['TLT'].iloc[-20]) - 1
            
            regime = "RISK_ON" if spy_return > 0 else "RISK_OFF"
            print(f"   📊 Macro Regime Identified: {regime} (SPY 20d: {spy_return*100:.2f}%)")
            return {
                "regime": regime,
                "spy_20d_return": float(spy_return),
                "tlt_20d_return": float(tlt_return)
            }
        except Exception as e:
            print(f"   ⚠️ Regime analysis error: {e}")
            return {"regime": "NEUTRAL", "spy_20d_return": 0.0, "tlt_20d_return": 0.0}

    def _scan_volume_catalysts(self):
        """Scans liquid tech/growth equities for abnormal pre-market/daily volume spikes."""
        watchlist = ["NVDA", "TSLA", "META", "AAPL", "MSFT", "AMZN", "NFLX"]
        catalysts = []
        
        try:
            data = yf.download(watchlist, period="5d", interval="1d", progress=False)['Volume']
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
                
            for symbol in watchlist:
                if symbol not in data.columns:
                    continue
                vol = data[symbol].dropna()
                if len(vol) < 3:
                    continue
                
                recent = vol.iloc[-1]
                avg = vol.iloc[:-1].mean()
                if avg > 0 and (recent / avg) > 2.0:
                    catalysts.append({
                        "symbol": symbol,
                        "volume_surge_pct": float(((recent / avg) - 1) * 100)
                    })
            print(f"   📰 Found {len(catalysts)} volume catalyst anomaly tickers.")
        except Exception as e:
            print(f"   ⚠️ Catalyst scan error: {e}")
            
        return catalysts

    def _analyze_volatility_regime(self):
        """Evaluates market volatility status using SPY realized volatility."""
        try:
            data = yf.download("SPY", period="1mo", interval="1d", progress=False)['Close']
            if isinstance(data, pd.DataFrame):
                data = data.iloc[:, 0]
            returns = data.pct_change().dropna()
            realized_vol = float(returns.std() * np.sqrt(252))
            
            state = "HIGH_VOL" if realized_vol > 0.20 else "LOW_VOL"
            print(f"   📉 Volatility State: {state} (Annualized Realized Vol: {realized_vol*100:.1f}%)")
            return {"state": state, "realized_vol": realized_vol}
        except Exception as e:
            print(f"   ⚠️ Volatility regime error: {e}")
            return {"state": "NORMAL", "realized_vol": 0.15}

if __name__ == "__main__":
    engine = ResearchEngine()
    engine.run_daily_research()
