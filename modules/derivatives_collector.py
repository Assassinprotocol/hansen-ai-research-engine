import threading
import time
import sys

sys.path.insert(0, r"C:\AI\hansen_engine")
sys.path.insert(0, r"C:\AI\hansen_engine\modules")

from modules.funding_rate    import FundingRateTracker
from modules.open_interest   import OpenInterestTracker
from modules.liquidation_feed import LiquidationFeed

# ================================
# DERIVATIVES DATA COLLECTOR
# Runs every 15 minutes — safe dari rate limit
# ================================

COLLECT_INTERVAL = 900  # 15 menit

_funding   = FundingRateTracker()
_oi        = OpenInterestTracker()
_liq       = LiquidationFeed()

_data = {
    "funding":     [],
    "funding_summary": {},
    "oi":          [],
    "oi_summary":  {},
    "liquidations": [],
    "liq_summary": {},
    "last_update": None
}

_lock = threading.Lock()

def get_derivatives_data():
    with _lock:
        return dict(_data)

def _collect():
    global _data
    print("[DERIVATIVES] Collecting funding rate, OI, liquidations...")
    try:
        funding     = _funding.get(20)
        funding_sum = _funding.summary()
        oi          = _oi.get(20)
        oi_sum      = _oi.summary()
        liqs        = _liq.top(20)
        liq_sum     = _liq.summary()
        cascade     = _liq.cascade_alert()

        with _lock:
            _data["funding"]          = funding
            _data["funding_summary"]  = funding_sum
            _data["oi"]               = oi
            _data["oi_summary"]       = oi_sum
            _data["liquidations"]     = liqs
            _data["liq_summary"]      = liq_sum
            _data["cascade_alert"]    = cascade
            _data["last_update"]      = time.strftime('%Y-%m-%dT%H:%M:%S')

        print(f"[DERIVATIVES] Done — funding:{len(funding)} OI:{len(oi)} liqs:{len(liqs)}")

    except Exception as e:
        print(f"[DERIVATIVES] Collection error: {e}")

def _collector_loop():
    time.sleep(10)  # tunggu 10 detik setelah startup
    while True:
        _collect()
        time.sleep(COLLECT_INTERVAL)

def start_derivatives_collector():
    t = threading.Thread(target=_collector_loop, daemon=True)
    t.start()
    print("[DERIVATIVES] Collector started — every 15 minutes")