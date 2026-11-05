import yfinance as yf
import pandas as pd

class ExecutionGuard:
    def __init__(self, max_adv_pct=0.02):
        self.max_adv_pct = max_adv_pct

    def validate_execution(self, symbol, notional_amount, current_price):
        try:
            ticker_data = yf.download(symbol, period="5d", interval="1d", progress=False)
            if ticker_data.empty:
                return False, "No volume data available"
                
            volume = ticker_data['Volume']
            if isinstance(volume, pd.DataFrame):
                volume = volume.iloc[:, 0]
                
            avg_daily_volume = volume.mean()
            avg_daily_dollar_volume = avg_daily_volume * current_price
            max_allowed_notional = avg_daily_dollar_volume * self.max_adv_pct
            
            if notional_amount > max_allowed_notional:
                print(f"   ❌ [TCA Rejection] {symbol}: Order size ${notional_amount:,.2f} exceeds 2% ADV limit (${max_allowed_notional:,.2f}).")
                return False, "Exceeds ADV threshold"
                
            print(f"   ✅ [TCA Clear] {symbol}: Order size within safe market impact limits.")
            return True, "Passed TCA"
            
        except Exception as e:
            print(f"   ⚠️ [TCA Warning] {symbol}: Could not verify ADV ({e}). Proceeding with caution.")
            return True, "Bypassed on error"
