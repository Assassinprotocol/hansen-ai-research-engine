import requests
import time
from datetime import datetime

# ================================
# OPEN INTEREST TRACKER
# ================================

BASE_URL = "https://fapi.binance.com"

TRACKED_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT",
    "MATICUSDT", "UNIUSDT", "LTCUSDT", "ATOMUSDT", "NEARUSDT",
    "APTUSDT", "OPUSDT", "ARBUSDT", "INJUSDT", "SUIUSDT",
    "TIAUSDT", "SEIUSDT", "JUPUSDT", "WIFUSDT", "PEPEUSDT",
    "ORDIUSDT", "STXUSDT", "LDOUSDT", "RNDRUSDT", "FETUSDT"
]

class OpenInterestTracker:

    def __init__(self):
        self._cache      = None
        self._cache_time = 0
        self._cache_ttl  = 60
        self._prev       = {}  # untuk hitung perubahan OI

    def _fetch(self):
        try:
            res  = requests.get(
                f"{BASE_URL}/fapi/v1/openInterest",
                timeout=10,
                params={"symbol": "BTCUSDT"}  # test single first
            )
            # Fetch semua sekaligus
            results = []
            for sym in TRACKED_SYMBOLS:
                try:
                    r = requests.get(
                        f"{BASE_URL}/fapi/v1/openInterest",
                        params={"symbol": sym},
                        timeout=5
                    )
                    d = r.json()
                    oi_val  = float(d.get("openInterest", 0))
                    # OI history untuk delta
                    prev_oi = self._prev.get(sym, oi_val)
                    delta   = round(((oi_val - prev_oi) / prev_oi * 100) if prev_oi else 0, 2)
                    self._prev[sym] = oi_val
                    results.append({
                        "symbol":    sym.replace("USDT", ""),
                        "oi":        round(oi_val, 2),
                        "oi_delta":  delta,
                        "signal":    self._signal(delta),
                        "timestamp": d.get("time", 0)
                    })
                    time.sleep(0.05)  # rate limit safe
                except:
                    continue

            results.sort(key=lambda x: x["oi"], reverse=True)
            return results

        except Exception as e:
            print(f"[OI] Fetch error: {e}")
            return []

    def _signal(self, delta):
        if delta > 5:    return "SPIKE"
        if delta > 2:    return "RISING"
        if delta < -5:   return "DUMP"
        if delta < -2:   return "FALLING"
        return "STABLE"

    def get(self, limit=20):
        now = time.time()
        if self._cache and (now - self._cache_time < self._cache_ttl):
            return self._cache[:limit]
        data = self._fetch()
        if data:
            self._cache      = data
            self._cache_time = now
        return (self._cache or [])[:limit]

    def spikes(self, limit=5):
        """Coins dengan OI spike terbesar"""
        data = self.get(30)
        data.sort(key=lambda x: abs(x["oi_delta"]), reverse=True)
        return data[:limit]

    def summary(self):
        data = self.get(30)
        if not data:
            return {}
        total_oi    = sum(d["oi"] for d in data)
        spikes      = [d for d in data if d["signal"] == "SPIKE"]
        dumps       = [d for d in data if d["signal"] == "DUMP"]
        return {
            "total_oi_tracked": round(total_oi, 2),
            "oi_spikes":        len(spikes),
            "oi_dumps":         len(dumps),
            "top_spike":        spikes[0]["symbol"] if spikes else None,
            "timestamp":        datetime.now().isoformat()
        }