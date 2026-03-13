import statistics
from modules.market_history import MarketHistory


# ================================
# VOLATILITY DETECTOR
# ================================

class VolatilityDetector:

    def __init__(self):

        self.history = MarketHistory()

    # ================================
    # SINGLE SYMBOL VOLATILITY
    # ================================
    def calculate(self, symbol="BTCUSDT", minutes=60):

        prices = self.history.get_recent_prices(symbol, minutes)

        if len(prices) < 10:
            return None

        returns = []

        for i in range(1, len(prices)):

            change = (prices[i] - prices[i-1]) / prices[i-1]

            returns.append(change)

        if len(returns) < 2:
            return None

        volatility = statistics.stdev(returns)

        return round(volatility * 100, 4)

    # ================================
    # VOLATILITY RANKING
    # ================================
    def rank_volatility(self, minutes=60):

        symbols = self.history.get_active_symbols()

        results = []

        for symbol in symbols:

            vol = self.calculate(symbol, minutes)

            if vol is None:
                continue

            results.append({
                "symbol": symbol,
                "volatility": vol
            })

        results.sort(key=lambda x: x["volatility"], reverse=True)

        return results

    # ================================
    # MARKET VOLATILITY INDEX
    # ================================
    def market_index(self, minutes=60):

        ranked = self.rank_volatility(minutes)

        if not ranked:
            return None

        values = [r["volatility"] for r in ranked]

        avg = statistics.mean(values)

        return round(avg, 4)

    # ================================
    # TOP VOLATILE SYMBOLS
    # ================================
    def top_volatile(self, limit=5, minutes=60):

        ranked = self.rank_volatility(minutes)

        return ranked[:limit]