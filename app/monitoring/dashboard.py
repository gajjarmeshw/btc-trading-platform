from flask import Flask, render_template_string, request, Response
import pandas as pd
import os

app = Flask(__name__)

# SECURITY: Very basic protection. 
# In production, use Nginx/Apache with proper auth or VPN.
# For this personal bot, a simple query param or Basic Auth is better than nothing.
# Usage: http://IP:5000/?key=btc_alpha_secure_777
ACCESS_KEY = os.getenv("DASHBOARD_KEY", "btc_alpha_secure_777") 

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_FILE = os.path.join(BASE_DIR, 'trading.log')
CSV_FILE = os.path.join(BASE_DIR, 'data', 'live_trades.csv')

import sys
sys.path.append(BASE_DIR)

import json
from app.config.dynamic_config import load_config, save_config, get_status

# ... imports ...

# New HTML with Tabs (Status, Logs, Config)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>BTC Bot Control</title>
    <meta http-equiv="refresh" content="30">
    <style>
        body { font-family: monospace; background: #1a1a1a; color: #ccc; padding: 20px; }
        h1 { color: #fff; border-bottom: 2px solid #555; padding-bottom: 10px; }
        .stat-box { display: inline-block; background: #222; padding: 10px 20px; margin-right: 15px; border-radius: 5px; border: 1px solid #444; }
        .stat-val { font-size: 1.2em; font-weight: bold; color: #0f0; }
        .container { display: flex; gap: 20px; margin-top: 20px; }
        .left-panel { flex: 2; }
        .right-panel { flex: 1; }
        .box { background: #111; border: 1px solid #333; padding: 15px; margin-bottom: 20px; border-radius: 5px; }
        textarea { width: 95%; height: 400px; background: #000; color: #0f0; border: 1px solid #333; padding: 10px; }
        table { width: 100%; border-collapse: collapse; }
        th, td { border: 1px solid #333; padding: 8px; font-size: 0.9em; }
        input[type="number"] { background: #222; border: 1px solid #444; color: #fff; padding: 5px; width: 80px; }
        button { background: #0066cc; color: white; border: none; padding: 8px 15px; cursor: pointer; border-radius: 3px; }
        button:hover { background: #0055aa; }
        .success { color: #0f0; }
    </style>
</head>
<body>
    <h1>ðŸ¤– BTC Bot Command Center</h1>
    
    <!-- LIVE STATUS HEADER -->
    <div style="margin-bottom: 20px;">
        <div class="stat-box">Price: <span class="stat-val">${{ status.get('price', 0) }}</span></div>
        <div class="stat-box">Balance: <span class="stat-val">{{ status.get('balance', 'N/A') }}</span></div>
        <div class="stat-box">Position: <span class="stat-val" style="color: {{ 'cyan' if status.get('position')=='LONG' else '#888' }}">{{ status.get('position', 'UNKNOWN') }}</span></div>
        <div class="stat-box">Last Update: <span style="font-size:0.8em">{{ status.get('last_updated', '-') }}</span></div>
    </div>

    <div class="container">
        <!-- LEFT: Logs & Trades -->
        <div class="left-panel">
            <div class="box">
                <h3>ðŸ“œ Live Logs</h3>
                <textarea readonly>{{ logs }}</textarea>
            </div>
            <div class="box">
                <h3>ðŸ’° Trade History</h3>
                {{ trades_html | safe }}
            </div>
        </div>

        <!-- RIGHT: Live Configuration -->
        <div class="right-panel">
            <div class="box" style="border-color: #0066cc;">
                <h3>âš™ï¸  Live Settings</h3>
                <form method="POST" action="?key={{ key }}">
                    <p>
                        <label>Take Profit (%):</label><br>
                        <input type="number" step="0.1" name="take_profit_pct" value="{{ config.get('take_profit_pct', 1.0) }}">
                    </p>
                    <p>
                        <label>Stop Loss (%):</label><br>
                        <input type="number" step="0.1" name="stop_loss_pct" value="{{ config.get('stop_loss_pct', 0.5) }}">
                    </p>
                     <p>
                        <label>Risk Per Trade (%):</label><br>
                        <input type="number" step="0.1" name="risk_per_trade" value="{{ config.get('risk_per_trade', 1.0) }}">
                    </p>
                    <p>
                        <label>Max Positions:</label><br>
                        <input type="number" name="max_open_positions" value="{{ config.get('max_open_positions', 1) }}">
                    </p>
                    <button type="submit">Update Config</button>
                </form>
                <p style="font-size: 0.8em; color: #888; margin-top: 10px;">
                    Changes apply immediately to next trade.<br>
                    Current Strategy: <b>{{ status.get('strategy', '-') }}</b>
                </p>
            </div>
        </div>
    </div>
</body>
</html>
"""

# ... (Auth remains same) ...

@app.route('/', methods=['GET', 'POST'])
def index():
    if not check_auth():
        return "Access Denied.", 403
        
    key = request.args.get('key')
    
    # HANDLE CONFIG UPDATE
    if request.method == 'POST':
        new_config = {
            "take_profit_pct": float(request.form.get('take_profit_pct')),
            "stop_loss_pct": float(request.form.get('stop_loss_pct')),
            "risk_per_trade": float(request.form.get('risk_per_trade')),
            "max_open_positions": int(request.form.get('max_open_positions'))
        }
        save_config(new_config)
    
    # LOAD DATA
    config = load_config()
    status = get_status()

    # Read Logs
    logs = ""
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r') as f:
            lines = f.readlines()
            logs = "".join(lines[-50:]) # Fewer lines for improved UI
    
    # Read Trades
    trades_html = "<p>No trades.</p>"
    if os.path.exists(CSV_FILE):
        try:
            df = pd.read_csv(CSV_FILE)
            if not df.empty:
                trades_html = df.tail(10).to_html(classes='data', border=0, index=False)
                trades_html = trades_html.replace('<th>', '<th style="text-align: left;">')
        except: pass

    return render_template_string(HTML_TEMPLATE, logs=logs, trades_html=trades_html, config=config, status=status, key=key)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
