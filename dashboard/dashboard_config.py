# ================================
# HANSEN AI — DASHBOARD CONFIG
# ================================

# ================================
# SERVER
# ================================
DASHBOARD_HOST = "127.0.0.1"
DASHBOARD_PORT = 5000

# ================================
# SECURITY
# ================================
JWT_SECRET             = ""
SESSION_TIMEOUT_MINUTES = 60
REMEMBER_ME_DAYS       = 30
RATE_LIMIT_PER_MINUTE  = 60
MAX_LOGIN_ATTEMPTS     = 5
LOGIN_BLOCK_MINUTES    = 15
SANITIZE_HEADERS       = True
API_PREFIX = "/api/v1"

# ================================
# DATABASE
# ================================
DB_PATH = r"C:\AI\hansen_engine\dashboard\users.db"

# ================================
# ADMIN
# ================================
ADMIN_USERNAME = ""
ADMIN_PASSWORD = ""

# ================================
# EMAIL (Gmail SMTP)
# ================================
SMTP_HOST     = "smtp.gmail.com"
SMTP_PORT     = 587
SMTP_EMAIL    = "UR EMAIL"
SMTP_PASSWORD = ""

# ================================
# PAYMENT WALLETS
# ================================
WALLETS = {
    "BTC":        "UR WALLET",
    "USDT_BSC":   "",
    "USDT_ARB":   "",
    "USDT_BASE":  "",
    "USDT_HYPER": "",
    "USDT_SOL":   "",
    "USDT_APT":   "",
    "USDC_APT":   "",
}

# ================================
# PRICING
# ================================
PLANS = {
    "viewer": {
        "name":          "Viewer",
        "price_usdt":    0,
        "price_btc":     0,
        "duration_days": 0,
        "description":   "Basic market dashboard access"
    },
    "analyst": {
        "name":          "Analyst",
        "price_usdt":    5.00,
        "price_btc":     0.000050,
        "duration_days": 30,
        "description":   "Full market intelligence + AI insights"
    }
}

PAYMENT_MIN_USDT = 4.50
PAYMENT_MIN_BTC  = 0.000048
BSCSCAN_API_KEY   = ""
ARBISCAN_API_KEY  = ""
ETHERSCAN_API_KEY = ""
# ================================
# TRIAL
# ================================
TRIAL_ROLE          = "analyst"
TRIAL_DURATION_DAYS = 30
