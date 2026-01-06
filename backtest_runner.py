from app.engine.backtest_engine import BacktestEngine
from strategies.btc_ml_strategy import BTCMLStrategy5m, BTCMLStrategy1m
# from strategies.btc_volatility_breakout import BTCVolatilityBreakout
import pandas as pd
import os

import sys
sys.path.append(os.getcwd()) # Ensure root is in path
from scripts.download_data import download_data

def load_data(filepath, timeframe="5m", days=180):
    need_download = False
    if not os.path.exists(filepath):
        print(f"Data file {filepath} not found. Downloading...")
        need_download = True
    else:
        # Validate existing data duration
        try:
            df = pd.read_csv(filepath)
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                min_date = df['timestamp'].min()
                required_date = pd.Timestamp.now() - pd.Timedelta(days=days)
                # Allow 1 day buffer
                if min_date > (required_date + pd.Timedelta(days=1)):
                    print(f"Existing data insufficient (Starts {min_date}, need {required_date}). Re-downloading...")
                    need_download = True
            else:
                 need_download = True
        except:
            need_download = True

    if need_download:
        try:
            # Infer args or use defaults
            # Assuming filepath structure data/historical/BTC_USDT_5m.csv
            download_data("BTC/USDT", timeframe, days, os.path.dirname(filepath))
            if not os.path.exists(filepath):
                print("Error: Download failed or file naming mismatch.")
                return None
            df = pd.read_csv(filepath)
        except Exception as e:
            print(f"Auto-download failed: {e}")
            return None
            
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
    parser.add_argument("--days", type=int, default=180, help="Days of history to use")
    parser.add_argument("--compounding", action="store_true", help="Enable compounding (reinvest profits)")
    args = parser.parse_args()

    timeframe = "1m" if args.strategy == "ml_1m" else "5m"
    
    # Auto-adjust path if default used but strategy changed
    if args.data_path == "data/historical/BTC_USDT_5m.csv" and timeframe == "1m":
         args.data_path = "data/historical/BTC_USDT_1m.csv"

    print(f"Loading data from {args.data_path} (Last {args.days} Days)...")
    
    historical_data = load_data(args.data_path, timeframe=timeframe, days=args.days)
    if historical_data is None:
        return

    # Filter Last N Days
    if not pd.api.types.is_datetime64_any_dtype(historical_data["timestamp"]):
        historical_data["timestamp"] = pd.to_datetime(historical_data["timestamp"])
    
    end_date = historical_data["timestamp"].max()
    start_date = end_date - pd.Timedelta(days=args.days)
    print(f"Filtering data: {start_date} to {end_date}")
    
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
