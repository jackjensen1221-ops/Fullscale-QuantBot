import os
import time
import logging
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Import custom modules & Alpaca SDK components
from strategies.market_scanner import FullMarketScanner
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import DataFeed

# Load local environment variables from .env
load_dotenv()

# Configure logging to write both to a local file and console output
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("trading_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("CoreEngine")

class NotificationManager:
    """Handles real-time Discord webhook notifications with rich color-coded embeds."""
    def __init__(self):
        self.webhook_url = os.getenv("DISCORD_WEBHOOK_URL")

    def send_alert(self, title: str, message: str, level: str = "INFO"):
        if not self.webhook_url:
            return
        
        color_map = {
            "SUCCESS": 3066993,   # Green
            "ERROR": 15158332,    # Red
            "WARNING": 16776960,  # Yellow
            "INFO": 3447003       # Blue
        }
        
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
            logger.error(f"Failed to dispatch Discord webhook alert: {e}")

class CoreEngineOrchestrator:
    """Main automated trading engine orchestrating scanners, data feeds, strategies, and execution."""
    def __init__(self):
        self.api_key = os.getenv("APCA_API_KEY_ID")
        self.secret_key = os.getenv("APCA_API_SECRET_KEY")
        
        if not self.api_key or not self.secret_key:
            logger.error("Alpaca API credentials missing. Check your environment variables or .env file.")

        # Initialize Alpaca clients (Paper trading mode active)
        self.trading_client = TradingClient(self.api_key, self.secret_key, paper=True)
        self.data_client = StockHistoricalDataClient(self.api_key, self.secret_key)
        
        self.scanner = FullMarketScanner()
        self.notifier = NotificationManager()

    def execute_trade_safe(self, symbol: str, side: OrderSide, qty: int):
        """Submits market orders securely with exception handling and Discord notifications."""
        try:
            order_request = MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=side,
                time_in_force=TimeInForce.DAY,
                order_class=OrderClass.SIMPLE
            )
            order = self.trading_client.submit_order(order_request)
            msg = f"Successfully placed `{side.value}` order for **{qty} share(s)** of **{symbol}**."
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
                # 1. Dynamically scan and pull top market volume leaders
                active_universe = self.scanner.get_dynamic_trading_universe(top_n=5)

                # 2. Define historical query window (skipping the last 16 mins to prevent free-tier SIP restrictions)
                end_date = datetime.now() - timedelta(minutes=16)
                start_date = end_date - timedelta(days=7)

                # 3. Request historical bar data using the free IEX feed
                bars_request = StockBarsRequest(
                    symbol_or_symbols=active_universe,
                    timeframe=TimeFrame.Day,
                    start=start_date,
                    end=end_date,
                    feed=DataFeed.IEX
                )
                bars_response = self.data_client.get_stock_bars(bars_request)

                # Safely extract dictionary mapping from the BarSet object
                bars_dict = bars_response.data

                # 4. Iterate through universe and evaluate strategy criteria
                for symbol in active_universe:
                    logger.info(f"Evaluating strategy metrics for {symbol}...")
                    
                    try:
                        symbol_bars = bars_dict.get(symbol)
                        if symbol_bars and len(symbol_bars) >= 2:
                            latest_bar = symbol_bars[-1]
                            prev_bar = symbol_bars[-2]

                            # Momentum Strategy Rule: Buy if latest daily close exceeds previous close
                            if latest_bar.close > prev_bar.close:
                                logger.info(f"Bullish momentum confirmed for {symbol} (Close: {latest_bar.close} > Prev: {prev_bar.close})")
                                
                                # Check if position is already held to prevent duplicate order stacking
                                try:
                                    position = self.trading_client.get_open_position(symbol)
                                    logger.info(f"Already holding an active position in {symbol}. Skipping order.")
                                except Exception:
                                    # No open position found; safe to execute trade
                                    self.execute_trade_safe(symbol, OrderSide.BUY, qty=1)
                            else:
                                logger.info(f"No signal for {symbol}. Close did not exceed previous bar.")
                        else:
                            logger.warning(f"Insufficient bar data found for {symbol}.")
                    except Exception as inner_e:
                        logger.error(f"Error processing symbol {symbol}: {inner_e}")

                # 5. Sleep cycle before initiating the next check (respecting rate limits)
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
