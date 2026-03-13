import time
from modules.market_history import MarketHistory


# ================================
# MARKET REGIME DETECTOR
# ================================

class MarketRegimeDetector:

    def __init__(self):

        self.history = MarketHistory()

    # ================================
    # DETECT REGIME FOR ONE SYMBOL
    # ================================
    def detect(self, symbol="BTCUSDT", minutes=60):

        prices = self.history.get_recent_prices(symbol, minutes)

        if len(prices) < 10:
            return "unknown"

        start = prices[0]
        end = prices[-1]

        change = ((end - start) / start) * 100

        high = max(prices)
        low = min(prices)

        range_pct = ((high - low) / low) * 100

        if change > 1.5:
            return "bull"

        elif change < -1.5:
            return "bear"

        elif range_pct < 1.0:
            return "sideways"

        else:
            return "ranging"

    # ================================
    # MARKET WIDE REGIME
    # ================================
    def market_regime(self):

        coins = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]

        regimes = {}

        for coin in coins:

            regime = self.detect(coin, 60)

            regimes[coin] = regime

        # ================================
        # MAJORITY VOTE
        # ================================

        counts = {"bull": 0, "bear": 0, "sideways": 0, "ranging": 0, "unknown": 0}

        for r in regimes.values():
            counts[r] += 1

        dominant = max(counts, key=counts.get)

        return {
            "regime": dominant,
            "breakdown": regimes
        }