import ccxt
import pandas as pd
from datetime import datetime

class DataFeed:
    def get_latest(self):
        raise NotImplementedError

class BinanceDataFeed(DataFeed):
    def __init__(self, symbol="BTC/USDT", timeframe="5m", limit=100):
        self.symbol = symbol
        self.timeframe = timeframe
        self.limit = limit
        self.exchange = ccxt.binance()

    def get_latest(self):
        try:
            # Fetch OHLCV: timestamp, open, high, low, close, volume
            ohlcv = self.exchange.fetch_ohlcv(self.symbol, self.timeframe, limit=self.limit)
            
            if not ohlcv:
                return pd.DataFrame()

            # Create DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # Convert timestamp to datetime (optional, but good for debugging)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            return df
        except Exception as e:
            print(f"Error fetching live data: {e}")
            return pd.DataFrame()
