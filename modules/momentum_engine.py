import time
from modules.market_history import MarketHistory


# ================================
# MOMENTUM ENGINE
# ================================

class MomentumEngine:

    def __init__(self):

        self.history = MarketHistory()

    # ================================
    # SINGLE SYMBOL MOMENTUM
    # ================================
    def calculate(self, symbol="BTCUSDT", minutes=60):

        prices = self.history.get_recent_prices(symbol, minutes)

        if len(prices) < 5:
            return None

        start = prices[0]
        end = prices[-1]

        change = ((end - start) / start) * 100

        return round(change, 3)

    # ================================
    # MOMENTUM RANKING
    # ================================
    def rank_momentum(self, minutes=60):

        symbols = self.history.get_active_symbols()

        results = []

        for symbol in symbols:

            mom = self.calculate(symbol, minutes)

            if mom is None:
                continue

            results.append({
                "symbol": symbol,
                "momentum": mom
            })

        results.sort(key=lambda x: x["momentum"], reverse=True)

        return results

    # ================================
    # TOP GAINERS
    # ================================
    def top_gainers(self, limit=5, minutes=60):

        ranked = self.rank_momentum(minutes)

        return ranked[:limit]

    # ================================
    # TOP LOSERS
    # ================================
    def top_losers(self, limit=5, minutes=60):

        ranked = self.rank_momentum(minutes)

        return ranked[-limit:]

    # ================================
    # MOMENTUM SUMMARY
    # ================================
    def summary(self, minutes=60):

        gainers = self.top_gainers(5, minutes)
        losers = self.top_losers(5, minutes)

        return {
            "top_gainers": gainers,
            "top_losers": losers
        }