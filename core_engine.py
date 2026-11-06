import os
import time
import logging
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Import your custom modules
from strategies.market_scanner import FullMarketScanner
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import DataFeed  # <-- Required for free/paper IEX data feed

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("trading_bot.log"), logging.StreamHandler()]
)
logger = logging.getLogger("CoreEngine")

class NotificationManager:
    """Handles real-time Discord webhook notifications."""
    def __init__(self):
        self.webhook_url = os.getenv("DISCORD_WEBHOOK_URL")

    def send_alert(self, title: str, message: str, level: str = "INFO"):
        if not self.webhook_url:
            return
        color_map = {"SUCCESS": 3066993, "ERROR": 15158332, "WARNING": 16776960, "INFO": 3447003}
        payload = {
            "embeds": [{
                "title": f"[{level.upper()}] {title}",
                "description": message,
                "color": color_map.get(level.upper(), 3447003),
                "timestamp": datetime.utcnow().isoformat()
            }]
        }
        try:
            requests.post(self.webhook_url, json=payload, timeout=5)
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")

class CoreEngineOrchestrator:
    def __init__(self):
        self.api_key = os.getenv("APCA_API_KEY_ID")
        self.secret_key = os.getenv("APCA_API_SECRET_KEY")
        
        self.trading_client = TradingClient(self.api_key, self.secret_key, paper=True)
        self.data_client = StockHistoricalDataClient(self.api_key, self.secret_key)
        self.scanner = FullMarketScanner()
        self.notifier = NotificationManager()

    def execute_trade_safe(self, symbol: str, side: OrderSide, qty: int):
        """Executes market orders safely with error handling and Discord alerts."""
        try:
            order_request = MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=side,
                time_in_force=TimeInForce.DAY,
                order_class=OrderClass.SIMPLE
            )
            order = self.trading_client.submit_order(order_request)
            msg = f"Successfully placed `{side.value}` order for **{qty} shares** of **{symbol}**."
            logger.info(msg)
            self.notifier.send_alert("Order Executed", msg, level="SUCCESS")
        except Exception as e:
            err_msg = f"Failed to submit `{side.value}` order for {symbol}: {str(e)}"
            logger.error(err_msg)
            self.notifier.send_alert("Execution Failure", err_msg, level="ERROR")

    def run(self):
        self.notifier.send_alert("Core Engine Initialized", "Quantitative trading engine started successfully.", level="INFO")
        logger.info("Core engine operational. Entering primary execution loop...")

        while True:
            try:
                # 1. Dynamically pull top market volume leaders
                active_universe = self.scanner.get_dynamic_trading_universe(top_n=5)

                # 2. Fetch historical bar data using the free IEX feed
                end_date = datetime.now() - timedelta(minutes=16) # Avoid real-time block
                start_date = end_date - timedelta(days=5)

                bars_request = StockBarsRequest(
                    symbol_or_symbols=active_universe,
                    timeframe=TimeFrame.Day,
                    start=start_date,
                    end=end_date,
                    feed=DataFeed.IEX  # <-- Fixes the subscription error on paper accounts
                )
                bars_response = self.data_client.get_stock_bars(bars_request)

                # 3. Iterate through universe and evaluate strategy criteria
                for symbol in active_universe:
                    logger.info(f"Evaluating strategy metrics for {symbol}...")
                    
                    symbol_bars = bars_response.get(symbol)
                    if symbol_bars and len(symbol_bars) >= 2:
                        latest_bar = symbol_bars[-1]
                        prev_bar = symbol_bars[-2]

                        # Momentum Rule: Buy if latest daily close exceeds previous close
                        if latest_bar.close > prev_bar.close:
                            logger.info(f"Bullish momentum confirmed for {symbol} (Close: {latest_bar.close} > Prev: {prev_bar.close})")
                            self.execute_trade_safe(symbol, OrderSide.BUY, qty=1)
                            break 
                        else:
                            logger.info(f"No signal for {symbol}. Close did not exceed previous bar.")

                # 4. Sleep cycle before next check
                logger.info("Cycle complete. Sleeping for 300 seconds...")
                time.sleep(300)

            except Exception as e:
                err_msg = f"Critical error in core engine loop: {str(e)}"
                logger.error(err_msg)
                self.notifier.send_alert("Loop Exception", err_msg, level="ERROR")
                time.sleep(60)

if __name__ == "__main__":
    engine = CoreEngineOrchestrator()
    engine.run()
