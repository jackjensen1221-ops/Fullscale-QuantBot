import os
import time
import logging
import requests
from datetime import datetime
from dotenv import load_dotenv

# Import your custom modules based on your folder structure
from strategies.market_scanner import FullMarketScanner
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass

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
        self.scanner = FullMarketScanner()
        self.notifier = NotificationManager()

    def run(self):
        self.notifier.send_alert("Core Engine Initialized", "Quantitative trading engine started successfully.", level="INFO")
        logger.info("Core engine operational. Entering primary execution loop...")

        while True:
            try:
                # 1. Dynamically pull top market volume leaders (replaces hardcoded tickers)
                active_universe = self.scanner.get_dynamic_trading_universe(top_n=5)

                # 2. Iterate through the dynamic market universe to evaluate signals
                for symbol in active_universe:
                    logger.info(f"Evaluating multi-strategy signals for {symbol}...")
                    
                    # --- INSERT YOUR STRATEGY EVALUATION LOGIC HERE ---
                    # if strategy_triggers_buy:
                    #     self.execute_trade(symbol, OrderSide.BUY, qty=1)

                # 3. Sleep cycle to respect API rate limits (200 requests/minute)
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
