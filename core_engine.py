import json
import os
from datetime import datetime
from core.broker_gateway import BrokerGateway
from core.risk_manager import RiskManager
from core.execution_guard import ExecutionGuard
from core.data_validator import DataValidator

# Import all strategy desks
from strategies import stat_arb, market_neutral, global_macro, event_driven, options_vol

def main():
    print("==================================================")
    print("[QuantFund HQ]: Initializing Multi-Strategy Execution & Research Cycle...")
    print(f"Timestamp: {datetime.utcnow().isoformat()} UTC")
    print("==================================================")

    # 1. Initialize Infrastructure & Risk Modules
    broker = BrokerGateway()
    risk_mgr = RiskManager(max_gross_exposure=1.0, max_single_weight=0.03)
    exec_guard = ExecutionGuard(max_adv_pct=0.02)
    validator = DataValidator()

    # Fetch initial account state for reporting
    equity, buying_power = broker.get_account_status()
    print(f"💰 [Account Status]: Equity: ${equity:,.2f} | Buying Power: ${buying_power:,.2f}")

    # 2. Aggregate Signals Across All Strategy Desks
    print("\n🔍 [Strategy Execution]: Polling active alpha desks...")
    raw_signals = []
    
    desks = [
        ("StatArb-Pairs", stat_arb),
        ("MarketNeutral-Factor", market_neutral),
        ("GlobalMacro-Rates", global_macro),
        ("EventDriven-Catalyst", event_driven),
        ("OptionsVol-Regime", options_vol)
    ]

    for desk_name, desk_module in desks:
        try:
            signals = desk_module.generate_signals()
            if signals:
                raw_signals.extend(signals)
        except Exception as e:
            print(f"   ❌ Error executing {desk_name}: {e}")

    print(f"   📊 Total raw signals collected: {len(raw_signals)}")

    # 3. Portfolio-Level Risk & Covariance Optimization
    validated_orders = risk_mgr.evaluate_portfolio(raw_signals)

    # 4. Transaction Cost Analysis (TCA) & Execution Screening
    final_orders = []
    for order in validated_orders:
        symbol = order['symbol']
        # Calculate proposed dollar allocation based on account equity and target weight
        notional = equity * order.get('target_weight', 0.01)
        
        # Screen order against Average Daily Volume (ADV) market impact limits
        passed, reason = exec_guard.validate_execution(symbol, notional, current_price=100.0)
        if passed:
            order['allocation'] = notional
            final_orders.append(order)
        else:
            print(f"   🚫 Order blocked by Execution Guard for {symbol}: {reason}")

    # 5. Execute Approved Orders via Broker Gateway
    if final_orders:
        print(f"\n🚀 [Execution Phase]: Routing {len(final_orders)} validated orders to broker...")
        broker.execute_orders(final_orders)
    else:
        print("\n📭 [Execution Phase]: No orders cleared risk management and execution guards.")

    # 6. Log Performance & State Snapshot
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "equity": equity,
        "buying_power": buying_power,
        "signals_generated": len(raw_signals),
        "orders_executed": len(final_orders),
        "executed_orders": final_orders
    }

    log_file = "performance_log.json"
    history = []
    if os.path.exists(log_file):
        try:
            with open(log_file, "r") as f:
                history = json.load(f)
        except Exception:
            history = []

    history.append(log_entry)
    with open(log_file, "w") as f:
        json.dump(history, f, indent=4)

    print("\n✅ [QuantFund HQ]: Cycle completed successfully. Audit log updated.")
    print("==================================================")

if __name__ == "__main__":
    main()
