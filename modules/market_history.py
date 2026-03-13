import json
import os
import time
import threading

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.environ.get("HANSEN_DATA_FILE", os.path.join(BASE_DIR, "data", "market_history.json"))

_lock = threading.Lock()


class MarketHistory:

    def __init__(self):

        if not os.path.exists(DATA_FILE):
            raise FileNotFoundError("market_history.json not found")

        self._cache = None
        self._cache_time = 0
        self._cache_ttl = 30

    def load(self):

        now = time.time()

        if self._cache and (now - self._cache_time < self._cache_ttl):
            return self._cache

        with _lock:
            for attempt in range(3):
                try:
                    with open(DATA_FILE, "r") as f:
                        data = json.load(f)
                    self._cache = data
                    self._cache_time = now
                    return data
                except Exception:
                    time.sleep(0.5)

        return self._cache if self._cache else []

    def load_history(self):
        return self.load()

    def get_symbol_history(self, symbol):

        data = self.load()
        history = []

        for item in data:
            try:
                if item["symbol"] == symbol:
                    history.append(item)
            except:
                continue

        return history

    def get_recent_prices(self, symbol, minutes=60):

        data = self.load_history()
        cutoff = time.time() - (minutes * 60)
        prices = []

        for item in data:
            try:
                if item["symbol"] != symbol:
                    continue

                ts = item["timestamp"]

                if isinstance(ts, (int, float)):
                    ts_epoch = float(ts)
                else:
                    from datetime import datetime
                    ts_epoch = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S").timestamp()

                if ts_epoch >= cutoff:
                    prices.append(float(item["price"]))

            except:
                continue

        if len(prices) < 2:
            fallback = []
            for item in data:
                try:
                    if item["symbol"] != symbol:
                        continue
                    fallback.append(float(item["price"]))
                except:
                    continue
            prices = fallback[-20:]

        return prices

    def get_all_symbols(self):

        data = self.load()
        symbols = set()

        for item in data:
            try:
                symbol = item["symbol"]
                if symbol.endswith("USDT"):
                    symbols.add(symbol)
            except:
                continue

        return list(symbols)

    def get_active_symbols(self, min_records=30):

        data = self.load()
        counts = {}

        for item in data:
            try:
                symbol = item["symbol"]
                if not symbol.endswith("USDT"):
                    continue
                if symbol not in counts:
                    counts[symbol] = 0
                counts[symbol] += 1
            except:
                continue

        return [s for s, c in counts.items() if c >= min_records]

    def get_latest_price(self, symbol):

        history = self.get_symbol_history(symbol)

        if not history:
            return None

        try:
            return history[-1]["price"]
        except:
            return None

    def get_price_change(self, symbol, minutes=60):

        prices = self.get_recent_prices(symbol, minutes)

        if len(prices) < 2:
            return None

        start = prices[0]
        end = prices[-1]

        change = ((end - start) / start) * 100

        return round(change, 3)