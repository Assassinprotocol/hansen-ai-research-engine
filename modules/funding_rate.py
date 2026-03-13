import requests
import time
from datetime import datetime

# ================================
# FUNDING RATE TRACKER
# Top 20 symbols by absolute funding
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

class FundingRateTracker:

    def __init__(self):
        self._cache      = None
        self._cache_time = 0
        self._cache_ttl  = 60  # 1 menit cache

    def _fetch(self):
        try:
            res  = requests.get(
                f"{BASE_URL}/fapi/v1/premiumIndex",
                timeout=10
            )
            data = res.json()
            if not isinstance(data, list):
                return []

            results = []
            for item in data:
                sym = item.get("symbol", "")
                if sym not in TRACKED_SYMBOLS:
                    continue
                try:
                    rate = float(item.get("lastFundingRate", 0)) * 100  # convert to %
                    mark = float(item.get("markPrice", 0))
                    idx  = float(item.get("indexPrice", 0))
                    results.append({
                        "symbol":       sym.replace("USDT", ""),
                        "funding_rate": round(rate, 4),
                        "mark_price":   round(mark, 4),
                        "index_price":  round(idx, 4),
                        "premium":      round(mark - idx, 4),
                        "sentiment":    self._sentiment(rate)
                    })
                except:
                    continue

            # Sort by absolute funding rate
            results.sort(key=lambda x: abs(x["funding_rate"]), reverse=True)
            return results

        except Exception as e:
            print(f"[FUNDING] Fetch error: {e}")
            return []

    def _sentiment(self, rate):
        if rate > 0.05:   return "VERY_LONG"
        if rate > 0.01:   return "LONG"
        if rate < -0.05:  return "VERY_SHORT"
        if rate < -0.01:  return "SHORT"
        return "NEUTRAL"

    def get(self, limit=20):
        now = time.time()
        if self._cache and (now - self._cache_time < self._cache_ttl):
            return self._cache[:limit]
        data = self._fetch()
        if data:
            self._cache      = data
            self._cache_time = now
        return (self._cache or [])[:limit]

    def extremes(self, limit=5):
        """Top coins dengan funding paling extreme (long + short)"""
        data     = self.get(30)
        longs    = [d for d in data if d["funding_rate"] > 0][:limit]
        shorts   = [d for d in data if d["funding_rate"] < 0][:limit]
        return {"longs": longs, "shorts": shorts}

    def summary(self):
        data = self.get(30)
        if not data:
            return {}
        rates       = [d["funding_rate"] for d in data]
        avg         = round(sum(rates) / len(rates), 4)
        positive    = len([r for r in rates if r > 0])
        negative    = len([r for r in rates if r < 0])
        sentiment   = "GREED" if avg > 0.01 else "FEAR" if avg < -0.01 else "NEUTRAL"
        return {
            "avg_funding":    avg,
            "positive_count": positive,
            "negative_count": negative,
            "market_sentiment": sentiment,
            "timestamp":      datetime.now().isoformat()
        }