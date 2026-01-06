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
    <title>BTC Pro Terminal</title>
    <script src="https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js"></script>
    <style>
        :root { --bg: #0d1117; --panel: #161b22; --border: #30363d; --text: #c9d1d9; --green: #2ea043; --red: #da3633; --blue: #58a6ff; }
        body { margin: 0; padding: 0; font-family: 'Segoe UI', monospace; background: var(--bg); color: var(--text); height: 100vh; display: flex; flex-direction: column; }
        
        /* HEADER */
        header { background: var(--panel); border-bottom: 1px solid var(--border); padding: 10px 20px; display: flex; justify-content: space-between; align-items: center; height: 50px; }
        .logo { font-size: 1.2em; font-weight: bold; color: var(--text); display: flex; align-items: center; gap: 10px; }
        .live-indicator { width: 10px; height: 10px; background: var(--green); border-radius: 50%; box-shadow: 0 0 10px var(--green); animation: pulse 2s infinite; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
        
        /* METRICS BAR */
        .metrics { display: flex; gap: 20px; font-size: 0.9em; }
        .metric-item { display: flex; flex-direction: column; }
        .metric-label { font-size: 0.8em; color: #8b949e; }
        .metric-val { font-weight: bold; font-size: 1.1em; }
        
        /* MAIN GRID */
        .grid { display: grid; grid-template-columns: 3fr 1fr; grid-template-rows: 2fr 1fr; gap: 1px; background: var(--border); flex: 1; overflow: hidden; }
        .panel { background: var(--bg); overflow: auto; display: flex; flex-direction: column; }
        .panel-header { background: var(--panel); padding: 8px 15px; font-size: 0.85em; font-weight: bold; border-bottom: 1px solid #30363d; display: flex; justify-content: space-between; position: sticky; top: 0; }
        
        /* CHART */
        #chart-container { width: 100%; height: 100%; position: relative; }
        
        /* CONTROL FORM */
        .control-form { padding: 15px; display: flex; flex-direction: column; gap: 15px; }
        .input-group { display: flex; flex-direction: column; gap: 5px; }
        label { font-size: 0.8em; color: #8b949e; }
        input, select, button { background: #0d1117; border: 1px solid #30363d; color: white; padding: 8px; border-radius: 4px; font-family: monospace; }
        input:focus { border-color: var(--blue); outline: none; }
        button { background: #238636; border: none; font-weight: bold; cursor: pointer; transition: 0.2s; }
        button:hover { background: #2ea043; }
        
        /* LOGS */
        #logs-content { padding: 10px; font-size: 0.8em; white-space: pre-wrap; font-family: monospace; color: #8b949e; flex: 1; overflow-y: auto; }
        .log-line { margin-bottom: 2px; }
        .log-info { color: #58a6ff; }
        .log-warn { color: #d29922; }
        .log-error { color: #f85149; }
        
        /* TRADES TABLE */
        table { width: 100%; border-collapse: collapse; font-size: 0.85em; }
        th, td { text-align: left; padding: 8px; border-bottom: 1px solid #30363d; }
        th { color: #8b949e; }
        .text-green { color: var(--green); }
        .text-red { color: var(--red); }
    </style>
</head>
<body>
    <header>
        <div class="logo"><div class="live-indicator"></div> BTC PRO TERMINAL</div>
        <div class="metrics">
            <div class="metric-item"><span class="metric-label">PRICE</span><span class="metric-val" id="m-price">---</span></div>
            <div class="metric-item"><span class="metric-label">BALANCE</span><span class="metric-val" id="m-balance">---</span></div>
            <div class="metric-item"><span class="metric-label">POSITION</span><span class="metric-val" id="m-pos">---</span></div>
            <div class="metric-item"><span class="metric-label">STRATEGY</span><span class="metric-val" id="m-strat" style="color: var(--blue)">---</span></div>
        </div>
    </header>

    <div class="grid">
        <!-- TOP LEFT: CHART -->
        <div class="panel" style="grid-row: 1 / 2; grid-column: 1 / 2;">
            <div id="chart-container"></div>
        </div>
        
        <!-- TOP RIGHT: CONTROLS -->
        <div class="panel" style="grid-row: 1 / 3; grid-column: 2 / 3; border-left: 1px solid var(--border);">
            <div class="panel-header">STRATEGY & RISK</div>
            <div class="control-form">
                <div class="input-group">
                    <label>ACTIVE STRATEGY</label>
                    <select id="cfg-strat">
                        <option value="btc_ml_1m">ML Scalper (1m)</option>
                        <option value="btc_ml_5m">ML Swing (5m)</option>
                    </select>
                </div>
                <!-- Divider -->
                <div style="height: 1px; background: #30363d; margin: 5px 0;"></div>
                <div class="input-group">
                    <label>TAKE PROFIT (%)</label>
                    <input type="number" step="0.1" id="cfg-tp">
                </div>
                <div class="input-group">
                    <label>STOP LOSS (%)</label>
                    <input type="number" step="0.1" id="cfg-sl">
                </div>
                <div class="input-group">
                    <label>RISK / TRADE (%)</label>
                    <input type="number" step="0.1" id="cfg-risk">
                </div>
                <button onclick="saveConfig()">UPDATE CONFIG</button>
                <div id="cfg-msg" style="font-size: 0.8em; text-align: center; height: 20px;"></div>
            </div>
            
            <div class="panel-header">LATEST TRADES</div>
            <div style="flex: 1; overflow: auto;">
                <table id="trades-table">
                    <thead><tr><th>Time</th><th>Side</th><th>Price</th><th>PnL</th></tr></thead>
                    <tbody></tbody>
                </table>
            </div>
        </div>
        
        <!-- BOTTOM LEFT: LOGS -->
        <div class="panel" style="grid-row: 2 / 3; grid-column: 1 / 2; border-top: 1px solid var(--border);">
            <div class="panel-header">SYSTEM LOGS <span style="font-weight: normal; font-size: 0.8em; margin-left: 10px; opacity: 0.7;">(Auto-scrolling)</span></div>
            <div id="logs-content"></div>
        </div>
    </div>

    <script>
        const API_KEY = "{{ key }}";
        const HEADERS = { 'X-API-KEY': API_KEY, 'Content-Type': 'application/json' };
        
        // --- CHART SETUP ---
        const chartContainer = document.getElementById('chart-container');
        const chart = LightweightCharts.createChart(chartContainer, {
            layout: { background: { type: 'solid', color: '#0d1117' }, textColor: '#c9d1d9' },
            grid: { vertLines: { color: '#161b22' }, horzLines: { color: '#161b22' } },
            timeScale: { timeVisible: true, secondsVisible: false },
        });
        const candleSeries = chart.addCandlestickSeries({
            upColor: '#2ea043', downColor: '#da3633', borderVisible: false, wickUpColor: '#2ea043', wickDownColor: '#da3633'
        });
        
        // Resize Chart
        new ResizeObserver(entries => {
            if (entries.length === 0 || entries[0].target !== chartContainer) { return; }
            const newRect = entries[0].contentRect;
            chart.applyOptions({ width: newRect.width, height: newRect.height });
        }).observe(chartContainer);

        // --- DATA FETCHING ---
        let lastLogLine = "";
        
        async function fetchStatus() {
            try {
                const res = await fetch(`/api/status?key=${API_KEY}`);
                const data = await res.json();
                
                document.getElementById('m-price').innerText = "$" + parseFloat(data.price).toFixed(2);
                document.getElementById('m-balance').innerText = data.balance;
                document.getElementById('m-pos').innerText = data.position;
                document.getElementById('m-pos').style.color = data.position === 'LONG' ? '#2ea043' : '#8b949e';
                document.getElementById('m-strat').innerText = data.strategy.toUpperCase();
                
                // Sync dropdown if not focused
                if (document.activeElement.id !== 'cfg-strat') {
                    document.getElementById('cfg-strat').value = data.strategy;
                }
            } catch(e) { console.error("Status error", e); }
        }
        
        async function fetchConfig() {
            try {
                const res = await fetch(`/api/config?key=${API_KEY}`);
                const data = await res.json();
                document.getElementById('cfg-tp').value = data.take_profit_pct;
                document.getElementById('cfg-sl').value = data.stop_loss_pct;
                document.getElementById('cfg-risk').value = data.risk_per_trade;
            } catch(e) { console.error("Config error", e); }
        }
        
        async function saveConfig() {
            const btn = document.querySelector('button');
            btn.innerText = "SAVING...";
            const payload = {
                strategy_name: document.getElementById('cfg-strat').value,
                take_profit_pct: parseFloat(document.getElementById('cfg-tp').value),
                stop_loss_pct: parseFloat(document.getElementById('cfg-sl').value),
                risk_per_trade: parseFloat(document.getElementById('cfg-risk').value)
            };
            
            try {
                await fetch(`/api/config?key=${API_KEY}`, { method: 'POST', headers: HEADERS, body: JSON.stringify(payload) });
                document.getElementById('cfg-msg').innerText = "Running Update...";
                document.getElementById('cfg-msg').style.color = "#2ea043";
                setTimeout(() => document.getElementById('cfg-msg').innerText = "", 3000);
            } catch(e) {
                alert("Failed to save config");
            }
            btn.innerText = "UPDATE CONFIG";
        }
        
        async function fetchLogs() {
            const res = await fetch(`/api/logs?key=${API_KEY}`);
            const data = await res.json();
            const container = document.getElementById('logs-content');
            
            // Only update if changed (simple check)
            const text = data.logs.join("");
            if (text !== lastLogLine) {
                container.innerHTML = data.logs.map(line => {
                    let cls = "log-line";
                    if (line.includes("ERROR")) cls += " log-error";
                    else if (line.includes("WARNING")) cls += " log-warn";
                    else if (line.includes("SIGNAL")) cls += " log-info";
                    return `<div class="${cls}">${line}</div>`;
                }).join("");
                container.scrollTop = container.scrollHeight;
                lastLogLine = text;
            }
        }
        
        async function fetchTrades() {
            const res = await fetch(`/api/trades?key=${API_KEY}`);
            const data = await res.json();
            const tbody = document.querySelector('#trades-table tbody');
            tbody.innerHTML = data.map(t => `
                <tr>
                    <td>${t.Timestamp.split(' ')[1]}</td>
                    <td class="${t.Side.includes('BUY') ? 'text-green':'text-red'}">${t.Side}</td>
                    <td>${t.Price}</td>
                    <td class="${(t['PnL (USDT)']||"").includes('-') ? 'text-red' : 'text-green'}">${t['PnL (USDT)'] || '-'}</td>
                </tr>
            `).join("");
        }
        
        async function initChart() {
            const res = await fetch(`/api/candles?key=${API_KEY}&limit=500`);
            const data = await res.json();
            candleSeries.setData(data);
            
            // Start Polling
            setInterval(fetchStatus, 2000);
            setInterval(fetchLogs, 2000);
            setInterval(fetchTrades, 5000);
            // Refresh chart every minute
            setInterval(async () => {
                const r = await fetch(`/api/candles?key=${API_KEY}&limit=2`);
                const d = await r.json();
                if (d.length > 0) candleSeries.update(d[d.length-1]);
            }, 5000); 
        }

        // Init
        fetchConfig();
        fetchStatus();
        fetchLogs();
        fetchTrades();
        initChart();
    </script>
</body>
</html>
"""

# ... (Auth remains same) ...

# ... (Previous imports)
import ccxt
from flask import jsonify

# Exchange for Chart Data
public_exchange = ccxt.binance()

def check_auth():
    key = request.args.get('key')
    if not key and request.headers.get('X-API-KEY'): 
        key = request.headers.get('X-API-KEY')
    return key == ACCESS_KEY

@app.route('/api/status')
def api_status():
    if not check_auth(): return jsonify({"error": "Auth failed"}), 403
    return jsonify(get_status())

@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    if not check_auth(): return jsonify({"error": "Auth failed"}), 403
    
    if request.method == 'POST':
        try:
            data = request.json
            current = load_config()
            # Merge updates
            current.update(data)
            save_config(current)
            return jsonify({"status": "ok", "config": current})
        except Exception as e:
            return jsonify({"error": str(e)}), 400
            
    return jsonify(load_config())

@app.route('/api/logs')
def api_logs():
    if not check_auth(): return jsonify({"error": "Auth failed"}), 403
    
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, 'r') as f:
                lines = f.readlines()
                return jsonify({"logs": lines[-100:]}) # Last 100 lines
        except: return jsonify({"logs": []})
    return jsonify({"logs": []})

@app.route('/api/trades')
def api_trades():
    if not check_auth(): return jsonify({"error": "Auth failed"}), 403
    
    trades = []
    if os.path.exists(CSV_FILE):
        try:
            df = pd.read_csv(CSV_FILE)
            trades = df.tail(50).to_dict(orient='records')
        except: pass
    return jsonify(trades)

@app.route('/api/candles')
def api_candles():
    if not check_auth(): return jsonify({"error": "Auth failed"}), 403
    
    timeframe = request.args.get('timeframe', '1m')
    limit = int(request.args.get('limit', 300))
    
    try:
        # Fetch directly from Binance for visualization
        ohlcv = public_exchange.fetch_ohlcv("BTC/USDT", timeframe, limit=limit)
        # Format for Lightweight Charts: { time: '2019-04-11', open: 80.01, high: 96.63, low: 76.6, close: 81.69 }
        formatted = []
        for c in ohlcv:
            # timestamp is ms
            formatted.append({
                "time": c[0] / 1000, 
                "open": c[1],
                "high": c[2],
                "low": c[3],
                "close": c[4],
                "volume": c[5]
            })
        return jsonify(formatted)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def index():
    if not check_auth():
        return "Access Denied.", 403
    
    # Render the PRO UI (We will replace HTML_TEMPLATE next)
    # Passing the key to the template so JS can use it
    key = request.args.get('key')
    return render_template_string(HTML_TEMPLATE, key=key)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
