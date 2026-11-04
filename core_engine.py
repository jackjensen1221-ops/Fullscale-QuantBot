import os
import sys
import json
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from core.risk_manager import RiskManager
from core.broker_gateway import BrokerGateway

from strategies import stat_arb, market_neutral, global_macro, event_driven, options_vol

def main():
    print("🏢 [QuantFund HQ]: Initializing Multi-Strategy Execution & Research Cycle...")
    
    broker = BrokerGateway()
    risk_manager = RiskManager(broker)
    
    portfolio_equity, _ = broker.get_account_status()
    print(f"💰 [Capital Base]: ${portfolio_equity:,.2f} under management.")

    all_signals = []
    print("\n📊 [Desks Activation]: Running strategy modules...")
    try:
        all_signals.extend(stat_arb.generate_signals())
        all_signals.extend(market_neutral.generate_signals())
        all_signals.extend(global_macro.generate_signals())
        all_signals.extend(event_driven.generate_signals())
        all_signals.extend(options_vol.generate_signals())
    except Exception as e:
        print(f"⚠️ [Desk Execution Warning]: Error during signal generation: {e}")

    print(f"📈 [Alpha Aggregation]: Collected {len(all_signals)} total candidate signals across all desks.")

    approved_orders = risk_manager.evaluate_and_clear(all_signals, portfolio_equity)

    if approved_orders:
        print(f"🚀 [Execution Gateway]: Submitting {len(approved_orders)} cleared orders to broker...")
        broker.execute_orders(approved_orders)
    else:
        print("📭 [Execution Gateway]: No orders cleared risk management thresholds.")

    audit_data = {
        "timestamp": str(datetime.now()),
        "equity": portfolio_equity,
        "signals_processed": len(all_signals),
        "orders_executed": len(approved_orders)
    }
    
    log_file = "performance_log.json"
    history = []
    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            try:
                history = json.load(f)
            except json.JSONDecodeError:
                history = []
    history.append(audit_data)
    with open(log_file, "w") as f:
        json.dump(history, f, indent=4)

    print("🏢 [QuantFund HQ]: Cycle successfully completed.")

if __name__ == "__main__":
    main()
