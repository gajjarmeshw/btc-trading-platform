from app.engine.backtest_engine import BacktestEngine
from strategies.btc_ml_strategy import BTCMLStrategy5m, BTCMLStrategy1m
# from strategies.btc_volatility_breakout import BTCVolatilityBreakout
import pandas as pd
import os

def load_data(filepath):
    if not os.path.exists(filepath):
        print(f"Error: Data file {filepath} not found.")
        return None
    df = pd.read_csv(filepath)
    # Ensure necessary columns
    expected_cols = ["timestamp", "open", "high", "low", "close", "volume"]
    if not all(col in df.columns for col in expected_cols):
        print(f"Error: Data file missing columns. Expected {expected_cols}")
        return None
    return df

import argparse

def main():
    parser = argparse.ArgumentParser(description="Run backtest on historical data")
    parser.add_argument("data_path", nargs="?", default="data/historical/BTC_USDT_5m.csv", help="Path to historical data CSV")
    parser.add_argument("--strategy", type=str, default="ml_5m", choices=["ml_5m", "ml_1m"], help="Strategy to run")
    parser.add_argument("--compounding", action="store_true", help="Enable compounding (reinvest profits)")
    args = parser.parse_args()

    print(f"Loading data from {args.data_path}...")
    
    historical_data = load_data(args.data_path)
    if historical_data is None:
        return

    # Filter Last 1 Year
    if not pd.api.types.is_datetime64_any_dtype(historical_data["timestamp"]):
        historical_data["timestamp"] = pd.to_datetime(historical_data["timestamp"])
    
    end_date = historical_data["timestamp"].max()
    start_date = end_date - pd.Timedelta(days=365)
    print(f"Filtering data: Last 1 Year ({start_date} to {end_date})")
    
    historical_data = historical_data[historical_data["timestamp"] >= start_date].copy().reset_index(drop=True)

    if args.strategy == "ml_1m":
        print("Initializing Strategy: BTCMLStrategy1m (Ultra Scalper)")
        strategy = BTCMLStrategy1m()
    else:
        print("Initializing Strategy: BTCMLStrategy5m (High Yield)")
        strategy = BTCMLStrategy5m()

    print(f"Initializing Backtest Engine... (Compounding: {args.compounding})")
    engine = BacktestEngine(strategy, historical_data, compounding=args.compounding)
    
    engine.run()

if __name__ == "__main__":
    main()
