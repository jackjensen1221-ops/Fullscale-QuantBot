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

    def get_open_positions(self):
        """Returns a mapping of active positions and their sides."""
        try:
            positions = self.client.get_all_positions()
            # Returns dictionary like {'MSFT': 'long', 'TSLA': 'short'}
            return {p.symbol: p.side for p in positions}
        except Exception as e:
            print(f"⚠️ [Broker Warning]: Could not fetch active positions: {e}")
            return {}

    def execute_orders(self, orders):
        print(f"🚀 [Broker Gateway]: Executing {len(orders)} order(s) with full long/short support...")
        active_positions = self.get_open_positions()

        for order in orders:
            symbol = order['symbol']
            signal_side = order['signal'] # 'BUY' or 'SELL'
            allocation = order.get('allocation', 100.0)
            estimated_price = order.get('current_price', 100.0)

            try:
                if signal_side == 'BUY':
                    side = OrderSide.BUY
                    # Long Bracket Math: TP above price, SL below price
                    tp_price = round(estimated_price * 1.03, 2)
                    sl_price = round(estimated_price * 0.985, 2)
                    action_label = "LONG BUY"
                
                elif signal_side == 'SELL':
                    # Check if we are holding a long position to close, or opening a short position
                    if symbol in active_positions and active_positions[symbol] == 'long':
                        # If we own it, a SELL signal means closing the long position (standard market order)
                        print(f"   🔄 [Position Close]: Closing existing long position in {symbol}.")
                        req = MarketOrderRequest(
                            symbol=symbol,
                            notional=allocation,
                            side=OrderSide.SELL,
                            time_in_force=TimeInForce.DAY
                        )
                        submitted = self.client.submit_order(req)
                        print(f"   ✅ [Close Order Submitted]: SELL {symbol} | Notional: ${allocation:,.2f}")
                        continue
                    else:
                        # Otherwise, open a new SHORT position
                        side = OrderSide.SELL
                        # Short Bracket Math: TP below price, SL above price
                        tp_price = round(estimated_price * 0.97, 2)
                        sl_price = round(estimated_price * 1.015, 2)
                        action_label = "SHORT SELL"
                else:
                    continue

                # Configure server-side bracket legs
                take_profit_req = TakeProfitRequest(limit_price=tp_price)
                stop_loss_req = StopLossRequest(stop_price=sl_price)

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
                print(f"   ✅ [{action_label} Submitted]: {symbol} | Notional: ${allocation:,.2f}")
                print(f"      └─ Guard Rails Set -> Take-Profit: ${tp_price} | Stop-Loss: ${sl_price}")

            except Exception as e:
                print(f"   ❌ [Order Rejection] {symbol} ({signal_side}): {e}")
