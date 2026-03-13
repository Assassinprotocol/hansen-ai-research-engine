import time
import statistics
from modules.market_history import MarketHistory


# ================================
# VOLATILITY INDEX
# ================================

class VolatilityIndex:

    def __init__(self):

        self.history = MarketHistory()

    # ================================
    # CALCULATE INDEX
    # ================================
    def calculate(self, minutes=60):

        symbols = self.history.get_active_symbols(min_records=2)

        values = []

        for symbol in symbols:

            prices = self.history.get_recent_prices(symbol, minutes)

            if len(prices) < 2:
                continue

            returns = []

            for i in range(1, len(prices)):

                change = (prices[i] - prices[i-1]) / prices[i-1]

                returns.append(change)

            if len(returns) < 2:
                continue

            vol = statistics.stdev(returns) * 100

            values.append(vol)

        if not values:
            return None

        index = statistics.mean(values)

        return round(index, 4)

    # ================================
    # VOLATILITY LEVEL
    # ================================
    def level(self, minutes=60):

        index = self.calculate(minutes)

        if index is None:
            return "unknown"

        if index > 0.5:
            return "high"

        elif index > 0.2:
            return "medium"

        else:
            return "low"

    # ================================
    # FULL REPORT
    # ================================
    def report(self, minutes=60):

        index = self.calculate(minutes)
        lvl = self.level(minutes)

        return {
            "index": index,
            "level": lvl,
            "minutes": minutes
        }