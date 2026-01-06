import pandas as pd
import numpy as np
import ta
import joblib
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_score, recall_score, accuracy_score
import os
import argparse

if not os.path.exists("models"):
    os.makedirs("models")

import sys
# Fix path to find scripts.download_data from inside scripts/
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.download_data import download_data

def load_data(filepath, timeframe="5m", days=180):
    if not os.path.exists(filepath):
        print(f"Data file {filepath} not found. Attempting auto-download ({days} days)...")
        try:
            download_data("BTC/USDT", timeframe, days, os.path.dirname(filepath))
        except Exception as e:
            print(f"Download failed: {e}")
            return None
            
    if not os.path.exists(filepath):
         return None
         
    df = pd.read_csv(filepath)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df

def feature_engineering(df, strategy_type="5m"):
    df = df.copy()
    
    # 1. Base Indicators
    bb = ta.volatility.BollingerBands(close=df["close"], window=20, window_dev=2)
    df["bb_high"] = bb.bollinger_hband()
    df["bb_width"] = (bb.bollinger_hband() - bb.bollinger_lband()) / bb.bollinger_mavg()
    
    df["rsi"] = ta.momentum.rsi(df["close"], window=14)
    df["adx"] = ta.trend.adx(df["high"], df["low"], df["close"], window=14)
    
    df["sma_200"] = ta.trend.sma_indicator(df["close"], window=200)
    df["dist_from_sma200"] = (df["close"] - df["sma_200"]) / df["sma_200"]
    
    df["volume_sma"] = df["volume"].rolling(window=20).mean()
    df["volume_rel"] = df["volume"] / df["volume_sma"]
    
    # 2. Lagged Features
    for col in ["rsi", "adx", "bb_width", "volume_rel"]:
        df[f"{col}_lag1"] = df[col].shift(1)
        df[f"{col}_lag2"] = df[col].shift(2)
        df[f"{col}_change"] = df[col] - df[f"{col}_lag1"]

    # Feature 5: Multi-Timeframe Trend (1H)
    df_1h = df.resample("1h", on="timestamp").agg({"close": "last"}).dropna()
    df_1h["sma200_1h"] = ta.trend.sma_indicator(df_1h["close"], window=200)
    df_1h = df_1h[["sma200_1h"]]
    
    df = pd.merge_asof(df.sort_values("timestamp"), df_1h.sort_values("timestamp"), on="timestamp", direction="backward")
    df["trend_1h"] = np.where(df["close"] > df["sma200_1h"], 1, -1)
    
    # Feature 6: Candle Micro-Structure (Only for 1m)
    if strategy_type == "1m":
        df["body_size"] = np.abs(df["close"] - df["open"])
        df["upper_shadow"] = df["high"] - np.maximum(df["close"], df["open"])
        df["lower_shadow"] = np.minimum(df["close"], df["open"]) - df["low"]
        
        # Ratios
        df["body_to_range"] = df["body_size"] / (df["high"] - df["low"])
        df["shadow_dominance"] = (df["upper_shadow"] + df["lower_shadow"]) / (df["high"] - df["low"])
    
    # 3. Breakout Signal check
    df["breakout"] = (df["close"] > df["bb_high"]) & (df["close"].shift(1) <= df["bb_high"].shift(1))
    
    # 4. Target Labeling
    df["target"] = 0
    t_horizon = 24 
    
    if strategy_type == "1m":
        # 1m Scalper: 0.4% / 0.25%
        tp = 0.0040
        sl = 0.0025
    else:
        # 5m High-Yield: 0.75% / 0.50%
        tp = 0.0075
        sl = 0.0050
    
    closes = df["close"].values
    highs = df["high"].values
    lows = df["low"].values
    
    targets = []
    for i in range(len(df) - t_horizon):
        curr_close = closes[i]
        window_highs = highs[i+1 : i+1+t_horizon]
        window_lows = lows[i+1 : i+1+t_horizon]
        
        high_chg = window_highs / curr_close - 1
        low_chg = window_lows / curr_close - 1
        
        tp_hit = np.where(high_chg >= tp)[0]
        sl_hit = np.where(low_chg <= -sl)[0]
        
        first_tp = tp_hit[0] if len(tp_hit) > 0 else t_horizon + 1
        first_sl = sl_hit[0] if len(sl_hit) > 0 else t_horizon + 1
        
        if first_tp < first_sl:
            targets.append(1)
        else:
            targets.append(0)
            
    targets.extend([0] * t_horizon)
    df["target"] = targets
    
    return df

def train_model():
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", type=str, default="5m", choices=["1m", "5m"], help="Strategy Type")
    parser.add_argument("--days", type=int, default=180, help="Days of history to use")
    args = parser.parse_args()
    
    strategy_type = args.type
    days = args.days
    print(f"Training Model for Strategy: {strategy_type} (Days: {days})")
    
    # Select Data File
    data_file = "data/historical/BTC_USDT_1m.csv" if strategy_type == "1m" else "data/historical/BTC_USDT_5m.csv"
    
    print(f"Loading data from {data_file}...")
    df = load_data(data_file, timeframe=strategy_type, days=days)
    if df is None: return

    print("Generating enhanced features (XGBoost)...")
    df = feature_engineering(df, strategy_type)
    
    breakout_df = df[df["breakout"] == True]
    print(f"Found {len(breakout_df)} breakout events.")
    
    # Select Features
    base_features = [c for c in df.columns if "lag" in c or "change" in c or c in 
                ["bb_width", "rsi", "adx", "dist_from_sma200", "volume_rel", "trend_1h"]]
    
    if strategy_type == "1m":
        base_features.extend(["body_to_range", "shadow_dominance"])
    
    features = base_features
    print(f"Training on {len(features)} features: {features}")
    
    X = breakout_df[features]
    y = breakout_df["target"]
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print("Training XGBoost Classifier...")
    ratio = float(np.sum(y_train == 0)) / np.sum(y_train == 1)
    
    # Hyperparameter Tuning
    from sklearn.model_selection import RandomizedSearchCV
    
    param_dist = {
        'n_estimators': [100, 200, 300, 500],
        'learning_rate': [0.01, 0.05, 0.1, 0.2],
        'max_depth': [3, 5, 7, 9],
        'subsample': [0.6, 0.8, 1.0],
        'colsample_bytree': [0.6, 0.8, 1.0]
    }
    
    xgb = XGBClassifier(scale_pos_weight=ratio, random_state=42, eval_metric='logloss', n_jobs=1)
    
    search = RandomizedSearchCV(
        xgb, 
        param_distributions=param_dist, 
        n_iter=10, 
        scoring='precision', 
        cv=3, 
        verbose=1, 
        random_state=42,
        n_jobs=1
    )
    
    search.fit(X_train, y_train)
    
    print(f"Best Params: {search.best_params_}")
    clf = search.best_estimator_
    
    print("\n--- Optimizing Confidence Threshold for VOLUME ---")
    y_probs = clf.predict_proba(X_test)[:, 1]
    
    best_thresh = 0.5
    best_trades = 0
    
    # Precision Settings
    # 5m Strategy: Lower Volume needs less strict precision to initiate
    # 1m Strategy: High Volume needs High Precision
    acceptable_precision = 0.70 if strategy_type == "1m" else 0.65
    
    for thresh in np.arange(0.3, 0.95, 0.05):
        y_pred_thresh = (y_probs >= thresh).astype(int)
        num_trades = np.sum(y_pred_thresh)
        
        if num_trades == 0: continue
        
        prec = precision_score(y_test, y_pred_thresh, zero_division=0)
        
        min_trades = 150 if strategy_type == "1m" else 20
        
        if num_trades >= min_trades:
             if prec > acceptable_precision:
                 acceptable_precision = prec
                 best_thresh = thresh
                 best_trades = num_trades
             elif best_trades == 0:
                 acceptable_precision = prec
                 best_thresh = thresh
                 best_trades = num_trades
    
    if best_trades == 0:
        print("Warning: Volume target not met. Forcing 0.60")
        best_thresh = 0.60

    print(f"\nCHOSEN OPTIMAL THRESHOLD: {best_thresh:.2f} (Trades approx in test: {best_trades})")
    
    # Save model and threshold
    model_name = f"models/btc_xgb_{strategy_type}.joblib"
    thresh_name = f"models/btc_xgb_threshold_{strategy_type}.joblib"
    
    joblib.dump(clf, model_name)
    joblib.dump(best_thresh, thresh_name)
    print(f"Model saved to {model_name}")

if __name__ == "__main__":
    train_model()
