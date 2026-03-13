import os
import json
import time
import secrets
import sys
from datetime import datetime, timedelta
from functools import wraps
from collections import defaultdict

sys.path.insert(0, r"C:\AI\hansen_engine")
sys.path.insert(0, r"C:\AI\hansen_engine\dashboard")

os.environ["HANSEN_DATA_FILE"] = r"C:\AI\hansen_engine\data\dashboard_cache.json"

from landing_page import LANDING_HTML

from flask import Flask, jsonify, render_template_string, request, redirect, make_response, send_from_directory
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
from modules.derivatives_collector import get_derivatives_data, start_derivatives_collector
from modules.market_data import MarketData
from modules.sector_performance import SectorPerformance
from modules.correlation_matrix import CorrelationMatrix
from modules.alert_engine import AlertEngine
from modules.market_heatmap import MarketHeatmap
from modules.smart_screener import SmartScreener
from modules.sentiment_engine import SentimentEngine
from modules.onchain_intel import OnchainIntel
from modules.ai_reports import AIReports
from modules.market_brain import MarketBrain
from dashboard_config import (
    DASHBOARD_HOST, DASHBOARD_PORT, JWT_SECRET,
    SESSION_TIMEOUT_MINUTES, REMEMBER_ME_DAYS,
    API_PREFIX, RATE_LIMIT_PER_MINUTE,
    MAX_LOGIN_ATTEMPTS, LOGIN_BLOCK_MINUTES,
    SANITIZE_HEADERS, WALLETS, PLANS,
    PAYMENT_MIN_USDT, PAYMENT_MIN_BTC,
    TRIAL_ROLE, TRIAL_DURATION_DAYS
)
from db_manager import (
    init_db, bootstrap_admin,
    get_user, get_all_users, create_user, update_user, delete_user,
    extend_subscription, update_last_login, is_subscription_active,
    verify_password, generate_password,
    create_session, validate_session, delete_session, refresh_session,
    create_payment, confirm_payment, get_pending_payments, get_all_payments,
    log_action, get_audit_log
)
from email_service import (
    send_welcome_email, send_trial_email,
    send_payment_pending_email
)

# ================================
# INIT
# ================================

init_db()
bootstrap_admin()
from expiry_checker import start_expiry_checker
start_expiry_checker()
from payment_detector import start_payment_detector
start_payment_detector()

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
sector_perf    = SectorPerformance(market_store=None, market_data=MarketData())
sector_perf._cache_ttl = 300
corr_matrix    = CorrelationMatrix(market_store=None, market_data=MarketData())
corr_matrix._cache_ttl = 300
alert_engine   = AlertEngine(market_data=MarketData())
market_heatmap = MarketHeatmap(market_data=MarketData())
market_heatmap._cache_ttl = 300
smart_screener    = SmartScreener(market_data=MarketData())
smart_screener._cache_ttl = 300
sentiment_engine  = SentimentEngine(market_data=MarketData())
sentiment_engine._cache_ttl = 300
onchain_intel     = OnchainIntel(market_data=MarketData())
onchain_intel._cache_ttl = 300
ai_reports        = AIReports(market_data=MarketData(), sector_perf=sector_perf, sentiment=sentiment_engine, alert_engine=alert_engine, onchain=onchain_intel, screener=smart_screener)
market_brain      = MarketBrain(market_data=MarketData(), sector_perf=sector_perf, correlation=corr_matrix, alert_engine=alert_engine, sentiment=sentiment_engine, onchain=onchain_intel, screener=smart_screener)
ai_reports.market_brain = market_brain
market_brain.modules["derivatives_fn"] = get_derivatives_data
start_derivatives_collector()
# ================================
# RATE LIMITING
# ================================

_rate_tracker = defaultdict(list)
_login_fails  = defaultdict(list)

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
    print(f"[SECURITY] Failed login from {ip} — attempt {len(_login_fails[ip])}")

# ================================
# AUTH DECORATOR
# ================================

def get_current_user():
    token = request.cookies.get("hansen_token")
    if not token:
        return None
    session = validate_session(token)
    if not session:
        return None
    refresh_session(token)
    return session

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        ip = request.remote_addr
        if is_rate_limited(ip):
            if request.path.startswith(API_PREFIX):
                return jsonify({"error": "rate limited"}), 429
            return redirect("/login")
        session = get_current_user()
        if not session:
            if request.path.startswith(API_PREFIX):
                return jsonify({"error": "unauthorized"}), 401
            return redirect("/login")
        resp = make_response(f(*args, **kwargs))
        if SANITIZE_HEADERS:
            resp.headers.pop("Server", None)
            resp.headers.pop("X-Powered-By", None)
            resp.headers["X-Content-Type-Options"] = "nosniff"
            resp.headers["X-Frame-Options"] = "DENY"
        return resp
    return decorated

def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        session = get_current_user()
        if not session or session.get("role") != "admin":
            return jsonify({"error": "forbidden"}), 403
        return f(*args, **kwargs)
    return decorated

# ================================
# CACHE
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
# AUTH ENDPOINTS
# ================================

@app.route("/")
def landing():
    return render_template_string(LANDING_HTML)

@app.route("/dashboard")
@require_auth
def index():
    session = get_current_user()
    role = session.get("role", "viewer") if session else "viewer"
    html = HTML.replace("ROLE_PLACEHOLDER", role)
    return render_template_string(html)

@app.route("/login")
def login_page():
    return render_template_string(LOGIN_HTML)

@app.route("/register")
def register_page():
    return render_template_string(REGISTER_HTML)

@app.route("/auth/login", methods=["POST"])
def do_login():
    ip = request.remote_addr
    if is_login_blocked(ip):
        return jsonify({"success": False, "blocked": True}), 429
    data = request.get_json() or {}
    username    = data.get("username", "").strip()
    password    = data.get("password", "")
    remember_me = data.get("remember_me", False)

    user = get_user(username)
    if not user or not verify_password(password, user["password"]):
        record_login_fail(ip)
        log_action(username, "login_failed", ip)
        return jsonify({"success": False, "blocked": False}), 401

    if not user["active"]:
        return jsonify({"success": False, "error": "account_disabled"}), 403

    if not is_subscription_active(user):
        return jsonify({"success": False, "error": "subscription_expired"}), 403

    token = create_session(user["id"], remember_me=remember_me)
    update_last_login(username)
    log_action(username, "login_success", ip)
    print(f"[AUTH] Login: {username} from {ip}")
    return jsonify({"success": True, "token": token, "role": user["role"]})

@app.route("/auth/logout")
def do_logout():
    token = request.cookies.get("hansen_token")
    if token:
        delete_session(token)
    resp = make_response(redirect("/login"))
    resp.delete_cookie("hansen_token")
    return resp

# ================================
# PAYMENT FLOW
# ================================

@app.route("/subscribe", methods=["POST"])
def subscribe():
    data     = request.get_json() or {}
    email    = data.get("email", "").strip().lower()
    chain    = data.get("chain", "")
    currency = data.get("currency", "USDT")
    plan     = data.get("plan", "analyst")

    if not email or not chain:
        return jsonify({"error": "email and chain required"}), 400

    amount  = PLANS[plan]["price_btc"] if currency == "BTC" else PLANS[plan]["price_usdt"]
    wallet  = WALLETS.get(chain, "")

    if not wallet:
        return jsonify({"error": "invalid chain"}), 400

    payment_id = create_payment(email, chain, amount, currency, plan)
    send_payment_pending_email(email, payment_id, chain, amount, currency, wallet)
    log_action(email, "payment_initiated", request.remote_addr, f"chain={chain} amount={amount}{currency}")

    return jsonify({
        "success":    True,
        "payment_id": payment_id,
        "wallet":     wallet,
        "amount":     amount,
        "currency":   currency,
        "chain":      chain
    })

# ================================
# ADMIN API
# ================================

@app.route(API_PREFIX + "/admin/users")
@require_auth
@require_admin
def admin_get_users():
    return jsonify(get_all_users())

@app.route(API_PREFIX + "/admin/users/create", methods=["POST"])
@require_auth
@require_admin
def admin_create_user():
    data     = request.get_json() or {}
    email    = data.get("email", "").strip().lower()
    role     = data.get("role", "viewer")
    days     = int(data.get("days", 30))
    is_trial = data.get("trial", False)

    if not email:
        return jsonify({"error": "email required"}), 400

    username = email.split("@")[0].lower().replace(".", "_")
    password = generate_password()

    # Ensure unique username
    base = username
    i = 1
    while get_user(username):
        username = f"{base}{i}"
        i += 1

    ok = create_user(username, password, email=email, role=role, expires_days=days)
    if not ok:
        return jsonify({"error": "user already exists"}), 409

    from db_manager import get_user as gu
    user = gu(username)
    if is_trial:
        send_trial_email(email, username, password, user["expires_at"])
    else:
        send_welcome_email(email, username, password, role, user["expires_at"])

    log_action("admin", "user_created", request.remote_addr, f"user={username} role={role}")
    return jsonify({"success": True, "username": username, "password": password})

@app.route(API_PREFIX + "/admin/users/update", methods=["POST"])
@require_auth
@require_admin
def admin_update_user():
    data     = request.get_json() or {}
    username = data.get("username")
    if not username:
        return jsonify({"error": "username required"}), 400
    allowed = {k: v for k, v in data.items() if k in {"role", "active", "expires_at"}}
    update_user(username, **allowed)
    log_action("admin", "user_updated", request.remote_addr, f"user={username}")
    return jsonify({"success": True})

@app.route(API_PREFIX + "/admin/users/extend", methods=["POST"])
@require_auth
@require_admin
def admin_extend_user():
    data     = request.get_json() or {}
    username = data.get("username")
    days     = int(data.get("days", 30))
    extend_subscription(username, days)
    log_action("admin", "subscription_extended", request.remote_addr, f"user={username} days={days}")
    return jsonify({"success": True})

@app.route(API_PREFIX + "/admin/users/delete", methods=["POST"])
@require_auth
@require_admin
def admin_delete_user():
    data     = request.get_json() or {}
    username = data.get("username")
    delete_user(username)
    log_action("admin", "user_deleted", request.remote_addr, f"user={username}")
    return jsonify({"success": True})

@app.route(API_PREFIX + "/admin/payments")
@require_auth
@require_admin
def admin_payments():
    return jsonify(get_all_payments())

@app.route(API_PREFIX + "/admin/payments/confirm", methods=["POST"])
@require_auth
@require_admin
def admin_confirm_payment():
    data       = request.get_json() or {}
    payment_id = data.get("payment_id")
    tx_hash    = data.get("tx_hash", "manual")
    confirm_payment(payment_id, tx_hash)

    # Get payment and create/extend user
    from db_manager import get_conn
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM payments WHERE id = ?", (payment_id,))
    payment = dict(c.fetchone())
    conn.close()

    email    = payment["email"]
    plan     = payment["plan"]
    role     = plan
    days     = PLANS[plan]["duration_days"]

    existing = get_user(email.split("@")[0].lower().replace(".", "_"))
    if existing:
        extend_subscription(existing["username"], days)
    else:
        username = email.split("@")[0].lower().replace(".", "_")
        password = generate_password()
        create_user(username, password, email=email, role=role, expires_days=days)
        from db_manager import get_user as gu
        user = gu(username)
        send_welcome_email(email, username, password, role, user["expires_at"])

    log_action("admin", "payment_confirmed", request.remote_addr, f"id={payment_id}")
    return jsonify({"success": True})

@app.route(API_PREFIX + "/admin/audit")
@require_auth
@require_admin
def admin_audit():
    return jsonify(get_audit_log(100))

# ================================
# MARKET API
# ================================

@app.route(API_PREFIX + "/movers")
@require_auth
def api_movers():
    session = get_current_user()
    role    = session.get("role", "viewer") if session else "viewer"
    try:
        data = {
            "top_movers": get_cached("top_movers",     lambda: movers.detect(10)),
            "gainers":    get_cached("movers_gainers", lambda: movers.gainers(10)),
            "losers":     get_cached("movers_losers",  lambda: movers.losers(10)),
            "regime":     get_cached("regime",         regime.market_regime),
            "volatility": get_cached("volatility",     vol_index.report),
            "summary":    get_cached("summary",        intel.market_summary),
        }
        # Insight only for analyst/admin
        if role in ("analyst", "admin"):
            data["insight"] = get_cached("insight", insight.analyze_market)
        else:
            data["insight"] = ["Upgrade to Analyst to unlock AI insights"]
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)})

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

@app.route(API_PREFIX + "/prices")
@require_auth
def api_prices():
    try:
        with open(r"C:\AI\hansen_engine\data\dashboard_cache.json", "r") as f:
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
    except:
        return jsonify([])

@app.route(API_PREFIX + "/derivatives")
@require_auth
def api_derivatives():
    return jsonify(get_derivatives_data())

@app.route("/api/v1/sector-performance")
def api_sector_performance():
    """P2: Sector performance ranking multi-timeframe"""
    try:
        timeframe = request.args.get("tf", "24h")
        data = sector_perf.get_sector_summary()
        return jsonify({"status": "ok", "data": data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/v1/sector-ranking")
def api_sector_ranking():
    """P2: Sector ranking by performance"""
    try:
        timeframe = request.args.get("tf", "24h")
        data = sector_perf.get_sector_ranking(timeframe)
        return jsonify({"status": "ok", "data": data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/v1/correlation")
def api_correlation():
    """P2: Correlation matrix + beta vs BTC"""
    try:
        window = request.args.get("window", "7d")
        data = corr_matrix.get_correlation_summary(window)
        return jsonify({"status": "ok", "data": data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/v1/alerts")
def api_alerts():
    try:
        alert_engine.run_full_scan()
        data = alert_engine.get_alert_summary()
        return jsonify({"status": "ok", "data": data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/v1/heatmap")
def api_heatmap():
    try:
        tf = request.args.get("tf", "24h")
        data = market_heatmap.get_heatmap_summary(tf)
        return jsonify({"status": "ok", "data": data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/v1/screener")
def api_screener():
    try:
        preset = request.args.get("preset", None)
        data = smart_screener.get_screener_summary() if not preset else smart_screener.screen(preset=preset, limit=20)
        return jsonify({"status": "ok", "data": data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/v1/sentiment")
def api_sentiment():
    try:
        sector_data = sector_perf.get_sector_ranking("24h")
        data = sentiment_engine.get_sentiment_summary(sector_data)
        return jsonify({"status": "ok", "data": data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/v1/onchain")
def api_onchain():
    try:
        data = onchain_intel.get_onchain_summary()
        return jsonify({"status": "ok", "data": data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/v1/reports")
def api_reports():
    try:
        data = ai_reports.get_reports_summary()
        return jsonify({"status": "ok", "data": data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/v1/reports/generate")
def api_generate_report():
    try:
        report_type = request.args.get("type", "daily")
        use_llm = request.args.get("llm", "true").lower() == "true"
        data = ai_reports.generate_report(report_type, use_llm)
        return jsonify({"status": "ok", "data": data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/v1/brain")
def api_brain():
    try:
        data = market_brain.get_brain_summary()
        return jsonify({"status": "ok", "data": data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/v1/brain/context")
def api_brain_context():
    try:
        data = market_brain.collect_full_context()
        return jsonify({"status": "ok", "data": data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/v1/ai-insight")
def api_ai_insight():
    try:
        insight_file = r"C:\AI\hansen_engine\data\latest_ai_insight.json"
        if os.path.exists(insight_file):
            with open(insight_file, "r") as f:
                data = json.load(f)
            return jsonify({"status": "ok", "data": data})
        return jsonify({"status": "ok", "data": {"analysis": "No AI insight yet — waiting for next snapshot cycle"}})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ================================
# MAIN ROUTES
# ================================

@app.route('/favicon.ico')
def favicon():
    return send_from_directory('.', 'favicon.ico')

@app.route("/admin")
@require_auth
def admin_panel():
    session = get_current_user()
    if not session or session.get("role") != "admin":
        return redirect("/login")
    return render_template_string(ADMIN_HTML)

# ================================
# LOGIN HTML
# ================================

LOGIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Hansen AI — Access</title>
<link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@400;600;700&display=swap" rel="stylesheet">
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { background:#080c10; color:#c9d1d9; font-family:'Rajdhani',sans-serif; min-height:100vh; display:flex; align-items:center; justify-content:center; }
  .box { background:#0d1117; border:1px solid #1c2a38; border-radius:4px; padding:56px 52px; width:520px; }
  .title { font-size:28px; font-weight:700; color:#00e5ff; letter-spacing:4px; text-transform:uppercase; margin-bottom:6px; }
  .sub { font-size:11px; color:#4a5568; letter-spacing:2px; margin-bottom:36px; }
  .dot { display:inline-block; width:7px; height:7px; border-radius:50%; background:#00ff88; margin-right:8px; animation:pulse 2s infinite; }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
  .field { margin-bottom:16px; }
  .field label { display:block; font-size:11px; letter-spacing:2px; color:#4a5568; text-transform:uppercase; margin-bottom:6px; }
  .field input { width:100%; background:#060a0e; border:1px solid #1c2a38; border-radius:2px; padding:12px 14px; color:#c9d1d9; font-family:'Share Tech Mono',monospace; font-size:14px; outline:none; transition:border-color 0.2s; }
  .field input:focus { border-color:#00e5ff; }
  .remember { display:flex; align-items:center; gap:8px; margin-bottom:16px; font-size:13px; color:#4a5568; cursor:pointer; }
  .remember input { width:auto; }
  .btn { width:100%; background:#00e5ff11; border:1px solid #00e5ff44; color:#00e5ff; font-family:'Rajdhani',sans-serif; font-size:14px; font-weight:700; letter-spacing:3px; text-transform:uppercase; padding:13px; border-radius:2px; cursor:pointer; transition:background 0.2s; }
  .btn:hover { background:#00e5ff22; }
  .btn-trial { width:100%; background:transparent; border:1px solid #1c2a38; color:#4a5568; font-family:'Rajdhani',sans-serif; font-size:12px; font-weight:600; letter-spacing:2px; text-transform:uppercase; padding:10px; border-radius:2px; cursor:pointer; margin-top:10px; transition:all 0.2s; }
  .btn-trial:hover { border-color:#ffd600; color:#ffd600; }
  .divider { border:none; border-top:1px solid #1c2a38; margin:20px 0; }
  .error   { color:#ff3d5a; font-size:12px; margin-top:12px; text-align:center; }
  .blocked { color:#ffd600; font-size:12px; margin-top:12px; text-align:center; }
  .success { color:#00ff88; font-size:12px; margin-top:12px; text-align:center; }
</style>
</head>
<body>
<div class="box">
  <div class="title"><span class="dot"></span>Hansen AI</div>
  <div class="sub">MARKET INTELLIGENCE SYSTEM</div>
  <div class="field"><label>Username</label><input type="text" id="username" placeholder="enter username" autocomplete="off"></div>
  <div class="field"><label>Password</label><input type="password" id="password" placeholder="enter password"></div>
  <label class="remember"><input type="checkbox" id="remember"> Remember me for 30 days</label>
  <button class="btn" onclick="doLogin()">ACCESS SYSTEM</button>
  <hr class="divider">
  <button class="btn-trial" onclick="window.location.href='/register'">REQUEST TRIAL ACCESS</button>
  <div id="msg"></div>
</div>
<script>
document.addEventListener("keydown", e => { if (e.key === "Enter") doLogin(); });
async function doLogin() {
  const username    = document.getElementById("username").value;
  const password    = document.getElementById("password").value;
  const remember_me = document.getElementById("remember").checked;
  const msg = document.getElementById("msg");
  msg.textContent = "";
  try {
    const res = await fetch("/auth/login", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({username, password, remember_me})
    });
    const d = await res.json();
    if (d.success) {
      if (remember_me) {
        document.cookie = `hansen_token=${d.token}; path=/; SameSite=Strict; max-age=${30*24*3600}`;
      } else {
        document.cookie = `hansen_token=${d.token}; path=/; SameSite=Strict`;
      }
      window.location.href = "/dashboard";
    } else if (d.blocked) {
      msg.className = "blocked"; msg.textContent = "Too many attempts. Blocked temporarily.";
    } else if (d.error === "subscription_expired") {
      msg.className = "error"; msg.textContent = "Subscription expired. Please renew.";
    } else if (d.error === "account_disabled") {
      msg.className = "error"; msg.textContent = "Account disabled. Contact admin.";
    } else {
      msg.className = "error"; msg.textContent = "Invalid credentials.";
    }
  } catch(e) {
    msg.className = "error"; msg.textContent = "Connection error.";
  }
}
</script>
</body>
</html>
"""

# ================================
# REGISTER / TRIAL HTML
# ================================

REGISTER_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Hansen AI — Trial Access</title>
<link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@400;600;700&display=swap" rel="stylesheet">
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { background:#080c10; color:#c9d1d9; font-family:'Rajdhani',sans-serif; min-height:100vh; display:flex; align-items:center; justify-content:center; }
  .box { background:#0d1117; border:1px solid #1c2a38; border-radius:4px; padding:48px 40px; width:460px; }
  .title { font-size:28px; font-weight:700; color:#00e5ff; letter-spacing:4px; text-transform:uppercase; margin-bottom:6px; }
  .sub { font-size:11px; color:#4a5568; letter-spacing:2px; margin-bottom:8px; }
  .badge { display:inline-block; background:#ffd60022; border:1px solid #ffd60044; color:#ffd600; font-size:11px; letter-spacing:2px; padding:4px 10px; border-radius:2px; margin-bottom:28px; }
  .field { margin-bottom:16px; }
  .field label { display:block; font-size:11px; letter-spacing:2px; color:#4a5568; text-transform:uppercase; margin-bottom:6px; }
  .field input, .field select { width:100%; background:#060a0e; border:1px solid #1c2a38; border-radius:2px; padding:12px 14px; color:#c9d1d9; font-family:'Share Tech Mono',monospace; font-size:13px; outline:none; transition:border-color 0.2s; }
  .field input:focus, .field select:focus { border-color:#00e5ff; }
  .field select option { background:#0d1117; }
  .btn { width:100%; background:#ffd60011; border:1px solid #ffd60044; color:#ffd600; font-family:'Rajdhani',sans-serif; font-size:14px; font-weight:700; letter-spacing:3px; text-transform:uppercase; padding:13px; border-radius:2px; cursor:pointer; transition:background 0.2s; }
  .btn:hover { background:#ffd60022; }
  .back { display:block; text-align:center; margin-top:14px; color:#4a5568; font-size:12px; cursor:pointer; }
  .back:hover { color:#00e5ff; }
  .error   { color:#ff3d5a; font-size:12px; margin-top:12px; text-align:center; }
  .success { color:#00ff88; font-size:13px; margin-top:12px; text-align:center; line-height:1.6; }
</style>
</head>
<body>
<div class="box">
  <div class="title">Trial Access</div>
  <div class="sub">HANSEN AI MARKET INTELLIGENCE</div>
  <div class="badge">30 DAYS ANALYST — FREE</div>
  <div class="field"><label>Email</label><input type="email" id="email" placeholder="your@email.com"></div>
  <button class="btn" onclick="requestTrial()">REQUEST TRIAL</button>
  <span class="back" onclick="window.location.href='/login'">← Back to login</span>
  <div id="msg"></div>
</div>
<script>
async function requestTrial() {
  const email = document.getElementById("email").value.trim();
  const msg = document.getElementById("msg");
  msg.textContent = "";
  if (!email) { msg.className="error"; msg.textContent="Email required."; return; }
  try {
    const res = await fetch("/api/trial", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({email})
    });
    const d = await res.json();
    if (d.success) {
      msg.className = "success";
      msg.textContent = "Trial activated! Check your email for login credentials.";
    } else {
      msg.className = "error";
      msg.textContent = d.error || "Request failed.";
    }
  } catch(e) {
    msg.className = "error"; msg.textContent = "Connection error.";
  }
}
</script>
</body>
</html>
"""

@app.route("/api/trial", methods=["POST"])
def request_trial():
    ip = request.remote_addr

    # Cek IP udah pernah dapet trial (90 hari)
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT COUNT(*) FROM audit_log
        WHERE action = 'trial_requested' AND ip = ?
        AND timestamp > ?
    """, (ip, (datetime.now() - timedelta(days=90)).isoformat()))
    count = c.fetchone()[0]
    conn.close()
    if count >= 1:
        return jsonify({"error": "Trial already used from this network"}), 429

    data  = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    if not email or "@" not in email:
        return jsonify({"error": "valid email required"}), 400

    from db_manager import get_user_by_email
    if get_user_by_email(email):
        return jsonify({"error": "email already registered"}), 409

    username = email.split("@")[0].lower().replace(".", "_")
    password = generate_password()
    base = username
    i = 1
    while get_user(username):
        username = f"{base}{i}"
        i += 1

    expires_days = TRIAL_DURATION_DAYS
    ok = create_user(username, password, email=email, role=TRIAL_ROLE, expires_days=expires_days)
    if not ok:
        return jsonify({"error": "failed to create account"}), 500

    from db_manager import get_user as gu
    user = gu(username)
    send_trial_email(email, username, password, user["expires_at"])
    log_action(username, "trial_requested", ip, email)
    return jsonify({"success": True})

# ================================
# ADMIN HTML
# ================================

ADMIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Hansen AI — Admin</title>
<link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@400;600;700&display=swap" rel="stylesheet">
<style>
  :root { --bg:#080c10; --panel:#0d1117; --border:#1c2a38; --cyan:#00e5ff; --green:#00ff88; --red:#ff3d5a; --yellow:#ffd600; --text:#c9d1d9; --dim:#4a5568; }
  * { margin:0; padding:0; box-sizing:border-box; }
  body { background:var(--bg); color:var(--text); font-family:'Rajdhani',sans-serif; font-size:14px; }
  header { background:var(--panel); border-bottom:1px solid var(--border); padding:14px 24px; display:flex; justify-content:space-between; align-items:center; }
  header h1 { color:var(--cyan); font-size:16px; letter-spacing:3px; text-transform:uppercase; }
  .nav { display:flex; gap:8px; padding:16px 24px; border-bottom:1px solid var(--border); }
  .tab { background:none; border:1px solid var(--border); color:var(--dim); font-family:'Rajdhani',sans-serif; font-size:12px; letter-spacing:2px; text-transform:uppercase; padding:6px 16px; border-radius:2px; cursor:pointer; transition:all 0.2s; }
  .tab.active, .tab:hover { border-color:var(--cyan); color:var(--cyan); }
  .content { padding:24px; }
  .section { display:none; }
  .section.active { display:block; }
  table { width:100%; border-collapse:collapse; }
  th { text-align:left; font-size:10px; letter-spacing:2px; color:var(--dim); text-transform:uppercase; padding:8px 12px; border-bottom:1px solid var(--border); }
  td { padding:10px 12px; border-bottom:1px solid #0f1822; font-family:'Share Tech Mono',monospace; font-size:12px; }
  tr:hover td { background:#0d1420; }
  .badge { display:inline-block; font-size:10px; letter-spacing:1px; padding:2px 8px; border-radius:2px; }
  .badge-admin    { background:#00e5ff22; color:#00e5ff; border:1px solid #00e5ff44; }
  .badge-analyst  { background:#00ff8822; color:#00ff88; border:1px solid #00ff8844; }
  .badge-viewer   { background:#ffd60022; color:#ffd600; border:1px solid #ffd60044; }
  .badge-active   { background:#00ff8822; color:#00ff88; }
  .badge-inactive { background:#ff3d5a22; color:#ff3d5a; }
  .btn-sm { background:none; border:1px solid var(--border); color:var(--dim); font-family:'Rajdhani',sans-serif; font-size:11px; letter-spacing:1px; padding:3px 10px; border-radius:2px; cursor:pointer; transition:all 0.2s; }
  .btn-sm:hover { border-color:var(--cyan); color:var(--cyan); }
  .btn-sm.danger:hover { border-color:var(--red); color:var(--red); }
  .form-row { display:flex; gap:12px; margin-bottom:16px; flex-wrap:wrap; }
  .form-row input, .form-row select { background:#060a0e; border:1px solid var(--border); color:var(--text); font-family:'Share Tech Mono',monospace; font-size:13px; padding:8px 12px; border-radius:2px; outline:none; }
  .form-row input:focus, .form-row select:focus { border-color:var(--cyan); }
  .btn-action { background:#00e5ff11; border:1px solid #00e5ff44; color:#00e5ff; font-family:'Rajdhani',sans-serif; font-size:12px; letter-spacing:2px; text-transform:uppercase; padding:8px 20px; border-radius:2px; cursor:pointer; transition:background 0.2s; }
  .btn-action:hover { background:#00e5ff22; }
  .msg { font-size:12px; margin-top:10px; }
  .back-btn { background:none; border:1px solid #aabbcc; color:#aabbcc; font-family:'Rajdhani',sans-serif; font-size:11px; letter-spacing:2px; padding:5px 14px; border-radius:2px; cursor:pointer; }
  .back-btn:hover { border-color:#00e5ff; color:#00e5ff; }
</style>
</head>
<body>
<header>
  <h1>Hansen AI — Admin Panel</h1>
  <div style="display:flex;gap:12px;align-items:center">
    <button class="back-btn" onclick="window.location.href='/dashboard'">DASHBOARD</button>
    <button class="back-btn" onclick="window.location.href='/auth/logout'">LOGOUT</button>
  </div>
</header>

<div class="nav">
  <button class="tab active" onclick="showTab('users')">USERS</button>
  <button class="tab" onclick="showTab('create')">CREATE USER</button>
  <button class="tab" onclick="showTab('payments')">PAYMENTS</button>
  <button class="tab" onclick="showTab('audit')">AUDIT LOG</button>
</div>

<div class="content">

  <div id="tab-users" class="section active">
    <h3 style="color:var(--cyan);letter-spacing:2px;margin-bottom:16px;font-size:13px">ALL USERS</h3>
    <table>
      <thead><tr><th>Username</th><th>Email</th><th>Role</th><th>Expires</th><th>Last Login</th><th>Status</th><th>Actions</th></tr></thead>
      <tbody id="users-table"></tbody>
    </table>
  </div>

  <div id="tab-create" class="section">
    <h3 style="color:var(--cyan);letter-spacing:2px;margin-bottom:20px;font-size:13px">CREATE USER</h3>
    <div class="form-row">
      <input type="email" id="new-email" placeholder="user@email.com" style="flex:1;min-width:200px">
      <select id="new-role">
        <option value="viewer">Viewer (Free)</option>
        <option value="analyst" selected>Analyst ($5/mo)</option>
      </select>
      <input type="number" id="new-days" value="30" placeholder="days" style="width:80px">
      <label style="display:flex;align-items:center;gap:6px;color:var(--dim);font-size:12px;cursor:pointer">
        <input type="checkbox" id="new-trial"> Trial
      </label>
    </div>
    <button class="btn-action" onclick="createUser()">CREATE & SEND EMAIL</button>
    <div id="create-msg" class="msg"></div>
  </div>

  <div id="tab-payments" class="section">
    <h3 style="color:var(--cyan);letter-spacing:2px;margin-bottom:16px;font-size:13px">PAYMENTS</h3>
    <table>
      <thead><tr><th>ID</th><th>Email</th><th>Chain</th><th>Amount</th><th>Status</th><th>Date</th><th>Actions</th></tr></thead>
      <tbody id="payments-table"></tbody>
    </table>
  </div>

  <div id="tab-audit" class="section">
    <h3 style="color:var(--cyan);letter-spacing:2px;margin-bottom:16px;font-size:13px">AUDIT LOG</h3>
    <table>
      <thead><tr><th>Time</th><th>User</th><th>Action</th><th>IP</th><th>Detail</th></tr></thead>
      <tbody id="audit-table"></tbody>
    </table>
  </div>

</div>

<script>
const API = "/api/v1";

function showTab(name) {
  document.querySelectorAll(".section").forEach(s => s.classList.remove("active"));
  document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
  document.getElementById("tab-" + name).classList.add("active");
  event.target.classList.add("active");
  if (name === "users")    loadUsers();
  if (name === "payments") loadPayments();
  if (name === "audit")    loadAudit();
}

function roleClass(r) {
  return r === "admin" ? "badge-admin" : r === "analyst" ? "badge-analyst" : "badge-viewer";
}

async function loadUsers() {
  const res  = await fetch(API + "/admin/users");
  const data = await res.json();
  document.getElementById("users-table").innerHTML = data.map(u => `
    <tr>
      <td>${u.username}</td>
      <td style="color:var(--dim)">${u.email || "—"}</td>
      <td><span class="badge ${roleClass(u.role)}">${u.role.toUpperCase()}</span></td>
      <td style="color:${u.expires_at ? '#ffd600' : 'var(--dim)'}">${u.expires_at ? u.expires_at.split("T")[0] : "unlimited"}</td>
      <td style="color:var(--dim)">${u.last_login ? u.last_login.split("T")[0] : "never"}</td>
      <td><span class="badge ${u.active ? 'badge-active' : 'badge-inactive'}">${u.active ? "ACTIVE" : "DISABLED"}</span></td>
      <td style="display:flex;gap:6px;flex-wrap:wrap">
        <button class="btn-sm" onclick="extendUser('${u.username}', 30)">+30d</button>
        <button class="btn-sm" onclick="toggleUser('${u.username}', ${u.active ? 0 : 1})">${u.active ? "DISABLE" : "ENABLE"}</button>
        <button class="btn-sm danger" onclick="deleteUser('${u.username}')">DELETE</button>
      </td>
    </tr>
  `).join("");
}

async function createUser() {
  const email = document.getElementById("new-email").value;
  const role  = document.getElementById("new-role").value;
  const days  = parseInt(document.getElementById("new-days").value);
  const trial = document.getElementById("new-trial").checked;
  const msg   = document.getElementById("create-msg");

  const res = await fetch(API + "/admin/users/create", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({email, role, days, trial})
  });
  const d = await res.json();
  if (d.success) {
    msg.style.color = "#00ff88";
    msg.textContent = "Created: " + d.username + " / " + d.password + " — email sent!";
    document.getElementById("new-email").value = "";
  } else {
    msg.style.color = "#ff3d5a";
    msg.textContent = d.error || "Failed";
  }
}

async function extendUser(username, days) {
  await fetch(API + "/admin/users/extend", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({username, days})
  });
  loadUsers();
}

async function toggleUser(username, active) {
  await fetch(API + "/admin/users/update", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({username, active})
  });
  loadUsers();
}

async function deleteUser(username) {
  if (!confirm("Delete user " + username + "?")) return;
  await fetch(API + "/admin/users/delete", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({username})
  });
  loadUsers();
}

async function loadPayments() {
  const res  = await fetch(API + "/admin/payments");
  const data = await res.json();
  document.getElementById("payments-table").innerHTML = data.map(p => `
    <tr>
      <td>#${p.id}</td>
      <td>${p.email}</td>
      <td style="color:var(--cyan)">${p.chain}</td>
      <td style="color:var(--green)">${p.amount} ${p.currency}</td>
      <td><span class="badge ${p.status === 'confirmed' ? 'badge-active' : 'badge-viewer'}">${p.status.toUpperCase()}</span></td>
      <td style="color:var(--dim)">${p.created_at.split("T")[0]}</td>
      <td>${p.status === 'pending' ? `<button class="btn-sm" onclick="confirmPayment(${p.id})">CONFIRM</button>` : "—"}</td>
    </tr>
  `).join("");
}

async function confirmPayment(id) {
  const tx = prompt("Enter TX hash (or leave blank for manual confirm):");
  if (tx === null) return;
  await fetch(API + "/admin/payments/confirm", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({payment_id: id, tx_hash: tx || "manual"})
  });
  loadPayments();
}

async function loadAudit() {
  const res  = await fetch(API + "/admin/audit");
  const data = await res.json();
  document.getElementById("audit-table").innerHTML = data.map(a => `
    <tr>
      <td style="color:var(--dim)">${a.timestamp.split("T")[0]} ${a.timestamp.split("T")[1].split(".")[0]}</td>
      <td style="color:var(--cyan)">${a.username || "—"}</td>
      <td>${a.action}</td>
      <td style="color:var(--dim)">${a.ip || "—"}</td>
      <td style="color:var(--dim)">${a.detail || "—"}</td>
    </tr>
  `).join("");
}

loadUsers();
</script>
</body>
</html>
""".replace("API_PREFIX_PLACEHOLDER", API_PREFIX)

# ================================
# MAIN DASHBOARD HTML
# ================================

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Hansen AI — Market Intelligence</title>

  <!-- Favicon -->
  <link rel="icon" type="image/x-icon" href="/favicon.ico">

  <!-- Fonts -->
  <link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@400;600;700&display=swap" rel="stylesheet">

  <style>
  :root { --bg:#080c10; --panel:#0d1117; --border:#1c2a38; --cyan:#00e5ff; --green:#00ff88; --red:#ff3d5a; --yellow:#ffd600; --text:#c9d1d9; --dim:#4a5568; }
  * { margin:0; padding:0; box-sizing:border-box; }
  body { background:var(--bg); color:var(--text); font-family:'Rajdhani',sans-serif; font-size:15px; min-height:100vh; }
  header { border-bottom:1px solid var(--border); padding:14px 24px; display:flex; align-items:center; justify-content:space-between; background:var(--panel); }
  header h1 { font-size:18px; font-weight:700; color:var(--cyan); letter-spacing:3px; text-transform:uppercase; white-space:nowrap; }
  #clock { font-family:'Share Tech Mono',monospace; font-size:13px; color:#aabbcc; }
  #status { font-size:12px; color:#8899aa; }
  .dot { display:inline-block; width:7px; height:7px; border-radius:50%; background:var(--green); margin-right:6px; animation:pulse 2s infinite; }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
  .header-btns { display:flex; gap:8px; align-items:center; }
  .hbtn { font-family:'Rajdhani',sans-serif; font-size:11px; font-weight:700; letter-spacing:2px; text-transform:uppercase; color:#8899aa; background:none; border:1px solid #2a3a4a; border-radius:2px; padding:4px 12px; cursor:pointer; transition:all 0.2s; }
  .hbtn:hover { color:var(--cyan); border-color:var(--cyan); }
  .hbtn.admin { color:var(--yellow); border-color:#ffd60044; }
  .hbtn.admin:hover { background:#ffd60011; }
  .ticker-wrap { background:#060a0e; border-bottom:1px solid var(--border); overflow:hidden; height:34px; display:flex; align-items:center; position:relative; }
  .ticker-wrap::before,.ticker-wrap::after { content:''; position:absolute; top:0; bottom:0; width:60px; z-index:2; pointer-events:none; }
  .ticker-wrap::before { left:0; background:linear-gradient(to right,#060a0e,transparent); }
  .ticker-wrap::after  { right:0; background:linear-gradient(to left,#060a0e,transparent); }
  .ticker-track { display:flex; animation:ticker-scroll 60s linear infinite; white-space:nowrap; will-change:transform; }
  .ticker-track:hover { animation-play-state:paused; }
  @keyframes ticker-scroll { 0%{transform:translateX(0)} 100%{transform:translateX(-50%)} }
  .ticker-item { display:inline-flex; align-items:center; gap:6px; padding:0 20px; font-family:'Share Tech Mono',monospace; font-size:12px; border-right:1px solid #0f1a24; }
  .ticker-symbol { color:#7a9ab8; font-weight:600; letter-spacing:1px; }
  .ticker-price  { color:var(--text); }
  .grid { display:grid; grid-template-columns:repeat(3,1fr); gap:16px; padding:20px; }
  .grid-wide { display:grid; grid-template-columns:2fr 1fr; gap:16px; padding:0 20px 20px; }
  .panel { background:var(--panel); border:1px solid var(--border); border-radius:4px; padding:16px; }
  .panel-title { font-size:11px; font-weight:700; letter-spacing:3px; color:var(--cyan); text-transform:uppercase; border-bottom:1px solid var(--border); padding-bottom:10px; margin-bottom:14px; }
  .regime-badge { font-size:28px; font-weight:700; letter-spacing:4px; }
  .bull{color:var(--green)} .bear{color:var(--red)} .sideways{color:var(--yellow)} .ranging{color:var(--yellow)} .unknown{color:#8899aa}
  .breakdown { margin-top:12px; display:grid; grid-template-columns:1fr 1fr; gap:6px; }
  .breakdown-item { font-family:'Share Tech Mono',monospace; font-size:12px; display:flex; justify-content:space-between; padding:4px 8px; background:#0a1220; border-radius:2px; color:#aabbcc; }
  .vol-index { font-size:32px; font-weight:700; font-family:'Share Tech Mono',monospace; color:var(--cyan); margin-bottom:6px; }
  .vol-level { font-size:13px; font-weight:600; letter-spacing:2px; }
  .stat-row { display:flex; justify-content:space-between; padding:6px 0; border-bottom:1px solid var(--border); font-size:14px; }
  .stat-row:last-child { border-bottom:none; }
  .stat-label { color:#7a9ab8; }
  .mover-row { display:flex; justify-content:space-between; padding:5px 0; font-family:'Share Tech Mono',monospace; font-size:13px; border-bottom:1px solid #111820; color:#aabbcc; }
  .mover-row:last-child { border-bottom:none; }
  .pos{color:var(--green)} .neg{color:var(--red)}
  .insight-item { padding:8px 0; border-bottom:1px solid var(--border); font-size:14px; line-height:1.5; color:#c9d1d9; min-height:36px; }
  .insight-item:last-child { border-bottom:none; }
  .insight-item::before { content:'▸ '; color:var(--cyan); }
  .insight-locked { padding:8px 0; font-size:13px; color:#7a9ab8; font-style:italic; }
  .insight-locked::before { content:'🔒 '; }
  .cursor { display:inline-block; width:7px; height:13px; background:var(--cyan); margin-left:2px; vertical-align:middle; animation:blink 0.8s step-end infinite; }
  @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
  .summary-coin { padding:10px 0; border-bottom:1px solid var(--border); }
  .summary-coin:last-child { border-bottom:none; }
  .coin-name { font-weight:700; font-size:14px; margin-bottom:4px; color:var(--cyan); }
  .coin-stats { display:flex; gap:16px; font-family:'Share Tech Mono',monospace; font-size:12px; color:#aabbcc; }
  .loading { color:#7a9ab8; font-style:italic; }
  .role-badge { font-size:10px; letter-spacing:2px; padding:3px 8px; border-radius:2px; background:#ffd60011; border:1px solid #ffd60033; color:#ffd600; }
  /* DERIVATIVES PANELS */
  .deriv-section { padding:0 20px 20px; }
  .deriv-section-title { font-size:11px; font-weight:700; letter-spacing:3px; color:#ffd600; text-transform:uppercase; margin-bottom:12px; display:flex; align-items:center; gap:8px; }
  .deriv-section-title::before { content:''; display:inline-block; width:3px; height:14px; background:#ffd600; border-radius:1px; }
  .deriv-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:16px; }
  .deriv-panel { background:var(--panel); border:1px solid var(--border); border-radius:4px; padding:16px; }
  .deriv-panel-title { font-size:11px; font-weight:700; letter-spacing:3px; color:var(--cyan); text-transform:uppercase; border-bottom:1px solid var(--border); padding-bottom:10px; margin-bottom:12px; display:flex; justify-content:space-between; align-items:center; }
  .deriv-badge { font-size:9px; letter-spacing:1px; padding:2px 6px; border-radius:2px; }
  .badge-greed  { background:#ff3d5a22; color:#ff3d5a; border:1px solid #ff3d5a44; }
  .badge-fear   { background:#00ff8822; color:#00ff88; border:1px solid #00ff8844; }
  .badge-neutral{ background:#ffd60022; color:#ffd600; border:1px solid #ffd60044; }
  .deriv-row { display:flex; justify-content:space-between; align-items:center; padding:5px 0; border-bottom:1px solid #0f1822; font-family:'Share Tech Mono',monospace; font-size:12px; }
  .deriv-row:last-child { border-bottom:none; }
  .deriv-sym { color:#aabbcc; font-weight:600; }
  .deriv-val { font-weight:700; }
  .funding-pos { color:#ff3d5a; }
  .funding-neg { color:#00ff88; }
  .funding-neu { color:#ffd600; }
  .oi-spike  { color:#ff3d5a; }
  .oi-rising { color:#ffa500; }
  .oi-dump   { color:#00ff88; }
  .oi-stable { color:#7a9ab8; }
  .liq-long  { color:#ff3d5a; }
  .liq-short { color:#00ff88; }
  .deriv-summary { display:grid; grid-template-columns:1fr 1fr; gap:6px; margin-bottom:10px; }
  .deriv-sum-item { background:#060a0e; border-radius:2px; padding:6px 10px; font-family:'Share Tech Mono',monospace; font-size:11px; }
  .deriv-sum-label { color:#4a5568; font-size:10px; letter-spacing:1px; }
  .deriv-sum-val { color:#aabbcc; font-weight:700; margin-top:2px; }
  .cascade-alert { background:#ff3d5a11; border:1px solid #ff3d5a44; border-radius:2px; padding:8px 12px; margin-bottom:10px; font-size:12px; color:#ff3d5a; letter-spacing:1px; display:none; }
  .cascade-alert.active { display:block; }
  .sector-section { padding:0 20px 20px; }
  .sector-section-title { font-size:11px; font-weight:700; letter-spacing:3px; color:#00e5ff; text-transform:uppercase; margin-bottom:12px; display:flex; align-items:center; gap:8px; }
  .sector-section-title::before { content:''; display:inline-block; width:3px; height:14px; background:#00e5ff; border-radius:1px; }
  .sector-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:16px; }
  .sector-panel { background:var(--panel); border:1px solid var(--border); border-radius:4px; padding:16px; }
  .sector-panel-title { font-size:11px; font-weight:700; letter-spacing:3px; color:var(--cyan); text-transform:uppercase; border-bottom:1px solid var(--border); padding-bottom:10px; margin-bottom:12px; display:flex; justify-content:space-between; align-items:center; }
  .sector-badge { font-size:9px; letter-spacing:1px; padding:2px 6px; border-radius:2px; }
  .sector-row { display:flex; justify-content:space-between; align-items:center; padding:5px 0; border-bottom:1px solid #0f1822; font-family:'Share Tech Mono',monospace; font-size:12px; }
  .sector-row:last-child { border-bottom:none; }
  .sector-name { color:#aabbcc; font-weight:600; }
  .sector-val { font-weight:700; }
  .sector-bar { height:4px; background:#0f1822; border-radius:2px; margin-top:4px; overflow:hidden; }
  .sector-bar-fill { height:100%; border-radius:2px; transition:width 0.5s ease; }
  .sector-summary { display:grid; grid-template-columns:1fr 1fr; gap:6px; margin-bottom:10px; }
  .sector-sum-item { background:#060a0e; border-radius:2px; padding:6px 10px; font-family:'Share Tech Mono',monospace; font-size:11px; }
  .sector-sum-label { color:#4a5568; font-size:10px; letter-spacing:1px; }
  .sector-sum-val { color:#aabbcc; font-weight:700; margin-top:2px; }
  .sector-tf-tabs { display:flex; gap:6px; margin-bottom:12px; }
  .sector-tf-btn { background:#0a1018; border:1px solid var(--border); color:#4a5568; padding:3px 10px; font-size:10px; font-family:'Share Tech Mono',monospace; letter-spacing:1px; border-radius:2px; cursor:pointer; transition:all 0.2s; }
  .sector-tf-btn.active { color:#00e5ff; border-color:#00e5ff; background:#0a1a2a; }
  .sector-tf-btn:hover { color:#aabbcc; }
  .rotation-tag { display:inline-block; font-size:9px; letter-spacing:1px; padding:2px 6px; border-radius:2px; margin-right:4px; }
  .rotation-in { background:#00e5ff22; color:#00e5ff; }
  .rotation-out { background:#ff555522; color:#ff5555; }
  .corr-section { padding:0 20px 20px; }
  .corr-section-title { font-size:11px; font-weight:700; letter-spacing:3px; color:#ba68c8; text-transform:uppercase; margin-bottom:12px; display:flex; align-items:center; gap:8px; }
  .corr-section-title::before { content:''; display:inline-block; width:3px; height:14px; background:#ba68c8; border-radius:1px; }
  .corr-grid { display:grid; grid-template-columns:2fr 1fr; gap:16px; }
  .corr-panel { background:var(--panel); border:1px solid var(--border); border-radius:4px; padding:16px; }
  .corr-panel-title { font-size:11px; font-weight:700; letter-spacing:3px; color:var(--cyan); text-transform:uppercase; border-bottom:1px solid var(--border); padding-bottom:10px; margin-bottom:12px; display:flex; justify-content:space-between; align-items:center; }
  .corr-table-wrap { overflow-x:auto; }
  .corr-table { border-collapse:collapse; font-family:'Share Tech Mono',monospace; font-size:11px; width:100%; }
  .corr-table th { padding:5px 8px; color:#aabbcc; font-weight:700; text-align:center; border-bottom:1px solid var(--border); position:sticky; top:0; background:var(--panel); font-size:11px; }
  .corr-table td { padding:5px 8px; text-align:center; border-bottom:1px solid #0f1822; }
  .corr-cell { display:inline-block; width:100%; padding:3px 2px; border-radius:2px; font-weight:700; font-size:11px; }
  .corr-row { display:flex; justify-content:space-between; align-items:center; padding:5px 0; border-bottom:1px solid #0f1822; font-family:'Share Tech Mono',monospace; font-size:12px; }
  .corr-row:last-child { border-bottom:none; }
  .corr-pair { color:#aabbcc; font-weight:600; }
  .corr-val { font-weight:700; }
  .beta-row { display:flex; justify-content:space-between; align-items:center; padding:5px 0; border-bottom:1px solid #0f1822; font-family:'Share Tech Mono',monospace; font-size:12px; }
  .beta-row:last-child { border-bottom:none; }
  .beta-sym { color:#aabbcc; font-weight:600; }
  .beta-val { font-weight:700; }
  .corr-window-tabs { display:flex; gap:6px; margin-bottom:12px; }
  .corr-window-btn { background:#0a1018; border:1px solid var(--border); color:#4a5568; padding:3px 10px; font-size:10px; font-family:'Share Tech Mono',monospace; letter-spacing:1px; border-radius:2px; cursor:pointer; transition:all 0.2s; }
  .corr-window-btn.active { color:#ba68c8; border-color:#ba68c8; background:#1a0a2a; }
  .corr-window-btn:hover { color:#aabbcc; }
  .alert-section { padding:0 20px 20px; }
  .alert-section-title { font-size:11px; font-weight:700; letter-spacing:3px; color:#ff9800; text-transform:uppercase; margin-bottom:12px; display:flex; align-items:center; gap:8px; }
  .alert-section-title::before { content:''; display:inline-block; width:3px; height:14px; background:#ff9800; border-radius:1px; }
  .alert-grid { display:grid; grid-template-columns:1fr 2fr; gap:16px; }
  .alert-panel { background:var(--panel); border:1px solid var(--border); border-radius:4px; padding:16px; }
  .alert-panel-title { font-size:11px; font-weight:700; letter-spacing:3px; color:var(--cyan); text-transform:uppercase; border-bottom:1px solid var(--border); padding-bottom:10px; margin-bottom:12px; display:flex; justify-content:space-between; align-items:center; }
  .alert-row { display:flex; justify-content:space-between; align-items:center; padding:6px 0; border-bottom:1px solid #0f1822; font-family:'Share Tech Mono',monospace; font-size:11px; }
  .alert-row:last-child { border-bottom:none; }
  .alert-msg { color:#aabbcc; flex:1; margin-right:8px; }
  .alert-time { color:#4a5568; font-size:10px; white-space:nowrap; }
  .alert-severity { font-size:9px; letter-spacing:1px; padding:2px 6px; border-radius:2px; margin-right:8px; font-weight:700; }
  .sev-critical { background:#ff555533; color:#ff5555; }
  .sev-warning { background:#ff980033; color:#ff9800; }
  .sev-info { background:#00e5ff22; color:#00e5ff; }
  .alert-stat { background:#060a0e; border-radius:2px; padding:8px 12px; margin-bottom:6px; font-family:'Share Tech Mono',monospace; }
  .alert-stat-label { color:#4a5568; font-size:10px; letter-spacing:1px; }
  .alert-stat-val { color:#aabbcc; font-weight:700; font-size:14px; margin-top:2px; }
  .heatmap-section { padding:0 20px 20px; }
  .heatmap-section-title { font-size:11px; font-weight:700; letter-spacing:3px; color:#76ff03; text-transform:uppercase; margin-bottom:12px; display:flex; align-items:center; gap:8px; }
  .heatmap-section-title::before { content:''; display:inline-block; width:3px; height:14px; background:#76ff03; border-radius:1px; }
  .heatmap-panel { background:var(--panel); border:1px solid var(--border); border-radius:4px; padding:16px; }
  .heatmap-panel-title { font-size:11px; font-weight:700; letter-spacing:3px; color:var(--cyan); text-transform:uppercase; border-bottom:1px solid var(--border); padding-bottom:10px; margin-bottom:12px; display:flex; justify-content:space-between; align-items:center; }
  .heatmap-tf-tabs { display:flex; gap:6px; margin-bottom:12px; }
  .heatmap-tf-btn { background:#0a1018; border:1px solid var(--border); color:#4a5568; padding:3px 10px; font-size:10px; font-family:'Share Tech Mono',monospace; letter-spacing:1px; border-radius:2px; cursor:pointer; transition:all 0.2s; }
  .heatmap-tf-btn.active { color:#76ff03; border-color:#76ff03; background:#0a1a0a; }
  .heatmap-tf-btn:hover { color:#aabbcc; }
  .heatmap-grid { display:flex; flex-wrap:wrap; gap:4px; }
  .heatmap-cell { display:flex; flex-direction:column; align-items:center; justify-content:center; border-radius:3px; padding:6px 4px; min-width:58px; font-family:'Share Tech Mono',monospace; cursor:default; transition:transform 0.15s; border:1px solid transparent; }
  .heatmap-cell:hover { transform:scale(1.08); border-color:#ffffff33; z-index:1; }
  .heatmap-cell-sym { font-size:10px; font-weight:700; color:#fff; text-shadow:0 1px 2px rgba(0,0,0,0.5); }
  .heatmap-cell-val { font-size:9px; font-weight:600; color:#ffffffcc; }
  .heatmap-sector-label { font-size:10px; color:#4a5568; letter-spacing:2px; text-transform:uppercase; margin:10px 0 6px; font-weight:700; width:100%; }
  .heatmap-stats { display:grid; grid-template-columns:repeat(4,1fr); gap:8px; margin-bottom:16px; }
  .heatmap-stat-item { background:#060a0e; border-radius:2px; padding:8px 10px; font-family:'Share Tech Mono',monospace; }
  .heatmap-stat-label { color:#4a5568; font-size:10px; letter-spacing:1px; }
  .heatmap-stat-val { color:#aabbcc; font-weight:700; font-size:13px; margin-top:2px; }
  .screener-section { padding:0 20px 20px; }
  .screener-section-title { font-size:11px; font-weight:700; letter-spacing:3px; color:#e040fb; text-transform:uppercase; margin-bottom:12px; display:flex; align-items:center; gap:8px; }
  .screener-section-title::before { content:''; display:inline-block; width:3px; height:14px; background:#e040fb; border-radius:1px; }
  .screener-tabs { display:flex; gap:6px; margin-bottom:12px; flex-wrap:wrap; }
  .screener-tab { background:#0a1018; border:1px solid var(--border); color:#4a5568; padding:4px 12px; font-size:10px; font-family:'Share Tech Mono',monospace; letter-spacing:1px; border-radius:2px; cursor:pointer; transition:all 0.2s; }
  .screener-tab.active { color:#e040fb; border-color:#e040fb; background:#1a0a2a; }
  .screener-tab:hover { color:#aabbcc; }
  .screener-panel { background:var(--panel); border:1px solid var(--border); border-radius:4px; padding:16px; }
  .screener-panel-title { font-size:11px; font-weight:700; letter-spacing:3px; color:var(--cyan); text-transform:uppercase; border-bottom:1px solid var(--border); padding-bottom:10px; margin-bottom:12px; display:flex; justify-content:space-between; align-items:center; }
  .screener-table { width:100%; border-collapse:collapse; font-family:'Share Tech Mono',monospace; font-size:11px; }
  .screener-table th { padding:6px 8px; color:#4a5568; font-weight:700; text-align:left; border-bottom:1px solid var(--border); font-size:10px; letter-spacing:1px; text-transform:uppercase; }
  .screener-table td { padding:6px 8px; border-bottom:1px solid #0f1822; color:#aabbcc; }
  .screener-table tr:hover { background:#0a1a2a; }
  .screener-desc { color:#4a5568; font-size:10px; margin-bottom:12px; font-style:italic; }
  .screener-match { font-size:9px; letter-spacing:1px; padding:2px 6px; border-radius:2px; background:#e040fb22; color:#e040fb; }
  .sentiment-section { padding:0 20px 20px; }
  .sentiment-section-title { font-size:11px; font-weight:700; letter-spacing:3px; color:#ffd600; text-transform:uppercase; margin-bottom:12px; display:flex; align-items:center; gap:8px; }
  .sentiment-section-title::before { content:''; display:inline-block; width:3px; height:14px; background:#ffd600; border-radius:1px; }
  .sentiment-grid { display:grid; grid-template-columns:1fr 1fr 1fr; gap:16px; }
  .sentiment-panel { background:var(--panel); border:1px solid var(--border); border-radius:4px; padding:16px; }
  .sentiment-panel-title { font-size:11px; font-weight:700; letter-spacing:3px; color:var(--cyan); text-transform:uppercase; border-bottom:1px solid var(--border); padding-bottom:10px; margin-bottom:12px; }
  .fg-gauge { text-align:center; padding:16px 0; }
  .fg-score { font-size:48px; font-weight:700; font-family:'Share Tech Mono',monospace; }
  .fg-label { font-size:14px; font-weight:700; letter-spacing:2px; margin-top:4px; }
  .fg-bar { height:8px; background:#0f1822; border-radius:4px; margin:16px 0 8px; overflow:hidden; position:relative; }
  .fg-bar-fill { height:100%; border-radius:4px; transition:width 0.8s ease; }
  .fg-component { display:flex; justify-content:space-between; align-items:center; padding:5px 0; border-bottom:1px solid #0f1822; font-family:'Share Tech Mono',monospace; font-size:11px; }
  .fg-component:last-child { border-bottom:none; }
  .fg-comp-name { color:#4a5568; }
  .fg-comp-score { font-weight:700; }
  .narrative-card { background:#060a0e; border-radius:3px; padding:10px 12px; margin-bottom:8px; border-left:3px solid #4a5568; }
  .narrative-label { font-size:12px; font-weight:700; color:#aabbcc; font-family:'Share Tech Mono',monospace; }
  .narrative-desc { font-size:10px; color:#4a5568; margin-top:3px; }
  .narrative-strength { font-size:10px; font-weight:700; font-family:'Share Tech Mono',monospace; float:right; }
  .market-stat-row { display:flex; justify-content:space-between; padding:5px 0; border-bottom:1px solid #0f1822; font-family:'Share Tech Mono',monospace; font-size:11px; }
  .market-stat-row:last-child { border-bottom:none; }
  .stat-label { color:#4a5568; }
  .stat-val { color:#aabbcc; font-weight:700; }
  .onchain-section { padding:0 20px 20px; }
  .onchain-section-title { font-size:11px; font-weight:700; letter-spacing:3px; color:#18ffff; text-transform:uppercase; margin-bottom:12px; display:flex; align-items:center; gap:8px; }
  .onchain-section-title::before { content:''; display:inline-block; width:3px; height:14px; background:#18ffff; border-radius:1px; }
  .onchain-grid { display:grid; grid-template-columns:1fr 1fr 1fr; gap:16px; }
  .onchain-panel { background:var(--panel); border:1px solid var(--border); border-radius:4px; padding:16px; }
  .onchain-panel-title { font-size:11px; font-weight:700; letter-spacing:3px; color:var(--cyan); text-transform:uppercase; border-bottom:1px solid var(--border); padding-bottom:10px; margin-bottom:12px; display:flex; justify-content:space-between; align-items:center; }
  .whale-row { display:flex; justify-content:space-between; align-items:center; padding:5px 0; border-bottom:1px solid #0f1822; font-family:'Share Tech Mono',monospace; font-size:11px; }
  .whale-row:last-child { border-bottom:none; }
  .whale-sym { color:#aabbcc; font-weight:700; }
  .whale-score { font-weight:700; padding:2px 6px; border-radius:2px; font-size:10px; }
  .whale-dir { font-size:10px; }
  .flow-row { display:flex; justify-content:space-between; align-items:center; padding:5px 0; border-bottom:1px solid #0f1822; font-family:'Share Tech Mono',monospace; font-size:11px; }
  .flow-row:last-child { border-bottom:none; }
  .flow-sym { color:#aabbcc; font-weight:600; }
  .flow-type { font-size:9px; letter-spacing:1px; padding:2px 6px; border-radius:2px; font-weight:700; }
  .flow-in { background:#00e67622; color:#00e676; }
  .flow-out { background:#ff555522; color:#ff5555; }
  .flow-neutral { background:#4a556822; color:#4a5568; }
  .flow-bar { height:4px; background:#0f1822; border-radius:2px; margin-top:3px; overflow:hidden; }
  .flow-bar-fill { height:100%; border-radius:2px; }
  .stable-row { display:flex; justify-content:space-between; align-items:center; padding:6px 0; border-bottom:1px solid #0f1822; font-family:'Share Tech Mono',monospace; font-size:11px; }
  .stable-row:last-child { border-bottom:none; }
  .stable-sym { color:#aabbcc; font-weight:700; }
  .stable-peg { font-size:9px; padding:2px 6px; border-radius:2px; }
  .peg-ok { background:#00e67622; color:#00e676; }
  .peg-warn { background:#ff980022; color:#ff9800; }
  .onchain-stat { background:#060a0e; border-radius:2px; padding:6px 10px; margin-bottom:6px; font-family:'Share Tech Mono',monospace; font-size:11px; }
  .onchain-stat-label { color:#4a5568; font-size:10px; letter-spacing:1px; }
  .onchain-stat-val { color:#aabbcc; font-weight:700; margin-top:2px; }
  .reports-section { padding:0 20px 20px; }
  .reports-section-title { font-size:11px; font-weight:700; letter-spacing:3px; color:#69f0ae; text-transform:uppercase; margin-bottom:12px; display:flex; align-items:center; gap:8px; }
  .reports-section-title::before { content:''; display:inline-block; width:3px; height:14px; background:#69f0ae; border-radius:1px; }
  .reports-grid { display:grid; grid-template-columns:2fr 1fr; gap:16px; }
  .reports-panel { background:var(--panel); border:1px solid var(--border); border-radius:4px; padding:16px; }
  .reports-panel-title { font-size:11px; font-weight:700; letter-spacing:3px; color:var(--cyan); text-transform:uppercase; border-bottom:1px solid var(--border); padding-bottom:10px; margin-bottom:12px; display:flex; justify-content:space-between; align-items:center; }
  .report-content { font-family:'Share Tech Mono',monospace; font-size:11px; color:#aabbcc; white-space:pre-wrap; line-height:1.6; max-height:400px; overflow-y:auto; padding:8px; background:#060a0e; border-radius:3px; }
  .report-meta { font-size:10px; color:#4a5568; margin-top:8px; display:flex; gap:12px; }
  .report-actions { display:flex; gap:8px; margin-bottom:12px; }
  .report-btn { background:#0a1018; border:1px solid var(--border); color:#69f0ae; padding:5px 14px; font-size:10px; font-family:'Share Tech Mono',monospace; letter-spacing:1px; border-radius:2px; cursor:pointer; transition:all 0.2s; }
  .report-btn:hover { background:#0a2a1a; border-color:#69f0ae; }
  .report-btn.generating { color:#4a5568; cursor:wait; }
  .llm-status { font-size:9px; letter-spacing:1px; padding:2px 6px; border-radius:2px; font-weight:700; }
  .llm-online { background:#00e67622; color:#00e676; }
  .llm-offline { background:#ff555522; color:#ff5555; }
  .report-history-item { padding:8px 0; border-bottom:1px solid #0f1822; font-family:'Share Tech Mono',monospace; font-size:11px; cursor:pointer; transition:background 0.15s; }
  .report-history-item:hover { background:#0a1a2a; }
  .report-history-item:last-child { border-bottom:none; }
  .report-type-tag { font-size:9px; letter-spacing:1px; padding:2px 6px; border-radius:2px; margin-right:6px; }
  .tag-daily { background:#69f0ae22; color:#69f0ae; }
  .tag-weekly { background:#e040fb22; color:#e040fb; }
  .tag-flash { background:#ffd60022; color:#ffd600; }
  .insight-section { padding:0 20px 20px; }
  .insight-section-title { font-size:11px; font-weight:700; letter-spacing:3px; color:#40c4ff; text-transform:uppercase; margin-bottom:12px; display:flex; align-items:center; gap:8px; }
  .insight-section-title::before { content:''; display:inline-block; width:3px; height:14px; background:#40c4ff; border-radius:1px; }
  .insight-panel { background:var(--panel); border:1px solid var(--border); border-radius:4px; padding:16px; }
  .insight-panel-title { font-size:11px; font-weight:700; letter-spacing:3px; color:var(--cyan); text-transform:uppercase; border-bottom:1px solid var(--border); padding-bottom:10px; margin-bottom:12px; display:flex; justify-content:space-between; align-items:center; }
  .insight-content { font-family:'Share Tech Mono',monospace; font-size:11px; color:#aabbcc; white-space:pre-wrap; line-height:1.7; padding:12px; background:#060a0e; border-radius:3px; max-height:300px; overflow-y:auto; }
  .insight-grid { display:grid; grid-template-columns:2fr 1fr; gap:16px; }
  .insight-tags { display:flex; flex-wrap:wrap; gap:6px; margin-top:10px; }
  .insight-tag { font-size:9px; letter-spacing:1px; padding:3px 8px; border-radius:2px; background:#40c4ff22; color:#40c4ff; font-weight:700; }
  .insight-meta { font-size:10px; color:#4a5568; margin-top:8px; }
</style>
</head>
<body>

<header>
  <h1><span class="dot"></span>Hansen AI — Market Intelligence</h1>
  <div style="display:flex;gap:16px;align-items:center">
    <span id="status">Loading...</span>
    <span id="clock"></span>
    <span class="role-badge" id="role-badge">ROLE_PLACEHOLDER</span>
    <div class="header-btns">
      <button class="hbtn admin" id="admin-btn" style="display:none" onclick="window.location.href='/admin'">ADMIN</button>
      <button class="hbtn" onclick="logout()">LOGOUT</button>
    </div>
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

<div class="deriv-section">
  <div class="deriv-section-title">Derivatives Intelligence</div>
  <div class="deriv-grid">

    <div class="deriv-panel">
      <div class="deriv-panel-title">Funding Rate <span id="funding-sentiment-badge" class="deriv-badge badge-neutral">—</span></div>
      <div class="deriv-summary" id="funding-summary"></div>
      <div id="funding-list"><div class="loading">Loading...</div></div>
    </div>

    <div class="deriv-panel">
      <div class="deriv-panel-title">Open Interest <span id="oi-spike-badge" class="deriv-badge badge-neutral">—</span></div>
      <div class="deriv-summary" id="oi-summary"></div>
      <div id="oi-list"><div class="loading">Loading...</div></div>
    </div>

    <div class="deriv-panel">
      <div class="deriv-panel-title">Liquidations <span id="liq-dom-badge" class="deriv-badge badge-neutral">—</span></div>
      <div id="cascade-alert" class="cascade-alert">⚠ LIQUIDATION CASCADE DETECTED</div>
      <div class="deriv-summary" id="liq-summary"></div>
      <div id="liq-list"><div class="loading">Loading...</div></div>
    </div>

  </div>
</div>

<div class="sector-section">
  <div class="sector-section-title">Sector Performance</div>
  <div class="sector-tf-tabs">
    <button class="sector-tf-btn active" data-tf="1h">1H</button>
    <button class="sector-tf-btn" data-tf="4h">4H</button>
    <button class="sector-tf-btn" data-tf="24h">24H</button>
    <button class="sector-tf-btn" data-tf="7d">7D</button>
  </div>
  <div class="sector-grid">
    <div class="sector-panel">
      <div class="sector-panel-title">Sector Ranking
        <span id="sector-count-badge" class="sector-badge badge-neutral">—</span>
      </div>
      <div class="sector-summary" id="sector-summary"></div>
      <div id="sector-ranking-list"><div class="loading">Loading...</div></div>
    </div>
    <div class="sector-panel">
      <div class="sector-panel-title">Top Sectors
        <span class="sector-badge" style="background:#00e5ff22;color:#00e5ff;">BULLISH</span>
      </div>
      <div id="sector-top-list"><div class="loading">Loading...</div></div>
    </div>
    <div class="sector-panel">
      <div class="sector-panel-title">Sector Rotation
        <span id="rotation-badge" class="sector-badge badge-neutral">—</span>
      </div>
      <div id="sector-rotation-list"><div class="loading">Loading...</div></div>
    </div>
  </div>
</div>

<div class="corr-section">
  <div class="corr-section-title">Correlation Matrix</div>
  <div class="corr-window-tabs">
    <button class="corr-window-btn" data-window="24h">24H</button>
    <button class="corr-window-btn active" data-window="7d">7D</button>
    <button class="corr-window-btn" data-window="14d">14D</button>
    <button class="corr-window-btn" data-window="30d">30D</button>
  </div>
  <div class="corr-grid">
    <div class="corr-panel">
      <div class="corr-panel-title">Correlation Heatmap
        <span id="corr-count-badge" class="sector-badge badge-neutral">—</span>
      </div>
      <div class="corr-table-wrap" id="corr-heatmap"><div class="loading">Loading...</div></div>
    </div>
    <div class="corr-panel">
      <div class="corr-panel-title">Beta vs BTC</div>
      <div id="beta-list"><div class="loading">Loading...</div></div>
      <div class="corr-panel-title" style="margin-top:16px;">Strongest Pairs</div>
      <div id="corr-strongest-list"><div class="loading">Loading...</div></div>
      <div class="corr-panel-title" style="margin-top:16px;">Most Decorrelated</div>
      <div id="corr-weakest-list"><div class="loading">Loading...</div></div>
    </div>
  </div>
</div>

<div class="alert-section">
  <div class="alert-section-title">Alert Center</div>
  <div class="alert-grid">
    <div class="alert-panel">
      <div class="alert-panel-title">Alert Stats</div>
      <div id="alert-stats"><div class="loading">Loading...</div></div>
    </div>
    <div class="alert-panel">
      <div class="alert-panel-title">Recent Alerts
        <span id="alert-count-badge" class="alert-severity sev-info">—</span>
      </div>
      <div id="alert-list"><div class="loading">Loading...</div></div>
    </div>
  </div>
</div>

<div class="heatmap-section">
  <div class="heatmap-section-title">Market Heatmap</div>
  <div class="heatmap-tf-tabs">
    <button class="heatmap-tf-btn" data-tf="1h">1H</button>
    <button class="heatmap-tf-btn" data-tf="4h">4H</button>
    <button class="heatmap-tf-btn active" data-tf="24h">24H</button>
  </div>
  <div class="heatmap-panel">
    <div class="heatmap-panel-title">Sector Heatmap
      <span id="heatmap-sentiment-badge" class="sector-badge badge-neutral">—</span>
    </div>
    <div class="heatmap-stats" id="heatmap-stats"></div>
    <div class="heatmap-grid" id="heatmap-grid"><div class="loading">Loading...</div></div>
  </div>
</div>

<div class="screener-section">
  <div class="screener-section-title">Smart Screener</div>
  <div class="screener-tabs" id="screener-tabs"><div class="loading">Loading...</div></div>
  <div class="screener-panel">
    <div class="screener-panel-title">
      <span id="screener-active-label">Select a preset</span>
      <span id="screener-match-badge" class="screener-match">—</span>
    </div>
    <div class="screener-desc" id="screener-desc"></div>
    <div id="screener-results"><div class="loading">Loading...</div></div>
  </div>
</div>

<div class="sentiment-section">
  <div class="sentiment-section-title">Market Sentiment & Narrative</div>
  <div class="sentiment-grid">
    <div class="sentiment-panel">
      <div class="sentiment-panel-title">Fear & Greed Index</div>
      <div class="fg-gauge" id="fg-gauge"><div class="loading">Loading...</div></div>
      <div class="fg-bar"><div class="fg-bar-fill" id="fg-bar-fill"></div></div>
      <div id="fg-components"></div>
    </div>
    <div class="sentiment-panel">
      <div class="sentiment-panel-title">Active Narratives</div>
      <div id="narrative-list"><div class="loading">Loading...</div></div>
    </div>
    <div class="sentiment-panel">
      <div class="sentiment-panel-title">Market Stats</div>
      <div id="market-stats"><div class="loading">Loading...</div></div>
    </div>
  </div>
</div>

<div class="onchain-section">
  <div class="onchain-section-title">Onchain Intelligence</div>
  <div class="onchain-grid">
    <div class="onchain-panel">
      <div class="onchain-panel-title">Whale Activity
        <span id="whale-count-badge" class="sector-badge badge-neutral">—</span>
      </div>
      <div id="whale-list"><div class="loading">Loading...</div></div>
    </div>
    <div class="onchain-panel">
      <div class="onchain-panel-title">Exchange Flow
        <span id="flow-sentiment-badge" class="sector-badge badge-neutral">—</span>
      </div>
      <div class="onchain-stat" id="flow-summary"></div>
      <div id="flow-list"><div class="loading">Loading...</div></div>
    </div>
    <div class="onchain-panel">
      <div class="onchain-panel-title">Stablecoin Flow
        <span id="stable-signal-badge" class="sector-badge badge-neutral">—</span>
      </div>
      <div id="stable-list"><div class="loading">Loading...</div></div>
    </div>
  </div>
</div>

<div class="reports-section">
  <div class="reports-section-title">AI Reports</div>
  <div class="reports-grid">
    <div class="reports-panel">
      <div class="reports-panel-title">Latest Report
        <span id="llm-status-badge" class="llm-status llm-offline">CHECKING...</span>
      </div>
      <div class="report-actions">
        <button class="report-btn" onclick="generateReport('flash')">FLASH</button>
        <button class="report-btn" onclick="generateReport('daily')">DAILY</button>
        <button class="report-btn" onclick="generateReport('weekly')">WEEKLY</button>
      </div>
      <div class="report-content" id="report-content">Loading...</div>
      <div class="report-meta" id="report-meta"></div>
    </div>
    <div class="reports-panel">
      <div class="reports-panel-title">Report History</div>
      <div id="report-history"><div class="loading">Loading...</div></div>
    </div>
  </div>
</div>

<div class="insight-section">
  <div class="insight-section-title">AI Market Insight</div>
  <div class="insight-grid">
    <div class="insight-panel">
      <div class="insight-panel-title">Latest AI Analysis
        <span id="insight-score-badge" class="sector-badge badge-neutral">—</span>
      </div>
      <div class="insight-content" id="insight-content">Waiting for first snapshot cycle...</div>
      <div class="insight-meta" id="insight-meta"></div>
    </div>
    <div class="insight-panel">
      <div class="insight-panel-title">Context Summary</div>
      <div id="insight-context"><div class="loading">Loading...</div></div>
    </div>
  </div>
</div>

<script>
const API  = "API_PREFIX_PLACEHOLDER";
const ROLE = "ROLE_PLACEHOLDER";

if (ROLE === "admin") document.getElementById("admin-btn").style.display = "";

function clock() { document.getElementById("clock").textContent = new Date().toLocaleTimeString(); }
setInterval(clock, 1000); clock();

function logout() {
  document.cookie = "hansen_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
  window.location.href = "/login";
}

let tickerPrices = {}, tickerPrev = {};

function formatPrice(p) {
  if (p >= 1000) return p.toLocaleString("en-US",{minimumFractionDigits:2,maximumFractionDigits:2});
  if (p >= 1) return p.toFixed(3);
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
    tickerPrev = {...tickerPrices};
    const fl = prices.map(p => {
      const d = p.price * (Math.random() * 0.0004 - 0.0002);
      tickerPrices[p.symbol] = p.price + d;
      return {symbol: p.symbol, price: p.price + d};
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
    return {symbol, price: price + d};
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
  return {bull:"bull",bear:"bear",sideways:"sideways",ranging:"ranging"}[r] || "unknown";
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
    if (ROLE === "viewer") {
      document.getElementById("insight").innerHTML = "<div class='insight-locked'>AI Insights available for Analyst subscribers — $5/month</div>";
    } else if (ni.join("|") !== lastInsight.join("|") && ni.length) {
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

function refresh() { loadMarket(); loadSystem(); loadMovers(); loadDerivatives(); loadSectorPerformance(); loadCorrelation(); loadAlerts(); loadHeatmap(); loadScreener(); loadSentiment(); loadOnchain(); loadReports(); loadInsight(); }
refresh();
setInterval(refresh, 120000);
setInterval(loadDerivatives, 600000);

async function loadDerivatives() {
  try {
    const res = await fetch(API + "/derivatives");
    if (res.status === 401) { window.location.href = "/login"; return; }
    const d = await res.json();

    // FUNDING RATE
    const fs = d.funding_summary || {};
    const fsentiment = fs.market_sentiment || "NEUTRAL";
    const fbadge = document.getElementById("funding-sentiment-badge");
    if (fbadge) {
      fbadge.textContent = fsentiment;
      fbadge.className = "deriv-badge " + (fsentiment === "GREED" ? "badge-greed" : fsentiment === "FEAR" ? "badge-fear" : "badge-neutral");
    }
    const fsum = document.getElementById("funding-summary");
    if (fsum) fsum.innerHTML = `
      <div class="deriv-sum-item"><div class="deriv-sum-label">AVG RATE</div><div class="deriv-sum-val ${parseFloat(fs.avg_funding||0) > 0 ? 'funding-pos' : 'funding-neg'}">${fs.avg_funding ?? "—"}%</div></div>
      <div class="deriv-sum-item"><div class="deriv-sum-label">LONG/SHORT</div><div class="deriv-sum-val">${fs.positive_count ?? 0}/${fs.negative_count ?? 0}</div></div>
    `;
    const flist = document.getElementById("funding-list");
    if (flist) flist.innerHTML = (d.funding || []).slice(0,8).map(f => {
      const cls = f.funding_rate > 0.01 ? "funding-pos" : f.funding_rate < -0.01 ? "funding-neg" : "funding-neu";
      const sign = f.funding_rate > 0 ? "+" : "";
      return `<div class="deriv-row"><span class="deriv-sym">${f.symbol}</span><span class="deriv-val ${cls}">${sign}${f.funding_rate}%</span></div>`;
    }).join("") || "<div class='loading'>No data</div>";

    // OPEN INTEREST
    const os = d.oi_summary || {};
    const oibadge = document.getElementById("oi-spike-badge");
    if (oibadge) {
      oibadge.textContent = os.oi_spikes > 0 ? `${os.oi_spikes} SPIKE` : "STABLE";
      oibadge.className = "deriv-badge " + (os.oi_spikes > 0 ? "badge-greed" : "badge-neutral");
    }
    const oisum = document.getElementById("oi-summary");
    if (oisum) oisum.innerHTML = `
      <div class="deriv-sum-item"><div class="deriv-sum-label">SPIKES</div><div class="deriv-sum-val oi-spike">${os.oi_spikes ?? 0}</div></div>
      <div class="deriv-sum-item"><div class="deriv-sum-label">DUMPS</div><div class="deriv-sum-val oi-dump">${os.oi_dumps ?? 0}</div></div>
    `;
    const oilist = document.getElementById("oi-list");
    if (oilist) oilist.innerHTML = (d.oi || []).slice(0,8).map(o => {
      const cls = o.signal === "SPIKE" ? "oi-spike" : o.signal === "RISING" ? "oi-rising" : o.signal === "DUMP" ? "oi-dump" : "oi-stable";
      const sign = o.oi_delta > 0 ? "+" : "";
      return `<div class="deriv-row"><span class="deriv-sym">${o.symbol}</span><span class="deriv-val ${cls}">${sign}${o.oi_delta}%</span></div>`;
    }).join("") || "<div class='loading'>No data</div>";

    // LIQUIDATIONS
    const ls = d.liq_summary || {};
    const cascade = d.cascade_alert || {};
    const liqDom = ls.dominance || "";
    const liqbadge = document.getElementById("liq-dom-badge");
    if (liqbadge) {
      liqbadge.textContent = liqDom === "LONG_DOMINANT" ? "LONGS REKT" : liqDom === "SHORT_DOMINANT" ? "SHORTS REKT" : "—";
      liqbadge.className = "deriv-badge " + (liqDom === "LONG_DOMINANT" ? "badge-greed" : liqDom === "SHORT_DOMINANT" ? "badge-fear" : "badge-neutral");
    }
    const cascadeEl = document.getElementById("cascade-alert");
    if (cascadeEl) cascadeEl.classList[cascade.cascade ? "add" : "remove"]("active");
    const totalUsd = ls.total_liquidated_usd ? "$" + Number(ls.total_liquidated_usd).toLocaleString() : "—";
    const liqsum = document.getElementById("liq-summary");
    if (liqsum) liqsum.innerHTML = `
      <div class="deriv-sum-item"><div class="deriv-sum-label">TOTAL LIQ</div><div class="deriv-sum-val">${totalUsd}</div></div>
      <div class="deriv-sum-item"><div class="deriv-sum-label">LONG/SHORT</div><div class="deriv-sum-val"><span class="liq-long">${ls.long_count ?? 0}</span>/<span class="liq-short">${ls.short_count ?? 0}</span></div></div>
    `;
    const liqlist = document.getElementById("liq-list");
    if (liqlist) liqlist.innerHTML = (d.liquidations || []).slice(0,8).map(l => {
      const cls = l.type === "LONG_LIQ" ? "liq-long" : "liq-short";
      const label = l.type === "LONG_LIQ" ? "LONG" : "SHORT";
      return `<div class="deriv-row"><span class="deriv-sym">${l.symbol}</span><span class="deriv-val ${cls}">$${Number(l.value_usd||0).toLocaleString()} ${label}</span></div>`;
    }).join("") || "<div class='loading'>No data</div>";

  } catch(e) { console.log("[DERIVATIVES]", e); }
}

let currentSectorTF = "24h";
let currentCorrWindow = "7d";

document.querySelectorAll(".sector-tf-btn").forEach(btn => {
  btn.addEventListener("click", function() {
    document.querySelectorAll(".sector-tf-btn").forEach(b => b.classList.remove("active"));
    this.classList.add("active");
    currentSectorTF = this.dataset.tf;
    loadSectorPerformance();
  });
});

document.querySelectorAll(".corr-window-btn").forEach(btn => {
  btn.addEventListener("click", function() {
    document.querySelectorAll(".corr-window-btn").forEach(b => b.classList.remove("active"));
    this.classList.add("active");
    currentCorrWindow = this.dataset.window;
    loadCorrelation();
  });
});

function corrColor(val) {
  if (val === null || val === undefined) return "color:#4a5568";
  if (val >= 0.8) return "background:#00e67644;color:#00e676";
  if (val >= 0.6) return "background:#00e67622;color:#00e676";
  if (val >= 0.3) return "background:#4a556822;color:#aabbcc";
  if (val >= -0.3) return "color:#4a5568";
  if (val >= -0.6) return "background:#ff555522;color:#ff5555";
  return "background:#ff555544;color:#ff5555";
}

function trendColor(val) {
  if (val > 0) return "color:#00e676";
  if (val < 0) return "color:#ff5555";
  return "color:#4a5568";
}

function trendIcon(trend) {
  if (trend === "bullish") return "▲";
  if (trend === "bearish") return "▼";
  return "—";
}

async function loadSectorPerformance() {
  try {
    const res = await fetch(API + "/sector-performance");
    if (res.status === 401) { window.location.href = "/login"; return; }
    const d = await res.json();
    if (d.status !== "ok") return;
    const data = d.data;
    const ranking = data.ranking_24h || [];
    const rotation = data.rotation || {};
    document.getElementById("sector-count-badge").textContent = data.sector_count + " SECTORS";
    const bullish = ranking.filter(s => s.trend === "bullish").length;
    const bearish = ranking.filter(s => s.trend === "bearish").length;
    document.getElementById("sector-summary").innerHTML = `
      <div class="sector-sum-item"><div class="sector-sum-label">BULLISH</div><div class="sector-sum-val" style="color:#00e676">${bullish}</div></div>
      <div class="sector-sum-item"><div class="sector-sum-label">BEARISH</div><div class="sector-sum-val" style="color:#ff5555">${bearish}</div></div>
      <div class="sector-sum-item"><div class="sector-sum-label">TOTAL COINS</div><div class="sector-sum-val">${data.total_coins}</div></div>
      <div class="sector-sum-item"><div class="sector-sum-label">UPDATED</div><div class="sector-sum-val">${new Date(data.timestamp * 1000).toLocaleTimeString()}</div></div>
    `;
    document.getElementById("sector-ranking-list").innerHTML = ranking.slice(0, 15).map(s => `
      <div class="sector-row"><span class="sector-name">#${s.rank} ${s.name}</span><span class="sector-val" style="${trendColor(s.avg_change)}">${s.avg_change > 0 ? "+" : ""}${s.avg_change.toFixed(2)}% <small>${trendIcon(s.trend)}</small></span></div>
      <div class="sector-bar"><div class="sector-bar-fill" style="width:${Math.min(100, s.strength)}%;background:${s.avg_change >= 0 ? '#00e676' : '#ff5555'}"></div></div>
    `).join("");
    const topSectors = ranking.filter(s => s.avg_change > 0).slice(0, 5);
    document.getElementById("sector-top-list").innerHTML = topSectors.length > 0 ? topSectors.map(s => `
      <div class="sector-row"><span class="sector-name">${s.name}</span><span class="sector-val" style="color:#00e676">+${s.avg_change.toFixed(2)}%</span></div>
      <div style="font-size:10px;color:#4a5568;padding:2px 0 8px;">Best: <span style="color:#aabbcc">${s.top_coin ? s.top_coin.symbol.replace("USDT","") : "—"}</span> <span style="${trendColor(s.top_coin ? s.top_coin.change : 0)}">${s.top_coin ? (s.top_coin.change > 0 ? "+" : "") + s.top_coin.change.toFixed(2) + "%" : ""}</span> &nbsp;|&nbsp; ${s.coins_up}↑ ${s.coins_down}↓</div>
    `).join("") : '<div style="color:#4a5568;font-size:11px;">No bullish sectors</div>';
    const rotIn = rotation.rotating_in || [];
    const rotOut = rotation.rotating_out || [];
    let rotHTML = "";
    if (rotIn.length > 0) {
      rotHTML += '<div style="margin-bottom:8px;font-size:10px;color:#4a5568;letter-spacing:1px;">ROTATING IN</div>';
      rotHTML += rotIn.map(r => `<div class="sector-row"><span class="sector-name"><span class="rotation-tag rotation-in">IN</span>${r.name}</span><span class="sector-val" style="color:#00e5ff">${r["1h"] > 0 ? "+" : ""}${r["1h"].toFixed(2)}%</span></div>`).join("");
    }
    if (rotOut.length > 0) {
      rotHTML += '<div style="margin:12px 0 8px;font-size:10px;color:#4a5568;letter-spacing:1px;">ROTATING OUT</div>';
      rotHTML += rotOut.map(r => `<div class="sector-row"><span class="sector-name"><span class="rotation-tag rotation-out">OUT</span>${r.name}</span><span class="sector-val" style="color:#ff5555">${r["1h"].toFixed(2)}%</span></div>`).join("");
    }
    if (!rotHTML) rotHTML = '<div style="color:#4a5568;font-size:11px;">No rotation signals</div>';
    document.getElementById("sector-rotation-list").innerHTML = rotHTML;
    document.getElementById("rotation-badge").textContent = rotIn.length + " IN / " + rotOut.length + " OUT";
  } catch(e) { console.log("[SECTOR]", e); }
}

async function loadCorrelation() {
  try {
    const res = await fetch(API + "/correlation?window=" + currentCorrWindow);
    if (res.status === 401) { window.location.href = "/login"; return; }
    const d = await res.json();
    if (d.status !== "ok") return;
    const data = d.data;
    const matrix = data.matrix || {};
    const labels = matrix.labels || [];
    const grid = matrix.matrix || [];
    const strongest = data.strongest || [];
    const weakest = data.weakest || [];
    const betas = data.beta_vs_btc || [];
    document.getElementById("corr-count-badge").textContent = data.total_pairs + " PAIRS";
    const maxDisplay = Math.min(12, labels.length);
    let tableHTML = '<table class="corr-table"><tr><th></th>';
    for (let i = 0; i < maxDisplay; i++) { tableHTML += `<th>${labels[i]}</th>`; }
    tableHTML += '</tr>';
    for (let i = 0; i < maxDisplay; i++) {
      tableHTML += `<tr><th style="text-align:right;padding-right:8px;">${labels[i]}</th>`;
      for (let j = 0; j < maxDisplay; j++) {
        const val = grid[i] && grid[i][j] !== null ? grid[i][j] : null;
        const display = val !== null ? val.toFixed(2) : "—";
        const style = i === j ? "color:#4a5568" : corrColor(val);
        tableHTML += `<td><span class="corr-cell" style="${style}">${display}</span></td>`;
      }
      tableHTML += '</tr>';
    }
    tableHTML += '</table>';
    document.getElementById("corr-heatmap").innerHTML = tableHTML;
    document.getElementById("beta-list").innerHTML = betas.slice(0, 10).map(b => `<div class="beta-row"><span class="beta-sym">${b.label}</span><span class="beta-val" style="${b.beta > 1.2 ? 'color:#ff5555' : b.beta < 0.8 ? 'color:#00e676' : 'color:#aabbcc'}">${b.beta.toFixed(2)}β</span></div>`).join("");
    document.getElementById("corr-strongest-list").innerHTML = strongest.slice(0, 5).map(p => `<div class="corr-row"><span class="corr-pair">${p.pair}</span><span class="corr-val" style="${corrColor(p.correlation)}">${p.correlation.toFixed(3)}</span></div>`).join("");
    document.getElementById("corr-weakest-list").innerHTML = weakest.slice(0, 5).map(p => `<div class="corr-row"><span class="corr-pair">${p.pair}</span><span class="corr-val" style="${corrColor(p.correlation)}">${p.correlation.toFixed(3)}</span></div>`).join("");
  } catch(e) { console.log("[CORRELATION]", e); }
}

let currentHeatmapTF = "24h";

document.querySelectorAll(".heatmap-tf-btn").forEach(btn => {
  btn.addEventListener("click", function() {
    document.querySelectorAll(".heatmap-tf-btn").forEach(b => b.classList.remove("active"));
    this.classList.add("active");
    currentHeatmapTF = this.dataset.tf;
    loadHeatmap();
  });
});

async function loadAlerts() {
  try {
    const res = await fetch(API + "/alerts");
    if (res.status === 401) { window.location.href = "/login"; return; }
    const d = await res.json();
    if (d.status !== "ok") return;
    const data = d.data;
    const stats = data.stats || {};
    const alerts = data.alerts || [];
    document.getElementById("alert-stats").innerHTML = `
      <div class="alert-stat"><div class="alert-stat-label">LAST HOUR</div><div class="alert-stat-val">${stats.last_hour || 0}</div></div>
      <div class="alert-stat"><div class="alert-stat-label">LAST 24H</div><div class="alert-stat-val">${stats.last_24h || 0}</div></div>
      <div class="alert-stat"><div class="alert-stat-label">CRITICAL</div><div class="alert-stat-val" style="color:#ff5555">${stats.critical_24h || 0}</div></div>
      <div class="alert-stat"><div class="alert-stat-label">WARNING</div><div class="alert-stat-val" style="color:#ff9800">${stats.warning_24h || 0}</div></div>
      <div class="alert-stat"><div class="alert-stat-label">TOTAL</div><div class="alert-stat-val">${stats.total_alerts || 0}</div></div>
    `;
    document.getElementById("alert-count-badge").textContent = alerts.length + " ALERTS";
    document.getElementById("alert-count-badge").className = "alert-severity " + (stats.critical_24h > 0 ? "sev-critical" : stats.warning_24h > 0 ? "sev-warning" : "sev-info");
    document.getElementById("alert-list").innerHTML = alerts.length > 0 ? alerts.slice(0, 20).map(a => `
      <div class="alert-row">
        <span class="alert-severity sev-${a.severity}">${a.severity.toUpperCase()}</span>
        <span class="alert-msg">${a.message}</span>
        <span class="alert-time">${a.datetime || new Date(a.timestamp * 1000).toLocaleTimeString()}</span>
      </div>
    `).join("") : '<div style="color:#4a5568;font-size:11px;padding:8px 0;">No alerts — market is calm</div>';
  } catch(e) { console.log("[ALERTS]", e); }
}

async function loadHeatmap() {
  try {
    const res = await fetch(API + "/heatmap?tf=" + currentHeatmapTF);
    if (res.status === 401) { window.location.href = "/login"; return; }
    const d = await res.json();
    if (d.status !== "ok") return;
    const data = d.data;
    const heatmap = data.heatmap || {};
    const sectors = heatmap.sectors || [];
    const gainer = heatmap.max_gainer;
    const loser = heatmap.max_loser;
    document.getElementById("heatmap-sentiment-badge").textContent = (data.sentiment || "neutral").toUpperCase();
    document.getElementById("heatmap-sentiment-badge").className = "sector-badge " + (data.sentiment === "bullish" ? "badge-greed" : data.sentiment === "bearish" ? "badge-fear" : "badge-neutral");
    document.getElementById("heatmap-stats").innerHTML = `
      <div class="heatmap-stat-item"><div class="heatmap-stat-label">COINS</div><div class="heatmap-stat-val">${heatmap.total_coins || 0}</div></div>
      <div class="heatmap-stat-item"><div class="heatmap-stat-label">GREEN</div><div class="heatmap-stat-val" style="color:#00e676">${data.green_count || 0}</div></div>
      <div class="heatmap-stat-item"><div class="heatmap-stat-label">RED</div><div class="heatmap-stat-val" style="color:#ff5555">${data.red_count || 0}</div></div>
      <div class="heatmap-stat-item"><div class="heatmap-stat-label">TOP</div><div class="heatmap-stat-val" style="color:#00e676">${gainer ? gainer.label + " +" + gainer.change.toFixed(1) + "%" : "—"}</div></div>
    `;
    let gridHTML = "";
    sectors.forEach(sec => {
      gridHTML += `<div class="heatmap-sector-label">${sec.name} (${sec.avg_change > 0 ? "+" : ""}${sec.avg_change.toFixed(2)}%)</div>`;
      sec.coins.forEach(c => {
        const bg = c.change > 0
          ? `rgba(0,230,118,${Math.min(0.8, Math.abs(c.intensity) * 0.8 + 0.1)})`
          : c.change < 0
            ? `rgba(255,85,85,${Math.min(0.8, Math.abs(c.intensity) * 0.8 + 0.1)})`
            : "rgba(74,85,104,0.3)";
        gridHTML += `<div class="heatmap-cell" style="background:${bg}" title="${c.symbol} | ${c.change > 0 ? "+" : ""}${c.change.toFixed(2)}% | Vol: ${(c.volume/1000000).toFixed(1)}M">
          <span class="heatmap-cell-sym">${c.label}</span>
          <span class="heatmap-cell-val">${c.change > 0 ? "+" : ""}${c.change.toFixed(1)}%</span>
        </div>`;
      });
    });
    document.getElementById("heatmap-grid").innerHTML = gridHTML || '<div style="color:#4a5568;font-size:11px;">No heatmap data</div>';
  } catch(e) { console.log("[HEATMAP]", e); }
}

let currentPreset = "momentum_kings";

async function loadScreener() {
  try {
    const res = await fetch(API + "/screener");
    if (res.status === 401) { window.location.href = "/login"; return; }
    const d = await res.json();
    if (d.status !== "ok") return;
    const data = d.data;
    const presets = data.available_presets || {};
    const results = data.presets || {};
    let tabsHTML = "";
    Object.keys(presets).forEach(key => {
      const p = presets[key];
      const matched = results[key] ? results[key].total_matched : 0;
      tabsHTML += `<button class="screener-tab ${key === currentPreset ? 'active' : ''}" data-preset="${key}">${p.label} (${matched})</button>`;
    });
    document.getElementById("screener-tabs").innerHTML = tabsHTML;
    document.querySelectorAll(".screener-tab").forEach(btn => {
      btn.addEventListener("click", function() {
        document.querySelectorAll(".screener-tab").forEach(b => b.classList.remove("active"));
        this.classList.add("active");
        currentPreset = this.dataset.preset;
        renderScreenerPreset(data, currentPreset);
      });
    });
    renderScreenerPreset(data, currentPreset);
  } catch(e) { console.log("[SCREENER]", e); }
}

function renderScreenerPreset(data, preset) {
  const presets = data.available_presets || {};
  const results = data.presets || {};
  const p = presets[preset] || {};
  const r = results[preset] || {};
  document.getElementById("screener-active-label").textContent = p.label || preset;
  document.getElementById("screener-desc").textContent = p.description || "";
  document.getElementById("screener-match-badge").textContent = (r.total_matched || 0) + " MATCHED";
  const coins = r.top_results || [];
  if (coins.length === 0) {
    document.getElementById("screener-results").innerHTML = '<div style="color:#4a5568;font-size:11px;padding:8px 0;">No coins matched this filter</div>';
    return;
  }
  let tableHTML = '<table class="screener-table"><tr><th>#</th><th>Symbol</th><th>Price</th><th>24h %</th><th>Volume</th><th>Vol Ratio</th><th>Range</th></tr>';
  coins.forEach((c, i) => {
    const cls = c.change_24h > 0 ? 'color:#00e676' : c.change_24h < 0 ? 'color:#ff5555' : 'color:#4a5568';
    tableHTML += `<tr>
      <td>${i + 1}</td>
      <td style="color:#e040fb;font-weight:700;">${c.label}</td>
      <td>${c.price < 1 ? c.price.toFixed(6) : c.price < 100 ? c.price.toFixed(3) : c.price.toFixed(1)}</td>
      <td style="${cls}">${c.change_24h > 0 ? "+" : ""}${c.change_24h.toFixed(2)}%</td>
      <td>${(c.volume / 1000000).toFixed(1)}M</td>
      <td>${c.volume_ratio.toFixed(1)}x</td>
      <td>${c.price_range.toFixed(1)}%</td>
    </tr>`;
  });
  tableHTML += '</table>';
  document.getElementById("screener-results").innerHTML = tableHTML;
}

async function loadSentiment() {
  try {
    const res = await fetch(API + "/sentiment");
    if (res.status === 401) { window.location.href = "/login"; return; }
    const d = await res.json();
    if (d.status !== "ok") return;
    const data = d.data;
    const fg = data.fear_greed || {};
    const narratives = data.narratives || [];
    const stats = fg.market_stats || {};
    const components = fg.components || {};
    document.getElementById("fg-gauge").innerHTML = `<div class="fg-score" style="color:${fg.color || '#4a5568'}">${fg.score || 50}</div><div class="fg-label" style="color:${fg.color || '#4a5568'}">${fg.label || 'Neutral'}</div>`;
    const bar = document.getElementById("fg-bar-fill");
    bar.style.width = (fg.score || 50) + "%";
    bar.style.background = fg.score > 60 ? "linear-gradient(90deg, #00e676, #00e5ff)" : fg.score < 40 ? "linear-gradient(90deg, #ff1744, #ff9800)" : "linear-gradient(90deg, #ff9800, #ffd600)";
    let compHTML = "";
    Object.keys(components).forEach(key => {
      const c = components[key];
      const cls = c.score > 60 ? "color:#00e676" : c.score < 40 ? "color:#ff5555" : "color:#ffd600";
      compHTML += `<div class="fg-component"><span class="fg-comp-name">${key.toUpperCase()} (${(c.weight * 100).toFixed(0)}%)</span><span class="fg-comp-score" style="${cls}">${c.score.toFixed(1)}</span></div>`;
    });
    document.getElementById("fg-components").innerHTML = compHTML;
    document.getElementById("narrative-list").innerHTML = narratives.length > 0 ? narratives.map(n => {
      const borderColor = n.sentiment === "extreme_greed" || n.sentiment === "greedy" ? "#00e676" : n.sentiment === "fearful" || n.sentiment === "extreme_fear" ? "#ff5555" : n.sentiment === "cautious" ? "#ff9800" : "#4a5568";
      return `<div class="narrative-card" style="border-left-color:${borderColor}"><span class="narrative-strength" style="color:${borderColor}">${n.strength || 0}</span><div class="narrative-label">${n.label}</div><div class="narrative-desc">${n.description}</div></div>`;
    }).join("") : '<div style="color:#4a5568;font-size:11px;">No active narratives detected</div>';
    let statsHTML = "";
    statsHTML += `<div class="market-stat-row"><span class="stat-label">TOTAL COINS</span><span class="stat-val">${stats.total_coins || 0}</span></div>`;
    statsHTML += `<div class="market-stat-row"><span class="stat-label">GREEN</span><span class="stat-val" style="color:#00e676">${stats.green_count || 0} (${stats.green_ratio || 0}%)</span></div>`;
    statsHTML += `<div class="market-stat-row"><span class="stat-label">RED</span><span class="stat-val" style="color:#ff5555">${stats.red_count || 0}</span></div>`;
    statsHTML += `<div class="market-stat-row"><span class="stat-label">AVG CHANGE</span><span class="stat-val" style="${stats.avg_change > 0 ? 'color:#00e676' : 'color:#ff5555'}">${stats.avg_change > 0 ? '+' : ''}${(stats.avg_change || 0).toFixed(3)}%</span></div>`;
    document.getElementById("market-stats").innerHTML = statsHTML;
  } catch(e) { console.log("[SENTIMENT]", e); }
}

async function loadOnchain() {
  try {
    const res = await fetch(API + "/onchain");
    if (res.status === 401) { window.location.href = "/login"; return; }
    const d = await res.json();
    if (d.status !== "ok") return;
    const data = d.data;
    const whales = data.whale_activity || {};
    const flow = data.exchange_flow || {};
    const stable = data.stablecoin_flow || {};
    const wcoins = whales.whale_coins || [];
    document.getElementById("whale-count-badge").textContent = whales.total_whale_signals + " SIGNALS";
    document.getElementById("whale-list").innerHTML = wcoins.length > 0 ? wcoins.slice(0, 10).map(w => {
      const dirCls = w.direction === "accumulation" ? "color:#00e676" : w.direction === "distribution" ? "color:#ff5555" : "color:#4a5568";
      const scoreBg = w.whale_score > 70 ? "background:#ff555533;color:#ff5555" : w.whale_score > 40 ? "background:#ff980033;color:#ff9800" : "background:#00e5ff22;color:#00e5ff";
      return `<div class="whale-row"><span class="whale-sym">${w.label}</span><span class="whale-dir" style="${dirCls}">${w.direction_label}</span><span class="whale-score" style="${scoreBg}">${w.whale_score}</span></div>`;
    }).join("") : '<div style="color:#4a5568;font-size:11px;">No whale signals</div>';
    const flows = flow.flows || [];
    document.getElementById("flow-sentiment-badge").textContent = (flow.net_sentiment || "neutral").toUpperCase();
    document.getElementById("flow-sentiment-badge").className = "sector-badge " + (flow.net_sentiment === "bullish" ? "badge-greed" : flow.net_sentiment === "bearish" ? "badge-fear" : "badge-neutral");
    document.getElementById("flow-summary").innerHTML = `<div class="onchain-stat-label">INFLOW ${flow.inflow_count || 0} | OUTFLOW ${flow.outflow_count || 0} | NEUTRAL ${flow.neutral_count || 0}</div>`;
    document.getElementById("flow-list").innerHTML = flows.slice(0, 10).map(f => {
      const typeCls = f.flow_type === "inflow" ? "flow-in" : f.flow_type === "outflow" ? "flow-out" : "flow-neutral";
      return `<div class="flow-row"><span class="flow-sym">${f.label}</span><span class="flow-type ${typeCls}">${f.flow_label}</span></div><div class="flow-bar"><div class="flow-bar-fill" style="width:${f.buy_pressure}%;background:${f.buy_pressure > 55 ? '#00e676' : f.buy_pressure < 45 ? '#ff5555' : '#4a5568'}"></div></div>`;
    }).join("");
    const stables = stable.stablecoins || [];
    document.getElementById("stable-signal-badge").textContent = (stable.deployment_signal || "low").toUpperCase();
    document.getElementById("stable-list").innerHTML = stables.map(s => {
      const pegCls = s.peg_status === "stable" ? "peg-ok" : "peg-warn";
      return `<div class="stable-row"><span class="stable-sym">${s.label}</span><span>${(s.volume_usd / 1000000).toFixed(1)}M</span><span class="stable-peg ${pegCls}">${s.peg_status === "stable" ? "PEG OK" : "DEPEG"}</span></div>`;
    }).join("") || '<div style="color:#4a5568;font-size:11px;">No stablecoin data</div>';
  } catch(e) { console.log("[ONCHAIN]", e); }
}

async function loadReports() {
  try {
    const res = await fetch(API + "/reports");
    if (res.status === 401) { window.location.href = "/login"; return; }
    const d = await res.json();
    if (d.status !== "ok") return;
    const data = d.data;
    const flash = data.flash_report || {};
    const recent = data.recent_reports || [];
    document.getElementById("llm-status-badge").textContent = data.llm_status === "online" ? "LLM ONLINE" : "LLM OFFLINE";
    document.getElementById("llm-status-badge").className = "llm-status " + (data.llm_status === "online" ? "llm-online" : "llm-offline");
    if (flash.content) {
      document.getElementById("report-content").textContent = flash.content;
      document.getElementById("report-meta").innerHTML = `<span>Type: ${flash.report_type}</span><span>By: ${flash.generated_by}</span><span>${flash.datetime}</span>`;
    }
    document.getElementById("report-history").innerHTML = recent.length > 0 ? recent.map(r => {
      const tagCls = r.report_type === "daily" ? "tag-daily" : r.report_type === "weekly" ? "tag-weekly" : "tag-flash";
      return `<div class="report-history-item" onclick="showReport('${r.filename}')"><span class="report-type-tag ${tagCls}">${r.report_type.toUpperCase()}</span><span style="color:#aabbcc">${r.datetime}</span><span style="color:#4a5568;margin-left:8px;">${r.generated_by}</span></div>`;
    }).join("") : '<div style="color:#4a5568;font-size:11px;">No reports yet</div>';
  } catch(e) { console.log("[REPORTS]", e); }
}

async function generateReport(type) {
  const btn = event.target;
  btn.classList.add("generating");
  btn.textContent = "GENERATING...";
  try {
    const res = await fetch(API + "/reports/generate?type=" + type);
    const d = await res.json();
    if (d.status === "ok" && d.data) {
      document.getElementById("report-content").textContent = d.data.content || "No content";
      document.getElementById("report-meta").innerHTML = `<span>Type: ${d.data.report_type}</span><span>By: ${d.data.generated_by}</span><span>${d.data.datetime}</span>`;
    }
  } catch(e) { console.log("[REPORT GEN]", e); }
  btn.classList.remove("generating");
  btn.textContent = type.toUpperCase();
  loadReports();
}

function showReport(filename) {
  document.getElementById("report-content").textContent = "Loading report...";
}

async function loadInsight() {
  try {
    const res = await fetch(API + "/ai-insight");
    if (res.status === 401) { window.location.href = "/login"; return; }
    const d = await res.json();
    if (d.status !== "ok") return;
    const data = d.data;
    document.getElementById("insight-content").textContent = data.analysis || "No insight available";
    const score = data.sentiment_score;
    const level = data.sentiment_level;
    if (score !== undefined && score !== null) {
      document.getElementById("insight-score-badge").textContent = score + " " + (level || "");
      document.getElementById("insight-score-badge").className = "sector-badge " + (score > 60 ? "badge-greed" : score < 40 ? "badge-fear" : "badge-neutral");
    }
    document.getElementById("insight-meta").innerHTML = data.generated_at ? "Generated: " + data.generated_at : "";
    let ctxHTML = "";
    if (data.top_sectors && data.top_sectors.length > 0) {
      ctxHTML += '<div style="margin-bottom:8px;font-size:10px;color:#4a5568;letter-spacing:1px;">TOP SECTORS</div>';
      ctxHTML += '<div class="insight-tags">' + data.top_sectors.map(s => '<span class="insight-tag">' + s + '</span>').join("") + '</div>';
    }
    if (data.narratives && data.narratives.length > 0) {
      ctxHTML += '<div style="margin:12px 0 8px;font-size:10px;color:#4a5568;letter-spacing:1px;">ACTIVE NARRATIVES</div>';
      ctxHTML += '<div class="insight-tags">' + data.narratives.map(n => '<span class="insight-tag" style="background:#ffd60022;color:#ffd600;">' + n + '</span>').join("") + '</div>';
    }
    ctxHTML += '<div style="margin:12px 0 8px;font-size:10px;color:#4a5568;letter-spacing:1px;">SIGNALS</div>';
    ctxHTML += '<div style="font-family:Share Tech Mono,monospace;font-size:11px;color:#aabbcc;">';
    ctxHTML += 'Whale Signals: ' + (data.whale_signals || 0) + '<br>';
    ctxHTML += 'Alerts 24h: ' + (data.alert_count || 0);
    ctxHTML += '</div>';
    document.getElementById("insight-context").innerHTML = ctxHTML || '<div style="color:#4a5568;font-size:11px;">No context data</div>';
  } catch(e) { console.log("[INSIGHT]", e); }
}

</script>
</body>
</html>
""".replace("API_PREFIX_PLACEHOLDER", API_PREFIX)

if __name__ == "__main__":
    app.run(host=DASHBOARD_HOST, port=DASHBOARD_PORT, debug=False)