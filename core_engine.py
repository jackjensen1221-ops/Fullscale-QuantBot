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
from alpaca.data.enums import DataFeed

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

    def execute_trade_safe(self, symbol: symbol := "", side: OrderSide = OrderSide.BUY, qty: int = 1):
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
                end_date = datetime.now() - timedelta(minutes=16)
                start_date = end_date - timedelta(days=7)

                bars_request = StockBarsRequest(
                    symbol_or_symbols=active_universe,
                    timeframe=TimeFrame.Day,
                    start=start_date,
                    end=end_date,
                    feed=DataFeed.IEX
                )
                bars_response = self.data_client.get_stock_bars(bars_request)

                # Convert BarSet response into a clean multi-index DataFrame dictionary
                bars_df = bars_response.df

                # 3. Iterate through universe and evaluate strategy criteria
                for symbol in active_universe:
                    logger.info(f"Evaluating strategy metrics for {symbol}...")
                    
                    try:
                        # Extract individual symbol slice from the DataFrame
                        if symbol in bars_df.index.get_level_values(0):
                            sym_df = bars_df.loc[symbol]
                            
                            if len(sym_df) >= 2:
                                latest_close = sym_df.iloc[-1]['close']
                                prev_close = sym_df.iloc[-2]['close']

                                # Momentum Rule: Buy if latest daily close exceeds previous close
                                if latest_close > prev_close:
                                    logger.info(f"Bullish momentum confirmed for {symbol} (Close: {latest_close} > Prev: {prev_close})")
                                    self.execute_trade_safe(symbol, OrderSide.BUY, qty=1)
                                    break 
                                else:
                                    logger.info(f"No signal for {symbol}. Close did not exceed previous bar.")
                        else:
                            logger.warning(f"No bar data found for {symbol} in response.")
                    except Exception as inner_e:
                        logger.error(f"Error processing symbol {symbol}: {inner_e}")

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
