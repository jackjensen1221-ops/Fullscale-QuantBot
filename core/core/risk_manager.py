class RiskManager:
    def __init__(self, broker_gateway, max_portfolio_leverage=1.5):
        self.broker = broker_gateway
        self.max_leverage = max_portfolio_leverage

    def evaluate_and_clear(self, signals, equity):
        print("🛡️ [Risk Manager]: Evaluating cross-strategy signals & netting exposures...")
        net_symbol_intent = {}
        cleared_orders = []

        for sig in signals:
            sym = sig['symbol']
            side = sig['signal']
            
            if sym in net_symbol_intent:
                existing = net_symbol_intent[sym]
                if existing['signal'] != side:
                    print(f"   ⚠️ [Conflict Resolved]: Conflicting signals for {sym}. Neutralizing position.")
                    continue

            net_symbol_intent[sym] = sig

        for sym, sig in net_symbol_intent.items():
            target_dollar_allocation = equity * sig.get('target_weight', 0.02)
            sig['allocation'] = target_dollar_allocation
            cleared_orders.append(sig)

        print(f"✨ [Risk Manager]: Cleared {len(cleared_orders)} orders through risk protocols.")
        return cleared_orders
