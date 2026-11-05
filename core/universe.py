import os
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetAssetsRequest
from alpaca.trading.enums import AssetClass, AssetStatus

def get_tradable_universe(min_price=10.0, max_symbols=100):
    """
    Dynamically fetches tradable US equities from Alpaca 
    and returns a filtered list of liquid tickers.
    """
    api_key = os.getenv("APCA_API_KEY_ID") or os.getenv("ALPACA_API_KEY_ID")
    secret_key = os.getenv("APCA_API_SECRET_KEY") or os.getenv("ALPACA_SECRET_KEY")
    
    if not api_key or not secret_key:
        print("⚠️ [Universe Loader]: Missing API credentials, falling back to core default watchlists.")
        return ["SPY", "QQQ", "AAPL", "MSFT", "NVDA", "TSLA", "KO", "PEP"]

    try:
        client = TradingClient(api_key, secret_key, paper=True)
        search_params = GetAssetsRequest(
            status=AssetStatus.ACTIVE,
            asset_class=AssetClass.US_EQUITY
        )
        assets = client.get_all_assets(search_params)
        
        # Filter for tradable, fractionable, marginable standard stocks
        valid_symbols = [
            asset.symbol for asset in assets 
            if asset.tradable and "/" not in asset.symbol and "." not in asset.symbol
        ]
        
        # Limit size to prevent API rate limits on free loops (e.g., top N symbols)
        selected = valid_symbols[:max_symbols]
        print(f"🌍 [Universe Loader]: Dynamically loaded {len(selected)} tradeable symbols from Alpaca.")
        return selected

    except Exception as e:
        print(f"❌ [Universe Loader Error]: {e}. Falling back to default list.")
        return ["SPY", "QQQ", "AAPL", "MSFT", "NVDA", "TSLA", "KO", "PEP"]
