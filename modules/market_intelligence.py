import json
import os
import statistics
import time


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(BASE_DIR, "data", "market_history.json")


# ================================
# SECTOR MAP
# ================================

SECTOR_MAP = {

    "BTCUSDT": "store_of_value",
    "ETHUSDT": "layer1",

    "BNBUSDT": "exchange",
    "SOLUSDT": "layer1",
    "ADAUSDT": "layer1",
    "AVAXUSDT": "layer1",

    "ARB": "layer2",
    "OP": "layer2",

    "LINKUSDT": "oracle",
    "PYTH": "oracle",

    "UNIUSDT": "dex",
    "SUSHIUSDT": "dex",
    "CAKEUSDT": "dex",

    "AAVEUSDT": "defi",
    "COMPUSDT": "defi",

    "MATICUSDT": "scaling",

    "DOGEUSDT": "meme",
    "SHIBUSDT": "meme"
}


class MarketIntelligence:

    def __init__(self):

        if not os.path.exists(DATA_FILE):
            raise FileNotFoundError("market_history.json not found")


    def load_data(self):

        with open(DATA_FILE, "r") as f:
            return json.load(f)


    def get_recent_prices(self, symbol, minutes=60):

        data = self.load_data()

        cutoff = time.time() - (minutes * 60)

        prices = []

        for item in data:

            try:

                if item["symbol"] != symbol:
                    continue

                ts = item["timestamp"]

                if ts >= cutoff:

                    prices.append(item["price"])

            except:

                continue

        return prices


    def volatility(self, symbol="BTCUSDT", minutes=60):

        prices = self.get_recent_prices(symbol, minutes)

        if len(prices) < 5:
            return None

        high = max(prices)
        low = min(prices)

        vol = ((high - low) / low) * 100

        return round(vol, 2)


    def momentum(self, symbol="BTCUSDT", minutes=60):

        prices = self.get_recent_prices(symbol, minutes)

        if len(prices) < 5:
            return None

        start = prices[0]
        end = prices[-1]

        change = ((end - start) / start) * 100

        return round(change, 2)


    def market_summary(self):

        coins = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]

        result = {}

        for coin in coins:

            vol = self.volatility(coin, 60)
            mom = self.momentum(coin, 60)

            result[coin] = {
                "volatility_1h": vol,
                "momentum_1h": mom
            }

        return result


    # ======================================
    # SECTOR ANALYSIS
    # ======================================

    def detect_sector_strength(self):

        sectors = {}

        for symbol, sector in SECTOR_MAP.items():

            mom = self.momentum(symbol, 60)

            if mom is None:
                continue

            if sector not in sectors:
                sectors[sector] = []

            sectors[sector].append(mom)

        sector_strength = {}

        for sector, values in sectors.items():

            if len(values) == 0:
                continue

            avg = statistics.mean(values)

            sector_strength[sector] = round(avg, 2)

        return sector_strength


    def sector_leaders(self):

        sectors = self.detect_sector_strength()

        if not sectors:
            return None

        strongest = max(sectors, key=sectors.get)
        weakest = min(sectors, key=sectors.get)

        return {
            "strongest_sector": strongest,
            "strength": sectors[strongest],
            "weakest_sector": weakest,
            "weakness": sectors[weakest]
        }