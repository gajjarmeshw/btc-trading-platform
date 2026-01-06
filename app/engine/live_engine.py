import time
import logging
from datetime import datetime
import math

# Configure Logging
logging.basicConfig(
    filename='trading.log', 
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger('').addHandler(console)

class LiveEngine:
    def __init__(self, strategy, data_feed, executor, risk):
        self.strategy = strategy
        self.data_feed = data_feed
        self.executor = executor
        self.risk = risk
        self.compounding = False
        self.timeframe_map = {"1m": 60, "5m": 300}
        self.interval_seconds = self.timeframe_map.get(strategy.timeframe_str, 60) # Default to 1m if unsure
        
        logging.info(f"Engine Initialized. Strategy: {strategy.name} | Interval: {self.interval_seconds}s")

    def sync_time(self):
        """Sleeps until the start of the next minute/interval"""
        now = time.time()
        next_boundary = math.ceil(now / 60) * 60
        # If interval is 5m, align to 5m grid (00:00, 00:05...)
        if self.interval_seconds == 300:
            next_boundary = math.ceil(now / 300) * 300
            
        sleep_sec = next_boundary - now + 1 # +1s buffer to ensure candle closed
        logging.info(f"Waiting {sleep_sec:.1f}s for candle close...")
        time.sleep(sleep_sec)

    def run(self):
        logging.info("Starting Live Trading Loop...")
        
        # Initial Pos Sync
        self.executor.sync_position()
        
        while True:
            try:
                self.sync_time()
                
                # Fetch Data
                df = self.data_feed.get_latest()
                if df is None or len(df) < 200:
                    logging.warning(f"Insufficient data ({len(df) if df is not None else 0} rows). Retrying next cycle.")
                    continue
                    
                # Calculate Indicators
                df = self.strategy.indicators(df)
                current_price = df.iloc[-1]["close"]
                
                if not self.executor.has_position():
                    # Look for Entry
                    if self.strategy.should_enter(df):
                        if self.risk.can_trade():
                            logging.info(f"SIGNAL DETECTED (BUY) @ {current_price}")
                            self.executor.buy()
                else:
                    # Look for Exit
                    # Pass a mock position object if internal tracking used, 
                    # but executor.position should handle it. Keep consistency.
                    if self.strategy.should_exit(df, self.executor.position):
                        logging.info(f"SIGNAL DETECTED (SELL) @ {current_price}")
                        self.executor.sell()
                        
            except KeyboardInterrupt:
                logging.info("Stopping Bot...")
                break
            except Exception as e:
                logging.error(f"CRITICAL ERROR in Loop: {e}")
                time.sleep(10) # Prevent tight crash loop
