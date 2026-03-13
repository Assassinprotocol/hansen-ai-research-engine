import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dashboard_config import SMTP_HOST, SMTP_PORT, SMTP_EMAIL, SMTP_PASSWORD

# ================================
# SEND EMAIL
# ================================

def send_email(to_email, subject, html_body):
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"Hansen AI <{SMTP_EMAIL}>"
        msg["To"]      = to_email
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.sendmail(SMTP_EMAIL, to_email, msg.as_string())

        print(f"[EMAIL] Sent to {to_email}: {subject}")
        return True
    except Exception as e:
        print(f"[EMAIL] Failed to {to_email}: {e}")
        return False

# ================================
# EMAIL TEMPLATES
# ================================

def send_welcome_email(to_email, username, password, role, expires_at=None):
    expiry_line = ""
    if expires_at:
        from datetime import datetime
        dt = datetime.fromisoformat(expires_at)
        expiry_line = f"<p style='color:#ffd600'>Subscription expires: <strong>{dt.strftime('%B %d, %Y')}</strong></p>"

    html = f"""
    <div style="background:#080c10;padding:40px;font-family:'Courier New',monospace;color:#c9d1d9;max-width:480px;margin:0 auto;border:1px solid #1c2a38;border-radius:4px">
      <h1 style="color:#00e5ff;letter-spacing:4px;font-size:20px;margin-bottom:4px">HANSEN AI</h1>
      <p style="color:#4a5568;font-size:12px;letter-spacing:2px;margin-bottom:32px">MARKET INTELLIGENCE SYSTEM</p>

      <p style="margin-bottom:16px">Your account has been activated.</p>

      <div style="background:#0d1117;border:1px solid #1c2a38;border-radius:4px;padding:20px;margin-bottom:24px">
        <p style="margin:0 0 8px 0">Username: <strong style="color:#00e5ff">{username}</strong></p>
        <p style="margin:0 0 8px 0">Password: <strong style="color:#00ff88">{password}</strong></p>
        <p style="margin:0">Plan: <strong style="color:#ffd600">{role.upper()}</strong></p>
      </div>

      {expiry_line}

      <p style="margin-bottom:24px">Access your dashboard at:</p>
      <div style="background:#0d1117;border:1px solid #00e5ff33;border-radius:4px;padding:12px;text-align:center">
        <span style="color:#00e5ff">https://unperishing-minerva-unprovidentially.ngrok-free.dev</span>
      </div>

      <p style="margin-top:32px;color:#4a5568;font-size:11px">Please change your password after first login.<br>Do not share your credentials.</p>
    </div>
    """
    return send_email(to_email, "Hansen AI — Account Activated", html)

def send_trial_email(to_email, username, password, expires_at):
    from datetime import datetime
    dt = datetime.fromisoformat(expires_at)
    html = f"""
    <div style="background:#080c10;padding:40px;font-family:'Courier New',monospace;color:#c9d1d9;max-width:480px;margin:0 auto;border:1px solid #1c2a38;border-radius:4px">
      <h1 style="color:#00e5ff;letter-spacing:4px;font-size:20px;margin-bottom:4px">HANSEN AI</h1>
      <p style="color:#4a5568;font-size:12px;letter-spacing:2px;margin-bottom:32px">MARKET INTELLIGENCE SYSTEM</p>

      <p style="margin-bottom:16px">Your <strong style="color:#ffd600">30-day Analyst trial</strong> has been activated.</p>

      <div style="background:#0d1117;border:1px solid #1c2a38;border-radius:4px;padding:20px;margin-bottom:24px">
        <p style="margin:0 0 8px 0">Username: <strong style="color:#00e5ff">{username}</strong></p>
        <p style="margin:0 0 8px 0">Password: <strong style="color:#00ff88">{password}</strong></p>
        <p style="margin:0 0 8px 0">Plan: <strong style="color:#ffd600">ANALYST TRIAL</strong></p>
        <p style="margin:0">Expires: <strong style="color:#ff3d5a">{dt.strftime('%B %d, %Y')}</strong></p>
      </div>

      <p style="color:#4a5568;font-size:11px">After trial ends, subscribe at $5/month to continue Analyst access.</p>
    </div>
    """
    return send_email(to_email, "Hansen AI — Trial Activated", html)

def send_payment_pending_email(to_email, payment_id, chain, amount, currency, wallet):
    html = f"""
    <div style="background:#080c10;padding:40px;font-family:'Courier New',monospace;color:#c9d1d9;max-width:480px;margin:0 auto;border:1px solid #1c2a38;border-radius:4px">
      <h1 style="color:#00e5ff;letter-spacing:4px;font-size:20px;margin-bottom:4px">HANSEN AI</h1>
      <p style="color:#4a5568;font-size:12px;letter-spacing:2px;margin-bottom:32px">PAYMENT INSTRUCTIONS</p>

      <p style="margin-bottom:16px">Send exactly <strong style="color:#00ff88">{amount} {currency}</strong> to:</p>

      <div style="background:#0d1117;border:1px solid #1c2a38;border-radius:4px;padding:20px;margin-bottom:24px;word-break:break-all">
        <p style="margin:0 0 8px 0;color:#4a5568;font-size:11px">CHAIN: {chain}</p>
        <p style="margin:0;color:#00e5ff;font-size:13px">{wallet}</p>
      </div>

      <p style="margin-bottom:8px">After payment:</p>
      <p style="margin-bottom:24px;color:#4a5568">Reply to this email with your transaction hash. Your account will be activated within 30 minutes.</p>

      <p style="color:#4a5568;font-size:11px">Payment ID: #{payment_id}<br>Do not send less than the required amount.</p>
    </div>
    """
    return send_email(to_email, "Hansen AI — Payment Instructions", html)

def send_subscription_expiry_warning(to_email, username, expires_at):
    from datetime import datetime
    dt = datetime.fromisoformat(expires_at)
    html = f"""
    <div style="background:#080c10;padding:40px;font-family:'Courier New',monospace;color:#c9d1d9;max-width:480px;margin:0 auto;border:1px solid #1c2a38;border-radius:4px">
      <h1 style="color:#00e5ff;letter-spacing:4px;font-size:20px;margin-bottom:4px">HANSEN AI</h1>
      <p style="color:#4a5568;font-size:12px;letter-spacing:2px;margin-bottom:32px">SUBSCRIPTION NOTICE</p>

      <p>Hi <strong>{username}</strong>,</p>
      <p style="margin:16px 0">Your Analyst subscription expires on <strong style="color:#ff3d5a">{dt.strftime('%B %d, %Y')}</strong>.</p>
      <p>Renew for $5 USDT to continue full access.</p>
    </div>
    """
    return send_email(to_email, "Hansen AI — Subscription Expiring Soon", html)