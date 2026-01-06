from flask import Flask, render_template_string, request, Response
import pandas as pd
import os

app = Flask(__name__)

# SECURITY: Very basic protection. 
# In production, use Nginx/Apache with proper auth or VPN.
# For this personal bot, a simple query param or Basic Auth is better than nothing.
# Usage: http://IP:5000/?key=mysecretpassword
ACCESS_KEY = "admin123" 

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_FILE = os.path.join(BASE_DIR, 'trading.log')
CSV_FILE = os.path.join(BASE_DIR, 'data', 'live_trades.csv')

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>BTC Bot Dashboard</title>
    <meta http-equiv="refresh" content="30"> <!-- Auto-refresh every 30s -->
    <style>
        body { font-family: monospace; background: #1a1a1a; color: #0f0; padding: 20px; }
        h1 { border-bottom: 1px solid #333; padding-bottom: 10px; }
        .box { background: #111; border: 1px solid #333; padding: 15px; margin-bottom: 20px; border-radius: 5px; }
        textarea { width: 100%; height: 400px; background: #000; color: #ccc; border: none; padding: 10px; font-family: monospace; }
        table { width: 100%; border-collapse: collapse; }
        th, td { border: 1px solid #333; padding: 8px; text-align: left; }
        th { background: #222; }
        .profit { color: #0f0; }
        .loss { color: #f00; }
    </style>
</head>
<body>
    <h1>ðŸ¤– BTC Trading Bot (Live)</h1>
    
    <div class="box">
        <h3>ðŸ“œ Live Logs (Last 100 Lines)</h3>
        <textarea readonly>{{ logs }}</textarea>
    </div>

    <div class="box">
        <h3>ðŸ’° Trade History</h3>
        {% if trades_html %}
            {{ trades_html | safe }}
        {% else %}
            <p>No trades recorded yet.</p>
        {% endif %}
    </div>
</body>
</html>
"""

def check_auth():
    # Simple check: ?key=admin123
    key = request.args.get('key')
    if key != ACCESS_KEY:
        return False
    return True

@app.route('/')
def index():
    if not check_auth():
        return "Access Denied.", 403

    # Read Logs
    logs = ""
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r') as f:
            # Efficiently read last lines
            lines = f.readlines()
            logs = "".join(lines[-100:])
    
    # Read Trades
    trades_html = ""
    if os.path.exists(CSV_FILE):
        try:
            df = pd.read_csv(CSV_FILE)
            # Add some styling classes based on PnL if possible, simply rendering table for now
            trades_html = df.tail(50).to_html(classes='data', border=0, index=False)
            trades_html = trades_html.replace('<th>', '<th style="text-align: left;">')
        except Exception:
            trades_html = "Error reading CSV"

    return render_template_string(HTML_TEMPLATE, logs=logs, trades_html=trades_html)

if __name__ == '__main__':
    # Host 0.0.0.0 allows external access
    app.run(host='0.0.0.0', port=5000)
