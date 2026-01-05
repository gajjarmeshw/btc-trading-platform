# btc-trading-platform

A strategy-first, private, extensible, and ML-ready Bitcoin trading platform.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure environment:
   ```bash
   cp .env.example .env
   # Edit .env with your keys
   ```

3. Run live:
   ```bash
   ./scripts/run_live.sh
   # Or: python3 main.py
   ```

4. Run Backtest:
   ```bash
   ./scripts/run_backtest.sh
   # Or: python3 backtest_runner.py
   ```


## Structure

- `app/engine`: Core trading engine
- `app/strategies`: Strategy logic
- `strategies`: User strategies
- `app/execution`: Exchange integration
- `app/risk`: Risk management
# btc-trading-platform
