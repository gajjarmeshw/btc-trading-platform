import time
import logging
from datetime import datetime
import math
from app.config.dynamic_config import update_status, load_config

# ... (Logging setup remains) ...

class LiveEngine:
    def __init__(self, strategy, data_feed, executor, risk):
        self.strategy = strategy
        self.data_feed = data_feed
        self.executor = executor
        self.risk = risk
        self.compounding = False
        self.timeframe_map = {"1m": 60, "5m": 300}
        self.interval_seconds = self.timeframe_map.get(strategy.timeframe_str, 60)
        
        logging.info(f"Engine Initialized. Strategy: {strategy.name} | Interval: {self.interval_seconds}s")

    def sync_time(self):
        """Align with candle close"""
        now = time.time()
        # Remaining time until next interval
        sleep_time = self.interval_seconds - (now % self.interval_seconds)
        
        # Add small buffer to ensure candle is closed at exchange
        sleep_time += 1 
        
        logging.info(f"Waiting {sleep_time:.1f}s for candle close...")
        time.sleep(sleep_time)

    def run(self):
        logging.info("Starting Live Trading Loop...")
        self.executor.sync_position()
        
        while True:
            try:
                self.sync_time()
                
                # 1. Update Dynamic Config
                config = load_config()
                # Pass config to strategy if supported
                if hasattr(self.strategy, 'update_parameters'):
                    self.strategy.update_parameters(config)
                
                # Fetch Data
                df = self.data_feed.get_latest()
                trend = self.data_feed.get_1h_trend()
                
                # 2. Update Dashboard Status
                last_price = 0
                if df is not None and not df.empty:
                    last_price = df.iloc[-1]["close"]
                
                # Get Balance (Estimate)
                bal = "N/A"
                if hasattr(self.executor, 'client') and self.executor.client:
                     try:
                        info = self.executor.client.fetch_balance()
                        usdt = info['USDT']['free']
                        btc = info['BTC']['free']
                        bal = f"${usdt:.2f} | {btc:.5f} BTC"
                     except: pass

                status_data = {
                    "price": last_price,
                    "balance": bal,
                    "position": "LONG" if self.executor.has_position() else "FLAT",
                    "strategy": self.strategy.name
                }
                update_status(status_data)

                # ... (Rest of loop) ...
                
                if df is None or len(df) < 200:
                    logging.warning(f"Insufficient data ({len(df) if df is not None else 0} rows). Retrying next cycle.")
                    continue
                
                # Inject 1H trend
                df["trend_1h"] = trend
                    
                # Calculate Indicators
                df = self.strategy.indicators(df)
                
                if len(df) == 0:
                     logging.warning("DataFrame empty after indicators (Check dropna). Retrying...")
                     continue
                     
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
