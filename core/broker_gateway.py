import os
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

class BrokerGateway:
    def __init__(self):
        self.api_key = (
            os.getenv("APCA_API_KEY_ID") 
            or os.getenv("ALPACA_API_KEY_ID") 
            or os.getenv("ALPACA_API_KEY")
        )
        self.secret_key = (
            os.getenv("APCA_SECRET_KEY") 
            or os.getenv("ALPACA_SECRET_KEY") 
            or os.getenv("ALPACA_SECRET")
        )
        self.client = TradingClient(self.api_key, self.secret_key, paper=True)

    def get_account_status(self):
        try:
            account = self.client.get_account()
            return float(account.equity), float(account.buying_power)
        except Exception as e:
            print(f"❌ [Broker Error]: Failed to fetch account status: {e}")
            return 0.0, 0.0

    def execute_orders(self, orders):
        print(f"🚀 [Broker Gateway]: Executing {len(orders)} order(s)...")
        for order in orders:
            symbol = order['symbol']
            side = OrderSide.BUY if order['signal'] == 'BUY' else OrderSide.SELL
            try:
                req = MarketOrderRequest(
                    symbol=symbol,
                    notional=order.get('allocation', 100.0),
                    side=side,
                    time_in_force=TimeInForce.DAY
                )
                submitted = self.client.submit_order(req)
                print(f"   ✅ [Order Submitted]: {side.value} {symbol} | Notional: ${order.get('allocation', 100.0):.2f} | ID: {submitted.id}")
            except Exception as e:
                print(f"   ❌ [Order Rejection] {symbol}: {e}")
