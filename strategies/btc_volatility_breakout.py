from app.strategies.base import StrategyBase
import ta

class BTCVolatilityBreakout(StrategyBase):
    name = "btc_volatility_breakout"
    timeframe = "15m"

    def indicators(self, df):
        df = df.copy()
        
        # 1. Volatility: Bollinger Bands (20, 2)
        bb = ta.volatility.BollingerBands(close=df["close"], window=20, window_dev=2)
        df["bb_high"] = bb.bollinger_hband()
        df["bb_mid"] = bb.bollinger_mavg() # SMA 20
        df["bb_low"] = bb.bollinger_lband()
        
        # 2. Trend Strength: ADX (14)
        adx = ta.trend.ADXIndicator(high=df["high"], low=df["low"], close=df["close"], window=14)
        df["adx"] = adx.adx()
        
        # 3. Momentum: RSI (14)
        df["rsi"] = ta.momentum.rsi(df["close"], window=14)
        
        return df

    def should_enter(self, df):
        if len(df) < 20:
            return False

        current = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Condition 1: Breakout (Close crosses above Upper Band)
        breakout = current["close"] > current["bb_high"]
        
        # Condition 2: Strength (ADX > 20)
        strong_trend = current["adx"] > 20
        
        # Condition 3: Momentum (RSI > 50 but not extremely overbought > 85 to avoid buying top)
        good_momentum = 50 < current["rsi"] < 85
        
        return breakout and strong_trend and good_momentum

    def should_exit(self, df, position):
        current = df.iloc[-1]
        
        # Exit 1: Trailing Stop - Price falls back below Middle Band (SMA 20)
        # This allows us to ride the trend as long as it stays above the mean.
        trend_broken = current["close"] < current["bb_mid"]
        
        # Exit 2: Hard Stop Loss (3%)
        # In a real engine, this is checked every tick, here every candle close.
        stop_loss = current["close"] < position.entry * 0.97
        
        return trend_broken or stop_loss
