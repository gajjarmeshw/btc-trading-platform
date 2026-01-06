from strategies.btc_volatility_breakout import BTCVolatilityBreakout
import joblib
import pandas as pd
import ta
import os
import numpy as np
# XGBoost must be imported for joblib to deserialize the model
from xgboost import XGBClassifier 

class BTCMLStrategyBase(BTCVolatilityBreakout):
    """Base class for ML Strategies"""
    
    def __init__(self, timeframe="5m", model_path="models/btc_xgb_5m.joblib", thresh_path="models/btc_xgb_threshold_5m.joblib"):
        super().__init__()
        self.timeframe_str = timeframe
        self.model = None
        self.threshold = 0.5
        
        # Dynamic Params (Defaults)
        self.dynamic_sl = 0.005 # 0.5%
        self.dynamic_tp = 0.010 # 1.0%
        
        self.load_model(model_path, thresh_path)
        
    def update_parameters(self, config):
        """Called by LiveEngine to update dynamic params"""
        try:
            self.dynamic_sl = float(config.get("stop_loss_pct", 0.5)) / 100.0
            self.dynamic_tp = float(config.get("take_profit_pct", 1.0)) / 100.0
        except: pass # Keep defaults on error
        
    def load_model(self, model_path, thresh_path):
        if os.path.exists(model_path):
            try:
                self.model = joblib.load(model_path)
                print(f"XGBoost Model ({self.timeframe_str}) loaded successfully.")
            except Exception as e:
                print(f"Failed to load XGBoost model: {e}")
        else:
            print(f"Warning: Model not found at {model_path}")
                
        if os.path.exists(thresh_path):
             self.threshold = joblib.load(thresh_path)
             print(f"Loaded Optimal Threshold: {self.threshold}")
             
    def indicators(self, df):
        # 1. Call Base Indicators (Vol Breakout)
        df = super().indicators(df)
        
        # 2. Add ML Specific Features (Lags)
        df["bb_width"] = (df["bb_high"] - df["bb_low"]) / df["bb_mid"]
        
        df["sma_200"] = ta.trend.sma_indicator(df["close"], window=200)
        df["dist_from_sma200"] = (df["close"] - df["sma_200"]) / df["sma_200"]
        
        df["volume_sma"] = df["volume"].rolling(window=20).mean()
        df["volume_rel"] = df["volume"] / df["volume_sma"]
        
        for col in ["rsi", "adx", "bb_width", "volume_rel"]:
            df[f"{col}_lag1"] = df[col].shift(1)
            df[f"{col}_lag2"] = df[col].shift(2)
            df[f"{col}_change"] = df[col] - df[f"{col}_lag1"]
            
        # 3. Multi-Timeframe Trend (1H)
        if "trend_1h" not in df.columns:
            if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
                 df["timestamp"] = pd.to_datetime(df["timestamp"])
    
            df_1h = df.resample("1h", on="timestamp").agg({"close": "last"}).dropna()
            df_1h["sma200_1h"] = ta.trend.sma_indicator(df_1h["close"], window=200)
            df_1h = df_1h[["sma200_1h"]]
            
            df = pd.merge_asof(df.sort_values("timestamp"), df_1h.sort_values("timestamp"), on="timestamp", direction="backward")
            df["trend_1h"] = np.where(df["close"] > df["sma200_1h"], 1, -1)
        
        # 4. Micro-Structure (Only for 1m subclass overrides, but we can compute here for base too or pass)
        # We'll compute it here for simplicity
        df["body_size"] = np.abs(df["close"] - df["open"])
        df["upper_shadow"] = df["high"] - np.maximum(df["close"], df["open"])
        df["lower_shadow"] = np.minimum(df["close"], df["open"]) - df["low"]
        
        price_range = df["high"] - df["low"]
        price_range = price_range.replace(0, 0.000001)
        
        df["body_to_range"] = df["body_size"] / price_range
        df["shadow_dominance"] = (df["upper_shadow"] + df["lower_shadow"]) / price_range

        return df.dropna()
        
    def should_enter(self, df):
        if self.model is None or len(df) < 200:
            return False

        current = df.iloc[-1]
        prev = df.iloc[-2]
        
        # 0. Volatility Breakout Check
        breakout = (current["close"] > current["bb_high"]) and (prev["close"] <= prev["bb_high"])
        
        if not breakout:
            # FORCE LOG for user visibility
            import logging
            logging.info(f"[Analysis] Price: {current['close']:.2f} | BB High: {current['bb_high']:.2f} | Action: WAIT (No Breakout)")
            return False
            
        return True 

class BTCMLStrategy5m(BTCMLStrategyBase):
    name = "btc_ml_5m"
    
    def __init__(self):
        super().__init__("5m", "models/btc_xgb_5m.joblib", "models/btc_xgb_threshold_5m.joblib")
        
    def should_enter(self, df):
        import logging
        if not super().should_enter(df):
            return False
            
        current = df.iloc[-1]
        
        # 5m Features (No Micro-Structure)
        features_list = [
            "bb_width", "rsi", "adx", "dist_from_sma200", "volume_rel",
            "rsi_lag1", "rsi_lag2", "rsi_change",
            "adx_lag1", "adx_lag2", "adx_change",
            "bb_width_lag1", "bb_width_lag2", "bb_width_change",
            "volume_rel_lag1", "volume_rel_lag2", "volume_rel_change",
            "trend_1h"
        ]
        
        try:
            X = current[features_list].values.reshape(1, -1)
            prob = self.model.predict_proba(X)[0][1]
            
            # DETAILED DECISION LOG
            log_msg = (
                f"Breakout Detected! Analying w/ ML...\n"
                f"  > Price: {current['close']:.2f}\n"
                f"  > 1H Trend: {'BULLISH' if current['trend_1h']==1 else 'BEARISH'}\n"
                f"  > RSI: {current['rsi']:.1f} | ADX: {current['adx']:.1f}\n"
                f"  > ML Probability: {prob:.4f} (Threshold: {self.threshold:.4f})"
            )
            
            if prob >= self.threshold:
                logging.info(log_msg + "\n  >>> RESULT: PASS (GO LONG) <<<")
                return True
            else:
                logging.info(log_msg + "\n  >>> RESULT: REJECT (Low Confidence) <<<")
                return False
                
        except Exception as e:
            logging.error(f"ML Prediction Failed: {e}")
            return False

    def should_exit(self, df, position):
        current = df.iloc[-1]
        if current["close"] >= position.entry * 1.0075: return True
        if current["close"] <= position.entry * 0.9950: return True
        return False

class BTCMLStrategy1m(BTCMLStrategyBase):
    name = "btc_ml_1m"
    
    def __init__(self):
        super().__init__("1m", "models/btc_xgb_1m.joblib", "models/btc_xgb_threshold_1m.joblib")
        
    def should_enter(self, df):
        import logging
        if not super().should_enter(df):
            return False
            
        current = df.iloc[-1]
        
        # 1m Features (WITH Micro-Structure)
        features_list = [
            "bb_width", "rsi", "adx", "dist_from_sma200", "volume_rel",
            "rsi_lag1", "rsi_lag2", "rsi_change",
            "adx_lag1", "adx_lag2", "adx_change",
            "bb_width_lag1", "bb_width_lag2", "bb_width_change",
            "volume_rel_lag1", "volume_rel_lag2", "volume_rel_change",
            "trend_1h",
            "body_to_range", "shadow_dominance"
        ]
        
        try:
            X = current[features_list].values.reshape(1, -1)
            prob = self.model.predict_proba(X)[0][1]
            
            # DETAILED DECISION LOG
            log_msg = (
                f"Breakout Detected! Analying w/ ML...\n"
                f"  > Price: {current['close']:.2f}\n"
                f"  > 1H Trend: {'BULLISH' if current['trend_1h']==1 else 'BEARISH'}\n"
                f"  > RSI: {current['rsi']:.1f} | ADX: {current['adx']:.1f}\n"
                f"  > ML Probability: {prob:.4f} (Threshold: {self.threshold:.4f})"
            )
            
            if prob >= self.threshold:
                logging.info(log_msg + "\n  >>> RESULT: PASS (GO LONG) <<<")
                return True
            else:
                logging.info(log_msg + "\n  >>> RESULT: REJECT (Low Confidence) <<<")
                return False
                
        except Exception as e:
            logging.error(f"ML Prediction Failed: {e}")
            return False

    def should_exit(self, df, position):
        current = df.iloc[-1]
        
        # 1. Take Profit (Dynamic)
        if current["close"] >= position.entry * (1 + self.dynamic_tp): 
            return True
            
        # 2. Dynamic Trailing (Breakeven)
        # If we hit +0.30% gain, move stop to Entry + 0.05% (Fees)
        # In backtest we can't "move" stop easily without state, 
        # but we can check if HIGH hit trigger, then CLOSE < Breakeven.
        # But for simple backtest engine, strict stop is safer.
        # Let's implement: If High > Entry * 1.0030, then "Virtual Stop" becomes Entry * 1.0005.
        
        # We need to know if we 'touched' the trigger in this candle or previous ones.
        # Since backtest engine is bar-by-bar, we can assume if High > Trigger, we represent "Protect Mode".
        # But simply:
        
        # 2. Stop Loss (Dynamic)
        # Note: Breakeven logic above is commented out/complex, using simple SL for now
        stop_price = position.entry * (1 - self.dynamic_sl)
        
        if current["close"] <= stop_price: 
            return True
            
        return False
