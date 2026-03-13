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
JWT_SECRET             = "KMZWAY87AA"
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
ADMIN_USERNAME = "Hansen"
ADMIN_PASSWORD = "Excuted90"

# ================================
# EMAIL (Gmail SMTP)
# ================================
SMTP_HOST     = "smtp.gmail.com"
SMTP_PORT     = 587
SMTP_EMAIL    = "dcaprioleonardo64@gmail.com"
SMTP_PASSWORD = "nhchhhcnbmqkotyy"

# ================================
# PAYMENT WALLETS
# ================================
WALLETS = {
    "BTC":        "bc1ptknrx96kuyudg5xnqc3wq6y4hdckqxay5cgq808um7e7gnygwc8swnv8xn",
    "USDT_BSC":   "0xC0D018E7278De2611B67c7e59b9b45570dC59aEB",
    "USDT_ARB":   "0xC0D018E7278De2611B67c7e59b9b45570dC59aEB",
    "USDT_BASE":  "0xC0D018E7278De2611B67c7e59b9b45570dC59aEB",
    "USDT_HYPER": "0xC0D018E7278De2611B67c7e59b9b45570dC59aEB",
    "USDT_SOL":   "DvbvPU25fftYV6LA21FxQ7B5y4bb6C6rQxMCLR5ariF",
    "USDT_APT":   "0x88001f20fc5d01220851e8cb9353e3cddc5fadc29c5cf41ec5d1caece0db6d73",
    "USDC_APT":   "0x88001f20fc5d01220851e8cb9353e3cddc5fadc29c5cf41ec5d1caece0db6d73",
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
BSCSCAN_API_KEY   = "JU2JMA7W7GN1IMN624N7141FE7TY3YE8SH"
ARBISCAN_API_KEY  = "JU2JMA7W7GN1IMN624N7141FE7TY3YE8SH"
ETHERSCAN_API_KEY = "JU2JMA7W7GN1IMN624N7141FE7TY3YE8SH"
# ================================
# TRIAL
# ================================
TRIAL_ROLE          = "analyst"
TRIAL_DURATION_DAYS = 30