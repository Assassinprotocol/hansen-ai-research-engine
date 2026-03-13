import sqlite3
import hashlib
import secrets
import os
from datetime import datetime, timedelta
from dashboard_config import DB_PATH

# ================================
# CONNECTION
# ================================

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ================================
# INIT DATABASE
# ================================

def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            username     TEXT UNIQUE NOT NULL,
            password     TEXT NOT NULL,
            email        TEXT,
            role         TEXT NOT NULL DEFAULT 'viewer',
            expires_at   TEXT,
            created_at   TEXT NOT NULL,
            last_login   TEXT,
            active       INTEGER NOT NULL DEFAULT 1
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            token        TEXT PRIMARY KEY,
            user_id      INTEGER NOT NULL,
            expires_at   TEXT NOT NULL,
            created_at   TEXT NOT NULL,
            remember_me  INTEGER NOT NULL DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            email        TEXT NOT NULL,
            chain        TEXT NOT NULL,
            amount       REAL NOT NULL,
            currency     TEXT NOT NULL,
            tx_hash      TEXT,
            status       TEXT NOT NULL DEFAULT 'pending',
            plan         TEXT NOT NULL DEFAULT 'analyst',
            created_at   TEXT NOT NULL,
            confirmed_at TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            username  TEXT,
            action    TEXT,
            ip        TEXT,
            detail    TEXT,
            timestamp TEXT
        )
    """)

    conn.commit()
    conn.close()
    print("[DB] Initialized")

# ================================
# PASSWORD
# ================================

def hash_password(password):
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{hashed}"

def verify_password(password, stored):
    try:
        salt, hashed = stored.split(":")
        return hashlib.sha256((salt + password).encode()).hexdigest() == hashed
    except:
        return False

def generate_password(length=12):
    chars = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789!@#"
    return "".join(secrets.choice(chars) for _ in range(length))

# ================================
# USER CRUD
# ================================

def create_user(username, password, email=None, role="viewer", expires_days=30):
    conn = get_conn()
    c = conn.cursor()
    try:
        if expires_days and expires_days > 0:
            expires_at = (datetime.now() + timedelta(days=expires_days)).isoformat()
        else:
            expires_at = None
        c.execute("""
            INSERT INTO users (username, password, email, role, expires_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (username, hash_password(password), email, role, expires_at, datetime.now().isoformat()))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_user(username):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_by_email(email):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email = ?", (email,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_users():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, username, email, role, expires_at, created_at, last_login, active FROM users ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_user(username, **kwargs):
    conn = get_conn()
    c = conn.cursor()
    allowed = {"role", "active", "expires_at", "password", "email"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if "password" in fields:
        fields["password"] = hash_password(fields["password"])
    if not fields:
        return False
    sets = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [username]
    c.execute(f"UPDATE users SET {sets} WHERE username = ?", values)
    conn.commit()
    conn.close()
    return True

def delete_user(username):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE username = ?", (username,))
    conn.commit()
    conn.close()

def extend_subscription(username, days):
    user = get_user(username)
    if not user:
        return False
    now = datetime.now()
    current = datetime.fromisoformat(user["expires_at"]) if user.get("expires_at") else now
    base = max(now, current)
    new_expiry = (base + timedelta(days=days)).isoformat()
    return update_user(username, expires_at=new_expiry)

def update_last_login(username):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE users SET last_login = ? WHERE username = ?", (datetime.now().isoformat(), username))
    conn.commit()
    conn.close()

def is_subscription_active(user):
    if user["role"] == "admin":
        return True
    if user["role"] == "viewer":
        return True
    if not user.get("expires_at"):
        return True
    return datetime.fromisoformat(user["expires_at"]) > datetime.now()

# ================================
# SESSION MANAGEMENT
# ================================

def create_session(user_id, remember_me=False):
    from dashboard_config import SESSION_TIMEOUT_MINUTES, REMEMBER_ME_DAYS
    token = secrets.token_hex(32)
    if remember_me:
        expires_at = (datetime.now() + timedelta(days=REMEMBER_ME_DAYS)).isoformat()
    else:
        expires_at = (datetime.now() + timedelta(minutes=SESSION_TIMEOUT_MINUTES)).isoformat()
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO sessions (token, user_id, expires_at, created_at, remember_me)
        VALUES (?, ?, ?, ?, ?)
    """, (token, user_id, expires_at, datetime.now().isoformat(), 1 if remember_me else 0))
    conn.commit()
    conn.close()
    return token

def validate_session(token):
    if not token:
        return None
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT s.*, u.username, u.role, u.active, u.expires_at as sub_expires
        FROM sessions s
        JOIN users u ON s.user_id = u.id
        WHERE s.token = ?
    """, (token,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    row = dict(row)
    if datetime.fromisoformat(row["expires_at"]) < datetime.now():
        delete_session(token)
        return None
    if not row["active"]:
        return None
    return row

def delete_session(token):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM sessions WHERE token = ?", (token,))
    conn.commit()
    conn.close()

def refresh_session(token):
    from dashboard_config import SESSION_TIMEOUT_MINUTES, REMEMBER_ME_DAYS
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT remember_me FROM sessions WHERE token = ?", (token,))
    row = c.fetchone()
    if not row:
        conn.close()
        return
    if row["remember_me"]:
        new_expiry = (datetime.now() + timedelta(days=REMEMBER_ME_DAYS)).isoformat()
    else:
        new_expiry = (datetime.now() + timedelta(minutes=SESSION_TIMEOUT_MINUTES)).isoformat()
    c.execute("UPDATE sessions SET expires_at = ? WHERE token = ?", (new_expiry, token))
    conn.commit()
    conn.close()

# ================================
# PAYMENT
# ================================

def create_payment(email, chain, amount, currency, plan="analyst"):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO payments (email, chain, amount, currency, plan, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (email, chain, amount, currency, plan, datetime.now().isoformat()))
    payment_id = c.lastrowid
    conn.commit()
    conn.close()
    return payment_id

def confirm_payment(payment_id, tx_hash):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        UPDATE payments SET status = 'confirmed', tx_hash = ?, confirmed_at = ?
        WHERE id = ?
    """, (tx_hash, datetime.now().isoformat(), payment_id))
    conn.commit()
    conn.close()

def get_pending_payments():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM payments WHERE status = 'pending' ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_payments():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM payments ORDER BY created_at DESC LIMIT 50")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ================================
# AUDIT LOG
# ================================

def log_action(username, action, ip="", detail=""):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO audit_log (username, action, ip, detail, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (username, action, ip, detail, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_audit_log(limit=50):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ================================
# BOOTSTRAP ADMIN
# ================================

def bootstrap_admin():
    from dashboard_config import ADMIN_USERNAME, ADMIN_PASSWORD
    if not get_user(ADMIN_USERNAME):
        create_user(ADMIN_USERNAME, ADMIN_PASSWORD, role="admin", expires_days=0)
        print(f"[DB] Admin created: {ADMIN_USERNAME}")
    else:
        print(f"[DB] Admin exists: {ADMIN_USERNAME}")