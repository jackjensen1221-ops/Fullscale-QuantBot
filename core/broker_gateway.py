import os
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, TakeProfitRequest, StopLossRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest

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
        # Data client for real-time bid/ask quote fetching
        self.data_client = StockHistoricalDataClient(self.api_key, self.secret_key)

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
            return {p.symbol: p.side for p in positions}
        except Exception as e:
            print(f"⚠️ [Broker Warning]: Could not fetch active positions: {e}")
            return {}

    def get_live_price(self, symbol: str) -> float:
        """Fetches the actual real-time price from Alpaca's data API."""
        try:
            request_params = StockLatestQuoteRequest(symbol_or_symbols=symbol)
            quote = self.data_client.get_stock_latest_quote(request_params)
            # Use Ask price for buys, Bid price for sells; fallback to ask price
            ask_price = quote[symbol].ask_price
            bid_price = quote[symbol].bid_price
            if ask_price and ask_price > 0:
                return float(ask_price)
            elif bid_price and bid_price > 0:
                return float(bid_price)
        except Exception as e:
            print(f"⚠️ [Price Fetch Warning] {symbol}: {e}. Falling back to order context price.")
        return None

    def execute_orders(self, orders):
        print(f"🚀 [Broker Gateway]: Executing {len(orders)} order(s) with live price quotes...")
        active_positions = self.get_open_positions()

        for order in orders:
            symbol = order['symbol']
            signal_side = order['signal'] # 'BUY' or 'SELL'
            allocation = order.get('allocation', 100.0)

            # Fetch real live market price from Alpaca Data API
            live_price = self.get_live_price(symbol) or order.get('current_price', 100.0)

            try:
                if signal_side == 'BUY':
                    side = OrderSide.BUY
                    # Long Bracket: TP 3% above live price, SL 1.5% below live price
                    tp_price = round(live_price * 1.03, 2)
                    sl_price = round(live_price * 0.985, 2)
                    action_label = "LONG BUY"
                
                elif signal_side == 'SELL':
                    if symbol in active_positions and active_positions[symbol] == 'long':
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
                        side = OrderSide.SELL
                        # Short Bracket: TP 3% below live price, SL 1.5% above live price
                        tp_price = round(live_price * 0.97, 2)
                        sl_price = round(live_price * 1.015, 2)
                        action_label = "SHORT SELL"
                else:
                    continue

                # Server-side bracket request with accurate price targets
                bracket_req = MarketOrderRequest(
                    symbol=symbol,
                    notional=allocation,
                    side=side,
                    time_in_force=TimeInForce.DAY,
                    order_class=OrderClass.BRACKET,
                    take_profit=TakeProfitRequest(limit_price=tp_price),
                    stop_loss=StopLossRequest(stop_price=sl_price)
                )

                submitted = self.client.submit_order(bracket_req)
                print(f"   ✅ [{action_label} Submitted]: {symbol} @ ~${live_price:.2f} | Notional: ${allocation:,.2f}")
                print(f"      └─ Guard Rails -> Take-Profit: ${tp_price} | Stop-Loss: ${sl_price}")

            except Exception as e:
                print(f"   ❌ [Order Rejection] {symbol} ({signal_side}): {e}")
