import json
import os
import time
import threading


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.join(BASE_DIR, "data")

DATA_FILE = os.path.join(DATA_DIR, "market_history.json")

DATASET_DIR = os.path.join(BASE_DIR, "dataset", "pending")


class MarketStorage:

    def __init__(self):

        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)

        if not os.path.exists(DATASET_DIR):
            os.makedirs(DATASET_DIR)

        if not os.path.exists(DATA_FILE):

            with open(DATA_FILE, "w") as f:
                json.dump([], f)

        # memory cache
        self.cache = []
        self.cache_timestamp = 0
        self.cache_ttl = 10

        # thread safety
        self.lock = threading.Lock()

        # snapshot timer
        self.last_snapshot = 0
        self.snapshot_interval = 4 * 60 * 60


    def load(self):

        with self.lock:

            if time.time() - self.cache_timestamp < self.cache_ttl:
                return list(self.cache)

            try:

                with open(DATA_FILE, "r") as f:

                    data = json.load(f)

                    self.cache = data
                    self.cache_timestamp = time.time()

                    return list(data)

            except:

                return []


    def atomic_replace(self, temp_file, target_file, retries=5):

        for _ in range(retries):

            try:

                os.replace(temp_file, target_file)
                return

            except PermissionError:

                time.sleep(0.2)

        raise PermissionError("Failed to replace market_history.json")


    def save(self, history):

        temp_file = DATA_FILE + ".tmp"

        with open(temp_file, "w") as f:

            json.dump(history, f)

        self.atomic_replace(temp_file, DATA_FILE)

        self.cache = history
        self.cache_timestamp = time.time()


    def prune_history(self, history):

        cutoff = time.time() - (90 * 24 * 60 * 60)

        filtered = []

        for item in history:

            try:

                ts = item.get("timestamp")

                ts_epoch = time.mktime(
                    time.strptime(ts, "%Y-%m-%dT%H:%M:%S")
                )

                if ts_epoch >= cutoff:
                    filtered.append(item)

            except:

                continue

        return filtered


    def create_snapshot(self, history):

        now = time.time()

        if now - self.last_snapshot < self.snapshot_interval:
            return

        try:

            ts = time.strftime("%Y%m%d_%H%M%S")

            file = os.path.join(
                DATASET_DIR,
                f"snapshot_{ts}.json"
            )

            sample = history[-5000:]

            with open(file, "w") as f:

                json.dump(sample, f)

            self.last_snapshot = now

        except:

            pass


    def append(self, records):

        with self.lock:

            history = self.load()

            history = self.prune_history(history)

            history.extend(records)

            self.save(history)

            self.create_snapshot(history)