import ccxt
import pandas as pd
from datetime import datetime

class DataFeed:
    def get_latest(self):
        raise NotImplementedError

class BinanceDataFeed(DataFeed):
    def __init__(self, symbol="BTC/USDT", timeframe="5m", limit=300):
        self.symbol = symbol
        self.timeframe = timeframe
        self.limit = limit
        self.exchange = ccxt.binance()
        
    def get_1h_trend(self):
        """Fetches 1h candles to determine long-term trend (1 or -1)"""
        try:
            # We need 200 candles for SMA 200
            ohlcv = self.exchange.fetch_ohlcv(self.symbol, "1h", limit=210)
            if not ohlcv or len(ohlcv) < 200:
                return 0 # Neutral fallback
            
            closes = pd.Series([x[4] for x in ohlcv])
            sma200 = closes.rolling(window=200).mean()
            
            # Check last closed candle (index -2 usually, but strict -1 is fine for trend)
            last_close = closes.iloc[-1]
            last_sma = sma200.iloc[-1]
            
            return 1 if last_close > last_sma else -1
        except Exception as e:
            print(f"Error fetching 1h trend: {e}")
            return 0

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
