# ================================
# HANSEN AI — DASHBOARD CONFIG
# ================================

# Port dashboard berjalan
DASHBOARD_PORT = 5000

# Host — 127.0.0.1 = local only, 0.0.0.0 = network accessible
DASHBOARD_HOST = "127.0.0.1"

# ================================
# AUTH CREDENTIALS
# ================================

DASHBOARD_USERNAME = "Hansen"
DASHBOARD_PASSWORD = "inoutlove"

# ================================
# SECURITY KEYS
# ================================

# Secret key buat JWT token signing — GANTI dengan string random lo sendiri
JWT_SECRET = "KMZWAY87AA"

# Session timeout dalam menit
SESSION_TIMEOUT_MINUTES = 60

# ================================
# ENDPOINT PREFIX (obfuscation)
# ================================

# Prefix random buat semua API endpoint
# Default: /hx7k — bisa diganti string apapun
API_PREFIX = "/hx7k"

# ================================
# RATE LIMITING
# ================================

# Max request per IP per menit
RATE_LIMIT_PER_MINUTE = 60

# Max login attempt sebelum IP di-block sementara
MAX_LOGIN_ATTEMPTS = 5

# Block duration dalam menit setelah gagal login
LOGIN_BLOCK_MINUTES = 15

# ================================
# RESPONSE HEADER SANITIZATION
# ================================

# Hapus header yang expose framework info
SANITIZE_HEADERS = True