import json
import os
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_FILE = os.path.join(BASE_DIR, 'data', 'config.json')
STATUS_FILE = os.path.join(BASE_DIR, 'data', 'status.json')

DEFAULT_CONFIG = {
    "stop_loss_pct": 0.5,
    "take_profit_pct": 1.0,
    "risk_per_trade": 1.0, # Not currently used but good for future
    "max_open_positions": 1
}

def load_config():
    """Reads config.json or returns defaults"""
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return DEFAULT_CONFIG

def save_config(config_dict):
    """Writes config.json"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config_dict, f, indent=4)
    except Exception as e:
        print(f"Error saving config: {e}")

def update_status(data):
    """Writes status.json (Price, Balance, etc.)"""
    # specific fields expected: price, balance, position, last_update
    data["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(STATUS_FILE, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Error saving status: {e}")

def get_status():
    """Reads status.json"""
    if not os.path.exists(STATUS_FILE):
        return {}
    try:
        with open(STATUS_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {}
