import time
from modules.market_history import MarketHistory

# ================================
# TOP MOVERS DETECTOR
# ================================

class TopMoversDetector:

    def __init__(self):
        self.history = MarketHistory()

    # ================================
    # PRICE CHANGE % PER SYMBOL
    # ================================

    def get_change(self, symbol, minutes=60):
        prices = self.history.get_recent_prices(symbol, minutes)
        if len(prices) < 2:
            return None
        start = prices[0]
        end = prices[-1]
        change = ((end - start) / start) * 100
        return round(change, 3)

    # ================================
    # DETECT TOP MOVERS
    # ================================

    def detect(self, limit=10, minutes=60):
        symbols = self.history.get_active_symbols(min_records=2)
        movers = []
        for symbol in symbols:
            change = self.get_change(symbol, minutes)
            if change is None:
                continue
            movers.append({
                "symbol": symbol,
                "change_pct": change
            })
        movers.sort(key=lambda x: abs(x["change_pct"]), reverse=True)
        return movers[:limit]

    # ================================
    # GAINERS ONLY
    # ================================

    def gainers(self, limit=5, minutes=60):
        movers = self.detect(limit * 2, minutes)
        return [m for m in movers if m["change_pct"] > 0][:limit]

    # ================================
    # LOSERS ONLY
    # ================================

    def losers(self, limit=5, minutes=60):
        movers = self.detect(limit * 2, minutes)
        return [m for m in movers if m["change_pct"] < 0][:limit]