from app.engine.live_engine import LiveEngine
from strategies.btc_ml_strategy import BTCMLStrategy5m, BTCMLStrategy1m
from app.market.data_feed import BinanceDataFeed
from app.execution.binance_spot import BinanceSpot
from app.risk.governor import RiskGovernor
import argparse

def main():
    parser = argparse.ArgumentParser(description="BTC Live Trading Bot")
    parser.add_argument("--choice", type=str, default="ml_5m", choices=["ml_5m", "ml_1m"], help="Strategy Choice")
    # Note: Compounding is handled in strategy logic or position sizing (not explicitly in live engine yet, but placeholder arg)
    parser.add_argument("--compounding", action="store_true", help="Enable compounding")
    args = parser.parse_args()

    print(f"Welcome to BTC Trading Platform (Live Mode) - {args.choice}")
    
    # Configure Logging (File + Console)
    import logging
    import os
    
    log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'trading.log')
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    logging.info("--- Service Started ---")
    
    if args.choice == "ml_1m":
        print("Strategy: 1m Ultra-Scalper")
        strategy = BTCMLStrategy1m()
        timeframe = "1m"
    else:
        print("Strategy: 5m High-Yield")
        strategy = BTCMLStrategy5m()
        timeframe = "5m"
    
    # Live Data Feed
    print(f"Connecting to Binance ({timeframe})...")
    data_feed = BinanceDataFeed(symbol="BTC/USDT", timeframe=timeframe)
    
    executor = BinanceSpot()
    risk = RiskGovernor()

    engine = LiveEngine(strategy, data_feed, executor, risk)
    
    # Pass compounding flag to risk or engine if supported (future proofing)
    if hasattr(engine, 'compounding'):
        engine.compounding = args.compounding

    try:
        engine.run()
    except KeyboardInterrupt:
        print("\nBot stopped by user.")
    except Exception as e:
        print(f"Engine stopped with error: {e}")

if __name__ == "__main__":
    main()
