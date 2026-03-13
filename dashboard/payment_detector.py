import threading
import time
import requests
from datetime import datetime, timedelta
from db_manager import (
    get_conn, get_pending_payments, confirm_payment,
    get_user_by_email, create_user, extend_subscription,
    generate_password, log_action
)
from email_service import send_welcome_email
from dashboard_config import (
    WALLETS, PLANS, PAYMENT_MIN_USDT, PAYMENT_MIN_BTC,
    BSCSCAN_API_KEY, ARBISCAN_API_KEY, ETHERSCAN_API_KEY
)

# ================================
# CONFIG
# ================================

CHECK_INTERVAL_SECONDS = 120
USDT_CONTRACT_BSC  = "0x55d398326f99059fF775485246999027B3197955"
USDT_CONTRACT_ARB  = "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9"
USDT_CONTRACT_ETH  = "0xdAC17F958D2ee523a2206206994597C13D831ec7"
USDC_CONTRACT_ETH  = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
APTOS_USDT         = "0xf22bede237a07cfa90b2fdc6e5e23de94b4e33bb::asset::USDT"
APTOS_USDC         = "0xf22bede237a07cfa90b2fdc6e5e23de94b4e33bb::asset::USDC"

EVM_WALLET  = WALLETS["USDT_BSC"].lower()
SOL_WALLET  = WALLETS["USDT_SOL"]
APT_WALLET  = WALLETS["USDT_APT"].lower()
BTC_WALLET  = WALLETS["BTC"]

# ================================
# HELPERS
# ================================

def _already_processed(tx_hash):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM payments WHERE tx_hash = ? AND status = 'confirmed'", (tx_hash,))
    count = c.fetchone()[0]
    conn.close()
    return count > 0

def _match_payment(amount_raw, currency, decimals=6):
    amount = amount_raw / (10 ** decimals)
    if currency in ("USDT", "USDC"):
        return amount >= PAYMENT_MIN_USDT, amount
    if currency == "BTC":
        return amount >= PAYMENT_MIN_BTC, amount
    return False, amount

def _auto_provision(email, plan, amount, currency, chain, tx_hash):
    role = plan
    days = PLANS[plan]["duration_days"]
    existing = get_user_by_email(email)
    if existing:
        extend_subscription(existing["username"], days)
        log_action(existing["username"], "subscription_renewed", "", f"tx={tx_hash} {amount}{currency} via {chain}")
        print(f"[PAYMENT] Extended subscription for {existing['username']}")
    else:
        from db_manager import get_user
        username = email.split("@")[0].lower().replace(".", "_").replace("+", "_")
        base = username
        i = 1
        while get_user(username):
            username = f"{base}{i}"
            i += 1
        password = generate_password()
        create_user(username, password, email=email, role=role, expires_days=days)
        from db_manager import get_user as gu
        user = gu(username)
        send_welcome_email(email, username, password, role, user["expires_at"])
        log_action(username, "auto_provisioned", "", f"tx={tx_hash} {amount}{currency} via {chain}")
        print(f"[PAYMENT] Auto-provisioned {username} via {chain}")

def _find_pending_by_chain(chain_key):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM payments WHERE status = 'pending'")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return [r for r in rows if chain_key.lower() in r["chain"].lower()]

# ================================
# EVM (BSC / ARB / ETH)
# ================================

def _check_evm(chain_name, api_url, api_key, contract, currency, decimals):
    try:
        url = (
            f"{api_url}?module=account&action=tokentx"
            f"&contractaddress={contract}"
            f"&address={EVM_WALLET}"
            f"&sort=desc&apikey={api_key}"
        )
        res  = requests.get(url, timeout=10)
        data = res.json()
        if data.get("status") != "1":
            return

        cutoff = time.time() - 3600
        for tx in data.get("result", []):
            if int(tx.get("timeStamp", 0)) < cutoff:
                break
            tx_hash = tx.get("hash", "")
            if _already_processed(tx_hash):
                continue
            if tx.get("to", "").lower() != EVM_WALLET:
                continue
            is_valid, amount = _match_payment(int(tx.get("value", 0)), currency, decimals)
            if not is_valid:
                continue
            pending = _find_pending_by_chain(chain_name)
            if pending:
                confirm_payment(pending[0]["id"], tx_hash)
                _auto_provision(pending[0]["email"], pending[0]["plan"], round(amount, 2), currency, chain_name, tx_hash)
                print(f"[{chain_name}] Matched #{pending[0]['id']} — {amount} {currency}")
            else:
                log_action("system", f"unmatched_{chain_name}", "", f"tx={tx_hash} {amount}{currency}")
    except Exception as e:
        print(f"[{chain_name}] Error: {e}")

def check_bsc(): _check_evm("USDT_BSC", "https://api.bscscan.com/api",   BSCSCAN_API_KEY,  USDT_CONTRACT_BSC, "USDT", 18)
def check_arb(): _check_evm("USDT_ARB", "https://api.arbiscan.io/api",   ARBISCAN_API_KEY, USDT_CONTRACT_ARB, "USDT", 6)
def check_eth():
    _check_evm("USDT_ETH", "https://api.etherscan.io/api", ETHERSCAN_API_KEY, USDT_CONTRACT_ETH, "USDT", 6)
    _check_evm("USDC_ETH", "https://api.etherscan.io/api", ETHERSCAN_API_KEY, USDC_CONTRACT_ETH, "USDC", 6)

# ================================
# SOLANA
# ================================

def check_sol():
    try:
        USDT_MINT = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"
        rpc = "https://api.mainnet-beta.solana.com"
        sigs = requests.post(rpc, json={
            "jsonrpc":"2.0","id":1,
            "method":"getSignaturesForAddress",
            "params":[SOL_WALLET,{"limit":20}]
        }, timeout=10).json().get("result", [])

        cutoff = time.time() - 3600
        for s in sigs:
            if s.get("blockTime", 0) < cutoff:
                continue
            sig = s["signature"]
            if _already_processed(sig):
                continue
            tx = requests.post(rpc, json={
                "jsonrpc":"2.0","id":1,
                "method":"getTransaction",
                "params":[sig,{"encoding":"jsonParsed","maxSupportedTransactionVersion":0}]
            }, timeout=10).json().get("result")
            if not tx:
                continue
            for ix in tx.get("transaction",{}).get("message",{}).get("instructions",[]):
                p = ix.get("parsed",{})
                if p.get("type") != "transferChecked":
                    continue
                info = p.get("info",{})
                if info.get("mint") != USDT_MINT or info.get("destination") != SOL_WALLET:
                    continue
                is_valid, amount = _match_payment(int(info.get("tokenAmount",{}).get("amount",0)), "USDT", 6)
                if not is_valid:
                    continue
                pending = _find_pending_by_chain("USDT_SOL")
                if pending:
                    confirm_payment(pending[0]["id"], sig)
                    _auto_provision(pending[0]["email"], pending[0]["plan"], round(amount,2), "USDT", "SOL", sig)
                    print(f"[SOL] Matched #{pending[0]['id']} — {amount} USDT")
                else:
                    log_action("system", "unmatched_SOL", "", f"tx={sig} {amount}USDT")
    except Exception as e:
        print(f"[SOL] Error: {e}")

# ================================
# BTC
# ================================

def check_btc():
    try:
        data = requests.get(f"https://blockchain.info/rawaddr/{BTC_WALLET}?limit=10", timeout=10).json()
        cutoff = time.time() - 3600
        for tx in data.get("txs", []):
            if tx.get("time", 0) < cutoff:
                continue
            tx_hash = tx.get("hash", "")
            if _already_processed(tx_hash):
                continue
            total = sum(o.get("value",0) for o in tx.get("out",[]) if o.get("addr") == BTC_WALLET)
            is_valid, amount = _match_payment(total, "BTC", 8)
            if not is_valid:
                continue
            pending = _find_pending_by_chain("BTC")
            if pending:
                confirm_payment(pending[0]["id"], tx_hash)
                _auto_provision(pending[0]["email"], pending[0]["plan"], round(amount,8), "BTC", "BTC", tx_hash)
                print(f"[BTC] Matched #{pending[0]['id']} — {amount} BTC")
            else:
                log_action("system", "unmatched_BTC", "", f"tx={tx_hash} {amount}BTC")
    except Exception as e:
        print(f"[BTC] Error: {e}")

# ================================
# APTOS
# ================================

def check_aptos():
    try:
        url  = f"https://fullnode.mainnet.aptoslabs.com/v1/accounts/{APT_WALLET}/transactions?limit=20"
        txs  = requests.get(url, timeout=10).json()
        if not isinstance(txs, list):
            return
        cutoff = time.time() - 3600
        for tx in txs:
            if int(tx.get("timestamp", 0)) / 1_000_000 < cutoff:
                continue
            tx_hash = tx.get("hash", "")
            if _already_processed(tx_hash):
                continue
            for event in tx.get("events", []):
                etype = event.get("type", "")
                if "DepositEvent" not in etype:
                    continue
                currency = "USDT" if APTOS_USDT in etype else "USDC" if APTOS_USDC in etype else None
                if not currency:
                    continue
                raw = int(event.get("data", {}).get("amount", 0))
                is_valid, amount = _match_payment(raw, currency, 6)
                if not is_valid:
                    continue
                pending = _find_pending_by_chain("APT")
                if pending:
                    confirm_payment(pending[0]["id"], tx_hash)
                    _auto_provision(pending[0]["email"], pending[0]["plan"], round(amount,2), currency, "Aptos", tx_hash)
                    print(f"[APT] Matched #{pending[0]['id']} — {amount} {currency}")
                else:
                    log_action("system", "unmatched_APT", "", f"tx={tx_hash} {amount}{currency}")
    except Exception as e:
        print(f"[APT] Error: {e}")

# ================================
# MAIN LOOP
# ================================

def _detector_loop():
    time.sleep(30)
    print("[PAYMENT DETECTOR] Started — checking every 2 minutes")
    while True:
        try:
            check_bsc()
            check_arb()
            check_eth()
            check_sol()
            check_btc()
            check_aptos()
        except Exception as e:
            print(f"[PAYMENT DETECTOR] Loop error: {e}")
        time.sleep(CHECK_INTERVAL_SECONDS)

def start_payment_detector():
    t = threading.Thread(target=_detector_loop, daemon=True)
    t.start()
    print("[PAYMENT DETECTOR] Background thread started")