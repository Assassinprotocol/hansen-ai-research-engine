import threading
import time
from datetime import datetime, timedelta
from db_manager import get_all_users, get_conn, log_action
from email_service import send_subscription_expiry_warning

# ================================
# EXPIRY CHECKER
# Jalan background, cek sekali per hari
# Kirim warning SEKALI SAJA 7 hari sebelum expired
# ================================

CHECK_INTERVAL_HOURS = 24
WARNING_DAYS_BEFORE  = 7

def _already_warned(username):
    """Cek apakah user sudah pernah dapat warning di periode ini"""
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT COUNT(*) FROM audit_log
        WHERE username = ? AND action = 'expiry_warning_sent'
        AND timestamp > ?
    """, (username, (datetime.now() - timedelta(days=WARNING_DAYS_BEFORE + 1)).isoformat()))
    count = c.fetchone()[0]
    conn.close()
    return count > 0

def check_expiring_users():
    print("[EXPIRY] Running subscription expiry check...")
    users = get_all_users()
    now   = datetime.now()
    sent  = 0

    for user in users:
        # Skip admin, viewer, inactive
        if user["role"] in ("admin", "viewer"):
            continue
        if not user["active"]:
            continue
        if not user.get("expires_at"):
            continue
        if not user.get("email"):
            continue

        try:
            expires = datetime.fromisoformat(user["expires_at"])
            days_left = (expires - now).days

            # Kirim warning kalau 7 hari atau kurang, tapi belum expired
            if 0 < days_left <= WARNING_DAYS_BEFORE:
                if not _already_warned(user["username"]):
                    ok = send_subscription_expiry_warning(
                        user["email"],
                        user["username"],
                        user["expires_at"]
                    )
                    if ok:
                        log_action(user["username"], "expiry_warning_sent", "", f"expires={user['expires_at']} days_left={days_left}")
                        print(f"[EXPIRY] Warning sent to {user['username']} — {days_left} days left")
                        sent += 1
                else:
                    print(f"[EXPIRY] Already warned {user['username']}, skip")

        except Exception as e:
            print(f"[EXPIRY] Error checking {user['username']}: {e}")

    print(f"[EXPIRY] Check done — {sent} warning(s) sent")

def _checker_loop():
    # Tunggu 1 menit setelah startup baru mulai
    time.sleep(60)
    while True:
        try:
            check_expiring_users()
        except Exception as e:
            print(f"[EXPIRY] Loop error: {e}")
        # Tidur 24 jam
        time.sleep(CHECK_INTERVAL_HOURS * 3600)

def start_expiry_checker():
    t = threading.Thread(target=_checker_loop, daemon=True)
    t.start()
    print("[EXPIRY] Background checker started — runs every 24h")