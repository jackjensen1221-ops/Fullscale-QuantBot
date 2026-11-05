import numpy as np
import pandas as pd
import yfinance as yf

class RiskManager:
    def __init__(self, max_gross_exposure=1.0, max_single_weight=0.03):
        self.max_gross_exposure = max_gross_exposure
        self.max_single_weight = max_single_weight

    def evaluate_portfolio(self, proposed_orders):
        print("🛡️ [Risk Manager]: Running portfolio covariance & exposure checks...")
        
        if not proposed_orders:
            return []

        validated_orders = []
        symbols = [o['symbol'] for o in proposed_orders]
        
        try:
            data = yf.download(symbols, period="1mo", interval="1d", progress=False)['Close']
            if isinstance(data, pd.DataFrame) and not data.empty:
                if isinstance(data.columns, pd.MultiIndex):
                    data.columns = data.columns.get_level_values(0)
                
                returns = data.pct_change().dropna()
                corr_matrix = returns.corr()
                for i, sym1 in enumerate(symbols):
                    for j, sym2 in enumerate(symbols):
                        if i < j and sym1 in corr_matrix.columns and sym2 in corr_matrix.columns:
                            corr_val = corr_matrix.loc[sym1, sym2]
                            if corr_val > 0.85:
                                print(f"   ⚠️ [Risk Warning]: High correlation detected between {sym1} and {sym2} ({corr_val:.2f}).")
        except Exception as e:
            print(f"   ⚠️ Covariance check skipped due to data fetch error: {e}")

        total_proposed_weight = sum([o.get('target_weight', 0.01) for o in proposed_orders])
        scaling_factor = 1.0
        
        if total_proposed_weight > self.max_gross_exposure:
            scaling_factor = self.max_gross_exposure / total_proposed_weight
            print(f"   ⚠️ Gross exposure {total_proposed_weight:.2f} exceeds limit. Scaling orders by {scaling_factor:.2f}.")

        for order in proposed_orders:
            w = order.get('target_weight', 0.01) * scaling_factor
            if w > self.max_single_weight:
                w = self.max_single_weight
            
            order['target_weight'] = w
            validated_orders.append(order)
            print(f"   ✅ Approved: {order['signal']} {order['symbol']} | Strategy: {order.get('strategy')} | Weight: {w:.3f}")

        return validated_orders
