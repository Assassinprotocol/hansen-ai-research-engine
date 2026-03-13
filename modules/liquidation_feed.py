import requests
import time
from datetime import datetime

# ================================
# LIQUIDATION FEED
# Ambil data liquidation dari Binance futures
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

class LiquidationFeed:

    def __init__(self):
        self._cache      = []
        self._cache_time = 0
        self._cache_ttl  = 60

    def _fetch(self, symbol, limit=10):
        try:
            res = requests.get(
                f"{BASE_URL}/fapi/v1/forceOrders",
                params={"symbol": symbol, "limit": limit},
                timeout=5
            )
            data = res.json()
            if not isinstance(data, list):
                return []
            results = []
            for item in data:
                try:
                    side    = item.get("side", "")
                    qty     = float(item.get("origQty", 0))
                    price   = float(item.get("price", 0))
                    value   = round(qty * price, 2)
                    ts      = item.get("time", 0)
                    results.append({
                        "symbol":    symbol.replace("USDT", ""),
                        "side":      side,           # BUY = short liq, SELL = long liq
                        "qty":       qty,
                        "price":     price,
                        "value_usd": value,
                        "type":      "SHORT_LIQ" if side == "BUY" else "LONG_LIQ",
                        "timestamp": ts
                    })
                except:
                    continue
            return results
        except:
            return []

    def get_all(self, limit_per_symbol=5):
        now = time.time()
        if self._cache and (now - self._cache_time < self._cache_ttl):
            return self._cache

        all_liqs = []
        for sym in TRACKED_SYMBOLS:
            liqs = self._fetch(sym, limit_per_symbol)
            all_liqs.extend(liqs)
            time.sleep(0.05)

        # Sort by value descending
        all_liqs.sort(key=lambda x: x["value_usd"], reverse=True)
        self._cache      = all_liqs
        self._cache_time = now
        return all_liqs

    def top(self, limit=10):
        return self.get_all()[:limit]

    def long_liquidations(self, limit=10):
        data = self.get_all()
        return [d for d in data if d["type"] == "LONG_LIQ"][:limit]

    def short_liquidations(self, limit=10):
        data = self.get_all()
        return [d for d in data if d["type"] == "SHORT_LIQ"][:limit]

    def summary(self):
        data     = self.get_all()
        if not data:
            return {}
        total_val   = sum(d["value_usd"] for d in data)
        long_liqs   = [d for d in data if d["type"] == "LONG_LIQ"]
        short_liqs  = [d for d in data if d["type"] == "SHORT_LIQ"]
        long_val    = sum(d["value_usd"] for d in long_liqs)
        short_val   = sum(d["value_usd"] for d in short_liqs)
        dominance   = "LONG_DOMINANT" if long_val > short_val else "SHORT_DOMINANT"

        return {
            "total_liquidated_usd": round(total_val, 2),
            "long_liquidated_usd":  round(long_val, 2),
            "short_liquidated_usd": round(short_val, 2),
            "dominance":            dominance,
            "long_count":           len(long_liqs),
            "short_count":          len(short_liqs),
            "biggest": data[0] if data else None,
            "timestamp": datetime.now().isoformat()
        }

    def cascade_alert(self):
        """Return True kalau ada liquidation cascade — total > $10M dalam 1 jam"""
        data      = self.get_all()
        now_ms    = time.time() * 1000
        cutoff_ms = now_ms - (3600 * 1000)
        recent    = [d for d in data if d.get("timestamp", 0) >= cutoff_ms]
        total     = sum(d["value_usd"] for d in recent)
        return {
            "cascade": total > 10_000_000,
            "total_1h_usd": round(total, 2),
            "threshold_usd": 10_000_000
        }