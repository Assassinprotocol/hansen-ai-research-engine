import os
import json
import time


# ================================
# LOGGER STATISTICS
# ================================

class LoggerStats:

    def __init__(self):

        self.data_file = r"C:\AI\hansen_engine\data\market_history.json"

    # ================================
    # LOAD DATA
    # ================================
    def load(self):

        if not os.path.exists(self.data_file):
            return []

        try:

            with open(self.data_file, "r") as f:
                return json.load(f)

        except:
            return []

    # ================================
    # TOTAL RECORDS
    # ================================
    def total_records(self):

        data = self.load()

        return len(data)

    # ================================
    # UNIQUE SYMBOLS
    # ================================
    def unique_symbols(self):

        data = self.load()

        symbols = set()

        for item in data:

            try:
                symbols.add(item["symbol"])
            except:
                continue

        return len(symbols)

    # ================================
    # OLDEST RECORD
    # ================================
    def oldest_record(self):

        data = self.load()

        if not data:
            return None

        timestamps = []

        for item in data:

            try:

                ts = item["timestamp"]

                if isinstance(ts, (int, float)):
                    timestamps.append(float(ts))

            except:
                continue

        if not timestamps:
            return None

        oldest = min(timestamps)

        elapsed = time.time() - oldest

        days = int(elapsed // 86400)
        hours = int((elapsed % 86400) // 3600)

        return f"{days}d {hours}h ago"

    # ================================
    # RECORDS PER SYMBOL (TOP 10)
    # ================================
    def records_per_symbol(self, limit=10):

        data = self.load()

        counts = {}

        for item in data:

            try:

                symbol = item["symbol"]

                if symbol not in counts:
                    counts[symbol] = 0

                counts[symbol] += 1

            except:
                continue

        ranked = sorted(counts.items(), key=lambda x: x[1], reverse=True)

        return ranked[:limit]

    # ================================
    # FULL STATS REPORT
    # ================================
    def report(self):

        print("\nLogger Statistics\n")

        print(f"Total Records   : {self.total_records()}")
        print(f"Unique Symbols  : {self.unique_symbols()}")
        print(f"Oldest Record   : {self.oldest_record() or 'unknown'}")

        print("\nTop 10 Symbols by Record Count:")

        for symbol, count in self.records_per_symbol():
            print(f"  {symbol}: {count}")

        print()