import json
import os
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(BASE_DIR, "data", "market_data.json")

TTL_DAYS = 90
TTL_SECONDS = TTL_DAYS * 86400


class MarketStore:

    def __init__(self):

        if not os.path.exists(DATA_FILE):
            with open(DATA_FILE, "w") as f:
                json.dump([], f)

    def load(self):

        with open(DATA_FILE, "r") as f:
            return json.load(f)

    def save(self, data):

        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)

    def add(self, symbol, price):

        data = self.load()

        data.append({
            "symbol": symbol,
            "price": price,
            "timestamp": time.time()
        })

        self.clean(data)

        self.save(data)

    def clean(self, data):

        now = time.time()

        data[:] = [
            d for d in data
            if now - d["timestamp"] < TTL_SECONDS
        ]