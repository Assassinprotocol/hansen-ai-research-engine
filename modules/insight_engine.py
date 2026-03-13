from modules.market_history import MarketHistory
from modules.volatility import VolatilityDetector


class InsightEngine:

    def __init__(self):

        self.history = MarketHistory()
        self.volatility = VolatilityDetector()


    # =============================
    # GET ACTIVE COINS (TOP 10)
    # =============================
    def get_active_coins(self, limit=10):

        data = self.history.load_history()

        activity = {}

        for item in data:

            symbol = item["symbol"]

            if not symbol.endswith("USDT"):
                continue

            if symbol not in activity:
                activity[symbol] = 0

            activity[symbol] += 1

        ranked = sorted(
            activity.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return [x[0] for x in ranked[:limit]]


    # =============================
    # MOMENTUM
    # =============================
    def momentum(self, symbol="BTCUSDT", minutes=60):

        prices = self.history.get_recent_prices(symbol, minutes)

        if len(prices) < 5:
            return None

        start = prices[0]
        end = prices[-1]

        change = ((end - start) / start) * 100

        return round(change, 3)


    # =============================
    # MARKET ANALYSIS
    # =============================
    def analyze_market(self):

        coins = self.get_active_coins()

        # =============================
        # DATA SUFFICIENCY CHECK
        # =============================

        data = self.history.load_history()

        if len(data) < 50:

            return [
                "Market data still building. Waiting for more samples before generating analysis."
            ]

        result = []

        momentum_values = []
        volatility_values = []

        for coin in coins:

            vol = self.volatility.calculate(coin, 60)
            mom = self.momentum(coin, 60)

            if vol is None or mom is None:
                continue

            momentum_values.append(mom)
            volatility_values.append(vol)

            # -----------------------------
            # VOLATILITY SIGNAL
            # -----------------------------
            if vol > 0.5:

                result.append(
                    f"{coin} volatility expanding around {vol:.2f}% suggesting stronger trading activity"
                )

            # -----------------------------
            # MOMENTUM SIGNAL
            # -----------------------------
            if mom > 1:

                result.append(
                    f"{coin} gaining upward momentum with a {mom:.2f}% move over the past hour"
                )

            elif mom < -1:

                result.append(
                    f"{coin} showing downside pressure after moving {mom:.2f}% over the last hour"
                )

        # -----------------------------
        # MARKET MOMENTUM CONTEXT
        # -----------------------------
        if momentum_values:

            avg_mom = sum(momentum_values) / len(momentum_values)

            if avg_mom > 0.5:

                result.append(
                    "Overall momentum across major assets is leaning positive, suggesting buyers are gradually taking control"
                )

            elif avg_mom < -0.5:

                result.append(
                    "Broader market momentum appears slightly negative with selling pressure visible across several assets"
                )

            else:

                result.append(
                    "Momentum across the market remains relatively balanced without a strong directional bias"
                )

        # -----------------------------
        # VOLATILITY CONTEXT
        # -----------------------------
        if volatility_values:

            avg_vol = sum(volatility_values) / len(volatility_values)

            if avg_vol > 1:

                result.append(
                    "Volatility across the market has expanded recently which usually signals increased trading activity"
                )

            else:

                result.append(
                    "Volatility remains relatively contained suggesting the market is currently trading in a calmer environment"
                )

        # -----------------------------
        # RELATIVE STRENGTH
        # -----------------------------
        btc_mom = self.momentum("BTCUSDT", 60)
        eth_mom = self.momentum("ETHUSDT", 60)

        if btc_mom is not None and eth_mom is not None:

            if eth_mom > btc_mom:

                result.append(
                    "ETH is currently outperforming BTC in short term momentum"
                )

            elif btc_mom > eth_mom:

                result.append(
                    "BTC continues to hold stronger relative momentum compared to ETH"
                )

        return result