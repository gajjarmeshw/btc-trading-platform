import pandas as pd
import numpy as np

class BacktestEngine:
    def __init__(self, strategy, historical_data, compounding=False):
        self.strategy = strategy
        self.data = historical_data
        self.position = None
        self.trades = []
        self.equity = 10000.0  # Starting capital
        self.compounding = compounding

    def run(self):
        print(f"Starting backtest with ${self.equity:.2f} (Compounding: {self.compounding})")
        print(f"Pre-calculating indicators for {len(self.data)} rows...")
        
        # Ensure timestamp is datetime for duration calc
        if not pd.api.types.is_datetime64_any_dtype(self.data["timestamp"]):
             self.data["timestamp"] = pd.to_datetime(self.data["timestamp"])
             
        full_df = self.strategy.indicators(self.data)
        
        # We need enough data for lookback
        min_lookback = 200 # increased for EMA 200 checks
        
        print("Running simulation...")
        
        # Fixed Stake Amount (Non-Compounding)
        fixed_stake = 10000.0
        
        for i in range(min_lookback, len(full_df)):
            if i % 1000 == 0:
                print(f"Processing candle {i}/{len(full_df)}...", end='\r')

            # Create a window view up to the current point
            window_with_indicators = full_df.iloc[:i+1]
            current_close = window_with_indicators["close"].iloc[-1]
            current_time = window_with_indicators["timestamp"].iloc[-1] 

            if not self.position:
                if self.strategy.should_enter(window_with_indicators):
                    # Capital Sizing
                    if self.compounding:
                        entry_capital = self.equity # All in (or manageable portion)
                    else:
                        entry_capital = min(fixed_stake, self.equity)
                    
                    self.position = type('Position', (), {
                        'entry': current_close, 
                        'size': entry_capital / current_close,
                        'entry_time': current_time,
                        'capital': entry_capital
                    })
            else:
                if self.strategy.should_exit(window_with_indicators, self.position):
                    # Simulate Sell
                    exit_price = current_close
                    pnl_pct = (exit_price - self.position.entry) / self.position.entry
                    pnl_amount = self.position.size * (exit_price - self.position.entry)
                    
                    self.equity += pnl_amount
                    
                    duration = current_time - self.position.entry_time
                    
                    self.trades.append({
                        'entry': self.position.entry, 
                        'exit': exit_price, 
                        'pnl': pnl_amount, 
                        'pnl_pct': pnl_pct, 
                        'entry_time': self.position.entry_time,
                        'exit_time': current_time,
                        'duration': duration
                    })
                    self.position = None

        print(f"Backtest finished.")
        print(f"Final Equity: ${self.equity:.2f}")
        
        if self.trades:
            trades_df = pd.DataFrame(self.trades)
            
            # Stats Calculation
            if len(trades_df) > 0:
                print("\n--- Detailed Statistics ---")
                print(f"Total Trades: {len(trades_df)}")
                print(f"Failed Trades: {len(trades_df[trades_df['pnl'] < 0])}")
                print(f"Win Rate: {len(trades_df[trades_df['pnl'] > 0]) / len(trades_df) * 100:.2f}%")
                print(f"Avg Hold Time: {pd.to_timedelta(trades_df['duration']).mean()}")
                print(f"Max Loss (Single Trade): ${trades_df['pnl'].min():.2f}")
                
                # Reconstruct Equity Curve for Drawdown
                equity_curve = [10000.0]
                current_eq = 10000.0
                for pnl in trades_df['pnl']:
                    current_eq += pnl
                    equity_curve.append(current_eq)
                
                equity_series = pd.Series(equity_curve)
                running_max = equity_series.cummax()
                drawdown = (equity_series - running_max) / running_max
                max_drawdown_pct = drawdown.min() * 100
                 
                print(f"Max Drawdown (Portfolio): {max_drawdown_pct:.2f}%")
                print(f"Final Return: {(self.equity - 10000) / 10000 * 100:.2f}%")

                # --- Monthly Breakdown ---
                print("\n--- Monthly ROI Breakdown ---")
                trades_df['exit_month'] = pd.to_datetime(trades_df['exit_time']).dt.to_period('M')
                monthly_group = trades_df.groupby('exit_month')
                
                for period, group in monthly_group:
                    m_pnl = group['pnl'].sum()
                    m_trades = len(group)
                    m_wins = len(group[group['pnl'] > 0])
                    m_wr = (m_wins / m_trades * 100) if m_trades > 0 else 0
                    print(f"{period}: PnL ${m_pnl:,.2f} | Trades: {m_trades} | WR: {m_wr:.1f}%")

                # --- Leverage Scenario Matrix ---
                print("\n--- Leverage Potential (Simulated) ---")
                print("Note: Estimates assuming proportional max drawdown scaling.")
                base_ret = (self.equity - 10000) / 10000 * 100
                base_dd = max_drawdown_pct
                
                print(f"{' Lev':<5} | {'Return %':<10} | {'Max DD %':<10} | {'Est. Equity':<15}")
                print("-" * 50)
                
                for lev in [1, 2, 5, 10, 20]:
                    sim_ret = base_ret * lev
                    sim_dd = base_dd * lev
                    sim_eq = 10000 * (1 + sim_ret/100)
                    
                    # Risk Warning
                    warning = " (RISKY)" if abs(sim_dd) > 30 else ""
                    warning = " (BUSTED)" if abs(sim_dd) > 90 else warning
                    
                    if abs(sim_dd) > 100:
                        sim_ret = -100
                        sim_eq = 0
                        warning = " (LIQUIDATED)"
                    
                    print(f"{lev:<5}x | {sim_ret:,.0f}%{warning:<10} | {sim_dd:.2f}%     | ${sim_eq:,.0f}")

            else:
                print("No trades were executed.")
        else:
            print("No trades were executed.")
