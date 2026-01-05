from .exchange import Exchange
import os
import logging
from dotenv import load_dotenv

load_dotenv()

class Position:
    def __init__(self, entry_price, size):
        self.entry = entry_price
        self.size = size

class BinanceSpot(Exchange):
    def __init__(self):
        self.position = None
        self.api_key = os.getenv("BINANCE_API_KEY")
        self.secret_key = os.getenv("BINANCE_SECRET_KEY")
        self.live_mode = os.getenv("LIVE_TRADING_ENABLED", "false").lower() == "true"
        
        self.client = None
        if self.api_key and self.secret_key and "your_key" not in self.api_key:
            import ccxt
            logging.info("Initializing connection to Binance...")
            self.client = ccxt.binance({
                'apiKey': self.api_key,
                'secret': self.secret_key,
                'enableRateLimit': True,
                # 'options': {'defaultType': 'future'} # Uncomment if trading futures
            })
            if not self.live_mode:
                 self.client.set_sandbox_mode(True) # Just in case, though usually manual
                 logging.info("Running in SIMULATION MODE (Live execution disabled in .env)")
        else:
             logging.warning("No API Keys found. Running in MOCK Mode.")

    def sync_position(self):
        """Query exchange to restore state on startup"""
        if not self.client: return
        
        try:
            bal = self.client.fetch_balance()
            btc_free = float(bal['BTC']['free'])
            usdt_free = float(bal['USDT']['free'])
            
            # Simple Logic: If we hold > 0.0001 BTC (~$4-5 at $45k), assume we are LONG
            if btc_free > 0.0001:
                # We don't know entry price from balance alone, assume current price?
                # Or fetch last trade. For strict safety, let's fetch ticker.
                ticker = self.client.fetch_ticker('BTC/USDT')
                current_price = ticker['last']
                
                logging.info(f"Restoring Position: {btc_free} BTC found.")
                # We assume entry is roughly current price if unknown, 
                # effectively resetting stops. Trade carefully.
                self.position = Position(entry_price=current_price, size=btc_free)
            else:
                logging.info(f"No existing BTC position ({btc_free}). Ready to Buy. USDT: {usdt_free:.2f}")
                self.position = None
                
        except Exception as e:
            logging.error(f"Failed to sync position: {e}")

    def has_position(self):
        return self.position is not None

    def _log_trade(self, side, price, size, pnl=None):
        """Append trade details to CSV for easy user access"""
        import csv
        from datetime import datetime
        
        file_path = "data/live_trades.csv"
        file_exists = os.path.isfile(file_path)
        
        try:
            with open(file_path, mode='a', newline='') as f:
                writer = csv.writer(f)
                
                # Write Header if new file
                if not file_exists:
                    writer.writerow(["Timestamp", "Side", "Price", "Size (BTC)", "Value (USDT)", "PnL (USDT)", "PnL (%)"])
                
                # Write Data
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                value = price * size
                pnl_str = f"{pnl:.2f}" if pnl is not None else ""
                pnl_pct = "" # Todo: Calculate if needed, but absolute is fine for now
                
                # Calculate % if PnL exists
                if pnl is not None and self.position and self.position.entry:
                    entry_val = self.position.entry * size
                    pnl_pct = f"{(pnl / entry_val * 100):.2f}%"

                writer.writerow([timestamp, side, f"{price:.2f}", f"{size:.6f}", f"{value:.2f}", pnl_str, pnl_pct])
                print(f"Trade Logged to {file_path}")
                
        except Exception as e:
            logging.error(f"Failed to log trade to CSV: {e}")

    def buy(self, size=None):
        if self.client:
            # Calculate Size (Compounding: 99% of USDT Balance)
            try:
                bal = self.client.fetch_balance()
                usdt_free = float(bal['USDT']['free'])
                ticker = self.client.fetch_ticker('BTC/USDT')
                price = ticker['last']
                
                amount_to_spend = usdt_free * 0.99
                amount_btc = amount_to_spend / price
                
                # Min Notional Check (approx $5 for testing)
                if amount_to_spend < 5:
                    logging.warning(f"Insufficient funds to buy: ${usdt_free:.2f} (Min $5)")
                    return

                if self.live_mode:
                    logging.info(f"EXECUTING MARKET BUY: {amount_btc:.5f} BTC @ ~{price}")
                    order = self.client.create_market_buy_order('BTC/USDT', amount_btc)
                    print(f"Order Filled: {order['id']}")
                    
                    real_entry = float(order.get('average', price))
                    self.position = Position(real_entry, amount_btc)
                    self._log_trade("BUY", real_entry, amount_btc)
                else:
                    logging.info(f"[SIM] BUY {amount_btc:.5f} BTC @ {price}")
                    self.position = Position(price, amount_btc)
                    self._log_trade("BUY (SIM)", price, amount_btc)

            except Exception as e:
                logging.error(f"Buy Order Failed: {e}")

    def sell(self):
        if self.client:
            try:
                bal = self.client.fetch_balance()
                btc_free = float(bal['BTC']['free'])
                
                if btc_free < 0.0001:
                    logging.warning("No BTC to sell?")
                    self.position = None
                    return

                # Calculate PnL Reference
                pnl = None
                ticker = self.client.fetch_ticker('BTC/USDT')
                current_price = ticker['last']
                
                if self.position:
                    revenue = current_price * btc_free
                    cost = self.position.entry * btc_free
                    pnl = revenue - cost

                if self.live_mode:
                    logging.info(f"EXECUTING MARKET SELL: {btc_free:.5f} BTC")
                    order = self.client.create_market_sell_order('BTC/USDT', btc_free)
                    print(f"Order Filled: {order['id']}")
                    
                    real_exit = float(order.get('average', current_price))
                    # Recalculate exact PnL with real exit price
                    if self.position:
                        revenue = real_exit * btc_free
                        pnl = revenue - cost
                        
                    self._log_trade("SELL", real_exit, btc_free, pnl)
                else:
                    logging.info(f"[SIM] SELL {btc_free:.5f} BTC")
                    self._log_trade("SELL (SIM)", current_price, btc_free, pnl)
                
                self.position = None

            except Exception as e:
                 logging.error(f"Sell Order Failed: {e}")
