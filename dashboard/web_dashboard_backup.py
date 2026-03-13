import os
import json
import time
import secrets
import sys
from datetime import datetime
from functools import wraps
from collections import defaultdict

os.environ["HANSEN_DATA_FILE"] = r"C:\AI\hansen_engine\data\dashboard_cache.json"
sys.path.insert(0, r"C:\AI\hansen_engine")
sys.path.insert(0, r"C:\AI\hansen_engine\dashboard")

from flask import Flask, jsonify, render_template_string, request, redirect, make_response
from modules.market_regime import MarketRegimeDetector
from modules.momentum_engine import MomentumEngine
from modules.top_movers import TopMoversDetector
from modules.volatility_index import VolatilityIndex
from modules.market_intelligence import MarketIntelligence
from modules.insight_engine import InsightEngine
from modules.logger_stats import LoggerStats
from modules.snapshot_stats import SnapshotStats
from modules.upload_tracker import UploadTracker
from modules.health_monitor import HealthMonitor
from dashboard_config import (
    DASHBOARD_HOST, DASHBOARD_PORT,
    DASHBOARD_USERNAME, DASHBOARD_PASSWORD,
    JWT_SECRET, SESSION_TIMEOUT_MINUTES,
    API_PREFIX, RATE_LIMIT_PER_MINUTE,
    MAX_LOGIN_ATTEMPTS, LOGIN_BLOCK_MINUTES,
    SANITIZE_HEADERS
)

app = Flask(__name__)

regime         = MarketRegimeDetector()
momentum       = MomentumEngine()
movers         = TopMoversDetector()
vol_index      = VolatilityIndex()
intel          = MarketIntelligence()
insight        = InsightEngine()
logger_stats   = LoggerStats()
snapshot_stats = SnapshotStats()
upload_tracker = UploadTracker()
health         = HealthMonitor()

# ================================
# SECURITY
# ================================

_active_tokens = {}
_rate_tracker  = defaultdict(list)
_login_fails   = defaultdict(list)
_failed_log    = []

def generate_token():
    raw = secrets.token_hex(32)
    _active_tokens[raw] = time.time() + (SESSION_TIMEOUT_MINUTES * 60)
    return raw

def validate_token(token):
    if not token:
        return False
    expiry = _active_tokens.get(token)
    if not expiry:
        return False
    if time.time() > expiry:
        del _active_tokens[token]
        return False
    _active_tokens[token] = time.time() + (SESSION_TIMEOUT_MINUTES * 60)
    return True

def get_token_from_request():
    token = request.cookies.get("hansen_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    return token

def is_rate_limited(ip):
    now = time.time()
    _rate_tracker[ip] = [t for t in _rate_tracker[ip] if now - t < 60]
    if len(_rate_tracker[ip]) >= RATE_LIMIT_PER_MINUTE:
        return True
    _rate_tracker[ip].append(now)
    return False

def is_login_blocked(ip):
    now = time.time()
    _login_fails[ip] = [t for t in _login_fails[ip] if now - t < LOGIN_BLOCK_MINUTES * 60]
    return len(_login_fails[ip]) >= MAX_LOGIN_ATTEMPTS

def record_login_fail(ip):
    _login_fails[ip].append(time.time())
    _failed_log.append({"ip": ip, "time": datetime.now().isoformat(), "attempts": len(_login_fails[ip])})
    print(f"[SECURITY] Failed login from {ip} — attempt {len(_login_fails[ip])}")

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        ip = request.remote_addr
        if is_rate_limited(ip):
            return jsonify({"error": "rate limited"}), 429
        token = get_token_from_request()
        if not validate_token(token):
            if not request.path.startswith(API_PREFIX):
                return redirect("/login")
            return jsonify({"error": "unauthorized"}), 401
        resp = make_response(f(*args, **kwargs))
        if SANITIZE_HEADERS:
            resp.headers.pop("Server", None)
            resp.headers.pop("X-Powered-By", None)
            resp.headers["X-Content-Type-Options"] = "nosniff"
            resp.headers["X-Frame-Options"] = "DENY"
        return resp
    return decorated

# ================================
# GLOBAL CACHE
# ================================

_cache       = {}
_cache_times = {}
_cache_ttl   = 30

def get_cached(key, fn):
    now = time.time()
    if key in _cache and (now - _cache_times.get(key, 0) < _cache_ttl):
        return _cache[key]
    try:
        result = fn()
        _cache[key] = result
        _cache_times[key] = now
        return result
    except:
        return _cache.get(key, {})

# ================================
# LOGIN PAGE
# ================================

LOGIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Hansen AI — Access</title>
<link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@400;600;700&display=swap" rel="stylesheet">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    background: #080c10;
    color: #c9d1d9;
    font-family: 'Rajdhani', sans-serif;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .login-box {
    background: #0d1117;
    border: 1px solid #1c2a38;
    border-radius: 4px;
    padding: 48px 40px;
    width: 380px;
  }
  .login-title {
    font-size: 20px;
    font-weight: 700;
    color: #00e5ff;
    letter-spacing: 4px;
    text-transform: uppercase;
    margin-bottom: 8px;
  }
  .login-sub {
    font-size: 12px;
    color: #4a5568;
    letter-spacing: 2px;
    margin-bottom: 36px;
  }
  .dot {
    display: inline-block;
    width: 7px; height: 7px;
    border-radius: 50%;
    background: #00ff88;
    margin-right: 8px;
    animation: pulse 2s infinite;
  }
  @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
  .field { margin-bottom: 16px; }
  .field label {
    display: block;
    font-size: 11px;
    letter-spacing: 2px;
    color: #4a5568;
    text-transform: uppercase;
    margin-bottom: 6px;
  }
  .field input {
    width: 100%;
    background: #060a0e;
    border: 1px solid #1c2a38;
    border-radius: 2px;
    padding: 10px 14px;
    color: #c9d1d9;
    font-family: 'Share Tech Mono', monospace;
    font-size: 14px;
    outline: none;
    transition: border-color 0.2s;
  }
  .field input:focus { border-color: #00e5ff; }
  .btn {
    width: 100%;
    background: #00e5ff11;
    border: 1px solid #00e5ff44;
    color: #00e5ff;
    font-family: 'Rajdhani', sans-serif;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 3px;
    text-transform: uppercase;
    padding: 12px;
    border-radius: 2px;
    cursor: pointer;
    margin-top: 8px;
    transition: background 0.2s;
  }
  .btn:hover { background: #00e5ff22; }
  .error   { color: #ff3d5a; font-size: 12px; letter-spacing: 1px; margin-top: 12px; text-align: center; }
  .blocked { color: #ffd600; font-size: 12px; letter-spacing: 1px; margin-top: 12px; text-align: center; }
</style>
</head>
<body>
<div class="login-box">
  <div class="login-title"><span class="dot"></span>Hansen AI</div>
  <div class="login-sub">MARKET INTELLIGENCE SYSTEM</div>
  <div class="field">
    <label>Username</label>
    <input type="text" id="username" placeholder="enter username" autocomplete="off">
  </div>
  <div class="field">
    <label>Password</label>
    <input type="password" id="password" placeholder="enter password">
  </div>
  <button class="btn" onclick="doLogin()">ACCESS SYSTEM</button>
  <div id="msg"></div>
</div>
<script>
document.addEventListener("keydown", e => { if (e.key === "Enter") doLogin(); });
async function doLogin() {
  const username = document.getElementById("username").value;
  const password = document.getElementById("password").value;
  const msg = document.getElementById("msg");
  msg.textContent = "";
  try {
    const res = await fetch("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password })
    });
    const d = await res.json();
    if (d.success) {
      document.cookie = "hansen_token=" + d.token + "; path=/; SameSite=Strict";
      window.location.href = "/";
    } else if (d.blocked) {
      msg.className = "blocked";
      msg.textContent = "Too many attempts. Blocked temporarily.";
    } else {
      msg.className = "error";
      msg.textContent = "Invalid credentials.";
    }
  } catch(e) {
    msg.className = "error";
    msg.textContent = "Connection error.";
  }
}
</script>
</body>
</html>
"""

# ================================
# AUTH ENDPOINTS
# ================================

@app.route("/login")
def login_page():
    return render_template_string(LOGIN_HTML)

@app.route("/auth/login", methods=["POST"])
def do_login():
    ip = request.remote_addr
    if is_login_blocked(ip):
        return jsonify({"success": False, "blocked": True}), 429
    data = request.get_json() or {}
    if data.get("username") == DASHBOARD_USERNAME and data.get("password") == DASHBOARD_PASSWORD:
        token = generate_token()
        print(f"[AUTH] Login success from {ip}")
        return jsonify({"success": True, "token": token})
    record_login_fail(ip)
    return jsonify({"success": False, "blocked": False}), 401

@app.route("/auth/logout")
def do_logout():
    token = get_token_from_request()
    if token and token in _active_tokens:
        del _active_tokens[token]
    resp = make_response(redirect("/login"))
    resp.delete_cookie("hansen_token")
    return resp

# ================================
# API ENDPOINTS
# ================================

@app.route(API_PREFIX + "/market")
@require_auth
def api_market():
    try:
        return jsonify({
            "regime":     get_cached("regime",     regime.market_regime),
            "volatility": get_cached("volatility", vol_index.report),
            "summary":    get_cached("summary",    intel.market_summary),
            "gainers":    get_cached("gainers",    lambda: momentum.top_gainers(5)),
            "losers":     get_cached("losers",     lambda: momentum.top_losers(5)),
            "insight":    get_cached("insight",    insight.analyze_market)
        })
    except Exception as e:
        return jsonify({"error": str(e), "regime": {}, "volatility": {}, "gainers": [], "losers": [], "insight": [], "summary": {}})

@app.route(API_PREFIX + "/system")
@require_auth
def api_system():
    try:
        return jsonify({
            "data_files":      health.check_data_files(),
            "dataset_folders": health.check_dataset_folders(),
            "last_snapshot":   health.last_snapshot_time(),
            "next_snapshot":   snapshot_stats.next_snapshot_eta(),
            "total_records":   logger_stats.total_records(),
            "unique_symbols":  logger_stats.unique_symbols(),
            "uploads":         upload_tracker.total_uploads(),
            "failed_uploads":  upload_tracker.total_failed()
        })
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route(API_PREFIX + "/movers")
@require_auth
def api_movers():
    try:
        return jsonify({
            "top_movers": get_cached("top_movers",     lambda: movers.detect(10)),
            "gainers":    get_cached("movers_gainers", lambda: movers.gainers(10)),
            "losers":     get_cached("movers_losers",  lambda: movers.losers(10)),
            "regime":     get_cached("regime",         regime.market_regime),
            "volatility": get_cached("volatility",     vol_index.report),
            "summary":    get_cached("summary",        intel.market_summary),
            "insight":    get_cached("insight",        insight.analyze_market)
        })
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route(API_PREFIX + "/prices")
@require_auth
def api_prices():
    try:
        cache_file = r"C:\AI\hansen_engine\data\dashboard_cache.json"
        with open(cache_file, "r") as f:
            data = json.load(f)
        top_coins = [
            "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT",
            "DOGEUSDT","ADAUSDT","AVAXUSDT","LINKUSDT","DOTUSDT",
            "MATICUSDT","UNIUSDT","LTCUSDT","ATOMUSDT","NEARUSDT",
            "APTUSDT","OPUSDT","ARBUSDT","INJUSDT","SUIUSDT",
            "TIAUSDT","SEIUSDT","JUPUSDT","WIFUSDT","PEPEUSDT"
        ]
        latest = {}
        for record in data:
            sym = record.get("symbol")
            if sym in top_coins:
                latest[sym] = record.get("price", 0)
        result = [{"symbol": c.replace("USDT",""), "price": latest[c]} for c in top_coins if c in latest]
        return jsonify(result)
    except Exception as e:
        return jsonify([])

@app.route(API_PREFIX + "/security")
@require_auth
def api_security():
    return jsonify({
        "active_sessions": len(_active_tokens),
        "failed_logins":   _failed_log[-20:],
        "blocked_ips":     [ip for ip, t in _login_fails.items() if len(t) >= MAX_LOGIN_ATTEMPTS]
    })

# ================================
# MAIN DASHBOARD
# ================================

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Hansen AI — Market Intelligence</title>
<link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@400;600;700&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #080c10; --panel: #0d1117; --border: #1c2a38;
    --cyan: #00e5ff; --green: #00ff88; --red: #ff3d5a;
    --yellow: #ffd600; --text: #c9d1d9; --dim: #4a5568;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: var(--bg); color: var(--text); font-family: 'Rajdhani', sans-serif; font-size: 15px; min-height: 100vh; }
  header { border-bottom: 1px solid var(--border); padding: 14px 24px; display: flex; align-items: center; justify-content: space-between; background: var(--panel); }
  header h1 { font-size: 18px; font-weight: 700; color: var(--cyan); letter-spacing: 3px; text-transform: uppercase; white-space: nowrap; }
  #clock { font-family: 'Share Tech Mono', monospace; font-size: 13px; color: var(--dim); }
  #status { font-size: 12px; color: var(--dim); }
  .dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%; background: var(--green); margin-right: 6px; animation: pulse 2s infinite; }
  @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
  .logout-btn { font-family: 'Rajdhani', sans-serif; font-size: 11px; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; color: var(--dim); background: none; border: 1px solid #1c2a38; border-radius: 2px; padding: 4px 12px; cursor: pointer; transition: color 0.2s, border-color 0.2s; }
  .logout-btn:hover { color: var(--red); border-color: var(--red); }
  .ticker-wrap { background: #060a0e; border-bottom: 1px solid var(--border); overflow: hidden; height: 34px; display: flex; align-items: center; position: relative; }
  .ticker-wrap::before, .ticker-wrap::after { content: ''; position: absolute; top: 0; bottom: 0; width: 60px; z-index: 2; pointer-events: none; }
  .ticker-wrap::before { left: 0; background: linear-gradient(to right, #060a0e, transparent); }
  .ticker-wrap::after  { right: 0; background: linear-gradient(to left, #060a0e, transparent); }
  .ticker-track { display: flex; animation: ticker-scroll 60s linear infinite; white-space: nowrap; will-change: transform; }
  .ticker-track:hover { animation-play-state: paused; }
  @keyframes ticker-scroll { 0% { transform: translateX(0); } 100% { transform: translateX(-50%); } }
  .ticker-item { display: inline-flex; align-items: center; gap: 6px; padding: 0 20px; font-family: 'Share Tech Mono', monospace; font-size: 12px; border-right: 1px solid #0f1a24; }
  .ticker-symbol { color: var(--dim); font-weight: 600; letter-spacing: 1px; }
  .ticker-price  { color: var(--text); }
  .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; padding: 20px; }
  .grid-wide { display: grid; grid-template-columns: 2fr 1fr; gap: 16px; padding: 0 20px 20px; }
  .panel { background: var(--panel); border: 1px solid var(--border); border-radius: 4px; padding: 16px; }
  .panel-title { font-size: 11px; font-weight: 700; letter-spacing: 3px; color: var(--cyan); text-transform: uppercase; border-bottom: 1px solid var(--border); padding-bottom: 10px; margin-bottom: 14px; }
  .regime-badge { font-size: 28px; font-weight: 700; letter-spacing: 4px; }
  .bull { color: var(--green); } .bear { color: var(--red); } .sideways { color: var(--yellow); } .ranging { color: var(--yellow); } .unknown { color: var(--dim); }
  .breakdown { margin-top: 12px; display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
  .breakdown-item { font-family: 'Share Tech Mono', monospace; font-size: 12px; display: flex; justify-content: space-between; padding: 4px 8px; background: #0a1220; border-radius: 2px; }
  .vol-index { font-size: 32px; font-weight: 700; font-family: 'Share Tech Mono', monospace; color: var(--cyan); margin-bottom: 6px; }
  .vol-level { font-size: 13px; font-weight: 600; letter-spacing: 2px; }
  .stat-row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid var(--border); font-size: 14px; }
  .stat-row:last-child { border-bottom: none; }
  .stat-label { color: var(--dim); }
  .mover-row { display: flex; justify-content: space-between; padding: 5px 0; font-family: 'Share Tech Mono', monospace; font-size: 13px; border-bottom: 1px solid #111820; }
  .mover-row:last-child { border-bottom: none; }
  .pos { color: var(--green); } .neg { color: var(--red); }
  .insight-item { padding: 8px 0; border-bottom: 1px solid var(--border); font-size: 14px; line-height: 1.5; color: var(--text); min-height: 36px; }
  .insight-item:last-child { border-bottom: none; }
  .insight-item::before { content: '▸ '; color: var(--cyan); }
  .cursor { display: inline-block; width: 7px; height: 13px; background: var(--cyan); margin-left: 2px; vertical-align: middle; animation: blink 0.8s step-end infinite; }
  @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
  .summary-coin { padding: 10px 0; border-bottom: 1px solid var(--border); }
  .summary-coin:last-child { border-bottom: none; }
  .coin-name { font-weight: 700; font-size: 14px; margin-bottom: 4px; color: var(--cyan); }
  .coin-stats { display: flex; gap: 16px; font-family: 'Share Tech Mono', monospace; font-size: 12px; }
  .loading { color: var(--dim); font-style: italic; }
</style>
</head>
<body>

<header>
  <h1><span class="dot"></span>Hansen AI — Market Intelligence</h1>
  <div style="display:flex;gap:24px;align-items:center">
    <span id="status">Loading...</span>
    <span id="clock"></span>
    <button class="logout-btn" onclick="logout()">LOGOUT</button>
  </div>
</header>

<div class="ticker-wrap">
  <div class="ticker-track" id="ticker-track">
    <div class="ticker-item"><span class="ticker-symbol">LOADING</span><span class="ticker-price">...</span></div>
  </div>
</div>

<div class="grid">
  <div class="panel"><div class="panel-title">Market Regime</div><div id="regime" class="regime-badge loading">—</div><div id="breakdown" class="breakdown"></div></div>
  <div class="panel"><div class="panel-title">Volatility Index</div><div id="vol-index" class="vol-index">—</div><div id="vol-level" class="vol-level">—</div></div>
  <div class="panel"><div class="panel-title">System Stats</div><div id="system-stats"></div></div>
</div>

<div class="grid" style="padding-top:0">
  <div class="panel"><div class="panel-title">Top Gainers</div><div id="gainers"></div></div>
  <div class="panel"><div class="panel-title">Top Losers</div><div id="losers"></div></div>
  <div class="panel"><div class="panel-title">Market Summary</div><div id="summary"></div></div>
</div>

<div class="grid-wide">
  <div class="panel"><div class="panel-title">Market Insight</div><div id="insight"></div></div>
  <div class="panel"><div class="panel-title">Top Movers</div><div id="movers"></div></div>
</div>

<script>
const API = "API_PREFIX_PLACEHOLDER";

function clock() { document.getElementById("clock").textContent = new Date().toLocaleTimeString(); }
setInterval(clock, 1000); clock();

function logout() {
  document.cookie = "hansen_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
  window.location.href = "/login";
}

let tickerPrices = {}, tickerPrev = {};

function formatPrice(p) {
  if (p >= 1000) return p.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  if (p >= 1)    return p.toFixed(3);
  if (p >= 0.01) return p.toFixed(4);
  return p.toFixed(6);
}

function buildTicker(prices) {
  const items = prices.map(p => {
    const prev = tickerPrev[p.symbol] || p.price;
    const sign = p.price > prev ? "▲" : p.price < prev ? "▼" : "▸";
    const cls  = p.price > prev ? "pos" : p.price < prev ? "neg" : "ticker-symbol";
    return `<div class="ticker-item"><span class="ticker-symbol">${p.symbol}</span><span class="ticker-price">${formatPrice(p.price)}</span><span class="${cls}" style="font-size:10px">${sign}</span></div>`;
  }).join("");
  return items + items;
}

async function loadTicker() {
  try {
    const res = await fetch(API + "/prices");
    if (res.status === 401) { window.location.href = "/login"; return; }
    const prices = await res.json();
    if (!prices.length) return;
    tickerPrev = { ...tickerPrices };
    const fl = prices.map(p => {
      const d = p.price * (Math.random() * 0.0004 - 0.0002);
      tickerPrices[p.symbol] = p.price + d;
      return { symbol: p.symbol, price: p.price + d };
    });
    document.getElementById("ticker-track").innerHTML = buildTicker(fl);
  } catch(e) {}
}

setInterval(() => {
  if (!Object.keys(tickerPrices).length) return;
  const fl = Object.entries(tickerPrices).map(([symbol, price]) => {
    tickerPrev[symbol] = price;
    const d = price * (Math.random() * 0.0004 - 0.0002);
    tickerPrices[symbol] = price + d;
    return { symbol, price: price + d };
  });
  document.getElementById("ticker-track").innerHTML = buildTicker(fl);
}, 3000);

loadTicker();
setInterval(loadTicker, 300000);

let typingQueue = [], lastInsight = [];

function typeInsight(lines) {
  const c = document.getElementById("insight");
  c.innerHTML = "";
  typingQueue = [...lines];
  typeNextLine(c);
}

function typeNextLine(c) {
  if (!typingQueue.length) return;
  const line = typingQueue.shift();
  const div = document.createElement("div");
  div.className = "insight-item";
  const cursor = document.createElement("span");
  cursor.className = "cursor";
  div.appendChild(cursor);
  c.appendChild(div);
  let i = 0;
  function typeChar() {
    if (i < line.length) {
      div.insertBefore(document.createTextNode(line[i++]), cursor);
      setTimeout(typeChar, 18 + Math.random() * 10);
    } else {
      cursor.remove();
      setTimeout(() => typeNextLine(c), 400);
    }
  }
  typeChar();
}

function regimeClass(r) {
  return { bull:"bull", bear:"bear", sideways:"sideways", ranging:"ranging" }[r] || "unknown";
}

async function loadMarket() {
  try {
    const res = await fetch(API + "/movers");
    if (res.status === 401) { window.location.href = "/login"; return; }
    const d = await res.json();

    const regime = d.regime?.regime || "unknown";
    const el = document.getElementById("regime");
    el.textContent = regime.toUpperCase();
    el.className = "regime-badge " + regimeClass(regime);

    document.getElementById("breakdown").innerHTML = Object.entries(d.regime?.breakdown || {}).map(([coin, r]) =>
      `<div class="breakdown-item"><span>${coin.replace("USDT","")}</span><span class="${regimeClass(r)}">${r}</span></div>`
    ).join("");

    const vol = d.volatility;
    document.getElementById("vol-index").textContent = vol?.index ?? "—";
    const lvl = vol?.level || "unknown";
    const lvlEl = document.getElementById("vol-level");
    lvlEl.textContent = lvl.toUpperCase();
    lvlEl.className = "vol-level " + (lvl === "high" ? "neg" : lvl === "medium" ? "ranging" : "bull");

    document.getElementById("gainers").innerHTML = (d.gainers || []).map(g =>
      `<div class="mover-row"><span>${g.symbol.replace("USDT","")}</span><span class="pos">+${g.change_pct}%</span></div>`
    ).join("") || "<div class='loading'>No data</div>";

    document.getElementById("losers").innerHTML = (d.losers || []).map(l =>
      `<div class="mover-row"><span>${l.symbol.replace("USDT","")}</span><span class="neg">${l.change_pct}%</span></div>`
    ).join("") || "<div class='loading'>No data</div>";

    document.getElementById("summary").innerHTML = Object.entries(d.summary || {}).map(([coin, data]) => {
      const mc = data.momentum_1h > 0 ? "pos" : "neg";
      return `<div class="summary-coin"><div class="coin-name">${coin.replace("USDT","")}</div><div class="coin-stats"><span>VOL: ${data.volatility_1h ?? "—"}%</span><span class="${mc}">MOM: ${data.momentum_1h ?? "—"}%</span></div></div>`;
    }).join("") || "<div class='loading'>No data</div>";

    const ni = d.insight || [];
    if (ni.join("|") !== lastInsight.join("|") && ni.length) {
      lastInsight = ni;
      typeInsight(ni);
    } else if (!ni.length) {
      document.getElementById("insight").innerHTML = "<div class='loading'>Building data...</div>";
    }

    document.getElementById("status").textContent = "Live — " + new Date().toLocaleTimeString();
  } catch(e) {
    document.getElementById("status").textContent = "Error: " + e.message;
  }
}

async function loadSystem() {
  try {
    const res = await fetch(API + "/system");
    if (res.status === 401) { window.location.href = "/login"; return; }
    const d = await res.json();
    document.getElementById("system-stats").innerHTML = `
      <div class="stat-row"><span class="stat-label">Total Records</span><span class="pos">${d.total_records?.toLocaleString()}</span></div>
      <div class="stat-row"><span class="stat-label">Unique Symbols</span><span>${d.unique_symbols}</span></div>
      <div class="stat-row"><span class="stat-label">Last Snapshot</span><span>${d.last_snapshot || "never"}</span></div>
      <div class="stat-row"><span class="stat-label">Next Snapshot</span><span class="ranging">${d.next_snapshot}</span></div>
      <div class="stat-row"><span class="stat-label">Uploads</span><span class="pos">${d.uploads}</span></div>
      <div class="stat-row"><span class="stat-label">Failed</span><span class="${d.failed_uploads > 0 ? 'neg' : 'pos'}">${d.failed_uploads}</span></div>
    `;
  } catch(e) {}
}

async function loadMovers() {
  try {
    const res = await fetch(API + "/movers");
    if (res.status === 401) { window.location.href = "/login"; return; }
    const d = await res.json();
    document.getElementById("movers").innerHTML = (d.top_movers || []).map(m => {
      const cls = m.change_pct > 0 ? "pos" : "neg";
      const sign = m.change_pct > 0 ? "+" : "";
      return `<div class="mover-row"><span>${m.symbol.replace("USDT","")}</span><span class="${cls}">${sign}${m.change_pct}%</span></div>`;
    }).join("") || "<div class='loading'>No data</div>";
  } catch(e) {}
}

function refresh() { loadMarket(); loadSystem(); loadMovers(); }
refresh();
setInterval(refresh, 30000);
</script>
</body>
</html>
"""

HTML = HTML.replace("API_PREFIX_PLACEHOLDER", API_PREFIX)

@app.route("/")
@require_auth
def index():
    return render_template_string(HTML)

if __name__ == "__main__":
    app.run(host=DASHBOARD_HOST, port=DASHBOARD_PORT, debug=False)