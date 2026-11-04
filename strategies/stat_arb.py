import pandas as pd
import yfinance as yf

def generate_signals():
    print("   🔬 [Stat Arb Desk]: Running cointegration & spread models...")
    signals = []
    pair = ["KO", "PEP"]
    try:
        data = yf.download(pair, period="6mo", interval="1d", progress=False)['Close']
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        if len(data) < 30:
            return signals

        spread = data['KO'] - (1.2 * data['PEP'])
        z_score = (spread.iloc[-1] - spread.mean()) / spread.std()

        if z_score > 2.0:
            signals.append({"symbol": "KO", "signal": "SELL", "strategy": "StatArb-Pairs", "target_weight": 0.015})
            signals.append({"symbol": "PEP", "signal": "BUY", "strategy": "StatArb-Pairs", "target_weight": 0.015})
        elif z_score < -2.0:
            signals.append({"symbol": "KO", "signal": "BUY", "strategy": "StatArb-Pairs", "target_weight": 0.015})
            signals.append({"symbol": "PEP", "signal": "SELL", "strategy": "StatArb-Pairs", "target_weight": 0.015})
    except Exception as e:
        print(f"      ⚠️ Stat Arb Error: {e}")
    return signals
