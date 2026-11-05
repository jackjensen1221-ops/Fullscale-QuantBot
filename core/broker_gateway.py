import os
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, TakeProfitRequest, StopLossRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass

class BrokerGateway:
    def __init__(self):
        self.api_key = (
            os.getenv("APCA_API_KEY_ID") 
            or os.getenv("ALPACA_API_KEY_ID") 
            or os.getenv("ALPACA_API_KEY")
        )
        self.secret_key = (
            os.getenv("APCA_API_SECRET_KEY") 
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
        print(f"🚀 [Broker Gateway]: Executing {len(orders)} order(s) with automated bracket risk guards...")
        
        for order in orders:
            symbol = order['symbol']
            side = OrderSide.BUY if order['signal'] == 'BUY' else OrderSide.SELL
            allocation = order.get('allocation', 100.0)
            
            try:
                # Estimate current approximate price from allocation or default baseline 
                # (In production, pass current live price from your data frame)
                estimated_price = order.get('current_price', 100.0)
                
                # Define automated risk guard parameters (e.g., 3% Take Profit, 1.5% Stop Loss)
                if side == OrderSide.BUY:
                    tp_price = round(estimated_price * 1.03, 2)
                    sl_price = round(estimated_price * 0.985, 2)
                else:
                    tp_price = round(estimated_price * 0.97, 2)
                    sl_price = round(estimated_price * 1.015, 2)

                # Configure server-side bracket legs
                take_profit_req = TakeProfitRequest(limit_price=tp_price)
                stop_loss_req = StopLossRequest(stop_price=sl_price)

                # Submit composite market order with attached bracket protection
                bracket_req = MarketOrderRequest(
                    symbol=symbol,
                    notional=allocation,
                    side=side,
                    time_in_force=TimeInForce.DAY,
                    order_class=OrderClass.BRACKET,
                    take_profit=take_profit_req,
                    stop_loss=stop_loss_req
                )

                submitted = self.client.submit_order(bracket_req)
                print(f"   ✅ [Protected Order Submitted]: {side.value} {symbol} | Notional: ${allocation:,.2f}")
                print(f"      └─ Guard Rails Set -> Take-Profit: ${tp_price} | Stop-Loss: ${sl_price}")

            except Exception as e:
                print(f"   ❌ [Order Rejection] {symbol}: {e}")
