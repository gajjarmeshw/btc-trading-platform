import ccxt
import pandas as pd
import argparse
import os
from datetime import datetime, timedelta

def download_data(symbol, timeframe, days, output_dir):
    print(f"Initializing Binance connection for {symbol} ({timeframe})...")
    exchange = ccxt.binance()
    
    # Calculate start time
    since = exchange.milliseconds() - (days * 24 * 60 * 60 * 1000)
    
    all_ohlcv = []
    limit = 1000  # Binance limit
    
    print(f"Fetching data since {datetime.fromtimestamp(since/1000)}...")
    
    while True:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since, limit)
            if not ohlcv:
                break
            
            all_ohlcv.extend(ohlcv)
            print(f"Fetched {len(ohlcv)} candles. Last: {datetime.fromtimestamp(ohlcv[-1][0]/1000)}")
            
            since = ohlcv[-1][0] + 1
            
            # If we fetched fewer than limit, we reached the end
            if len(ohlcv) < limit:
                break
                
        except Exception as e:
            print(f"Error fetching data: {e}")
            break
            
    if not all_ohlcv:
        print("No data fetched.")
        return

    # Convert to DataFrame
    df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Sanitize filename
    safe_symbol = symbol.replace('/', '_')
    filename = f"{safe_symbol}_{timeframe}.csv"
    filepath = os.path.join(output_dir, filename)
    
    df.to_csv(filepath, index=False)
    print(f"Saved {len(df)} rows to {filepath}")

def main():
    parser = argparse.ArgumentParser(description="Download historical data from Binance")
    parser.add_argument("--symbol", type=str, default="BTC/USDT", help="Trading pair symbol (e.g. BTC/USDT)")
    parser.add_argument("--timeframe", type=str, default="15m", help="Timeframe (e.g. 1m, 5m, 15m, 1h, 1d)")
    parser.add_argument("--days", type=int, default=30, help="Number of days of history to fetch")
    parser.add_argument("--output", type=str, default="data/historical", help="Output directory")
    
    args = parser.parse_args()
    
    download_data(args.symbol, args.timeframe, args.days, args.output)

if __name__ == "__main__":
    main()
