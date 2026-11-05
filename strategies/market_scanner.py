import os
import logging
from alpaca.data.historical.screener import ScreenerClient
from alpaca.data.requests import MostActivesRequest
from alpaca.data.enums import MostActivesBy

logger = logging.getLogger("FullMarketScanner")

class FullMarketScanner:
    def __init__(self):
        self.api_key = os.getenv("APCA_API_KEY_ID")
        self.secret_key = os.getenv("APCA_API_SECRET_KEY")
        self.screener_client = ScreenerClient(self.api_key, self.secret_key)

    def get_dynamic_trading_universe(self, top_n: int = 5) -> list[str]:
        """Queries Alpaca's Screener API to extract the top most active U.S. equities."""
        try:
            logger.info("Scanning full market for top volume leaders...")
            actives_request = MostActivesRequest(top=top_n, by=MostActivesBy.VOLUME)
            actives_response = self.screener_client.get_most_actives(actives_request)
            
            active_items = getattr(actives_response, 'most_actives', [])
            symbols = [item.symbol for item in active_items]
            
            if not symbols:
                logger.warning("Screener returned empty universe. Using fallback basket.")
                return ["SPY", "QQQ", "TLT"]
                
            logger.info(f"Full-market dynamic universe locked: {symbols}")
            return symbols
            
        except Exception as e:
            logger.error(f"Error executing full market scan: {e}")
            return ["SPY", "QQQ", "TLT"]
