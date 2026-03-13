import os
import json
import time


# ================================
# SNAPSHOT METADATA
# ================================

class SnapshotMetadata:

    def __init__(self):

        self.pending_dir = r"C:\AI\hansen_engine\dataset\pending"

    # ================================
    # GENERATE METADATA FOR SNAPSHOT
    # ================================
    def generate(self, snapshot_data, filename):

        if not snapshot_data:
            return {}

        symbols = set()
        timestamps = []
        prices = {}

        for item in snapshot_data:

            try:

                symbol = item["symbol"]
                price = float(item["price"])
                ts = item["timestamp"]

                symbols.add(symbol)

                if isinstance(ts, (int, float)):
                    timestamps.append(float(ts))

                if symbol not in prices:
                    prices[symbol] = []

                prices[symbol].append(price)

            except:
                continue

        oldest = min(timestamps) if timestamps else 0
        newest = max(timestamps) if timestamps else 0

        metadata = {
            "filename": filename,
            "created_at": time.time(),
            "total_records": len(snapshot_data),
            "unique_symbols": len(symbols),
            "time_range": {
                "start": oldest,
                "end": newest,
                "duration_hours": round((newest - oldest) / 3600, 2) if oldest and newest else 0
            },
            "symbols": list(symbols)
        }

        return metadata

    # ================================
    # SAVE METADATA ALONGSIDE SNAPSHOT
    # ================================
    def save(self, snapshot_data, snapshot_filename):

        metadata = self.generate(snapshot_data, snapshot_filename)

        if not metadata:
            return

        meta_filename = snapshot_filename.replace(".json", "_meta.json")

        meta_path = os.path.join(self.pending_dir, meta_filename)

        try:

            with open(meta_path, "w") as f:
                json.dump(metadata, f, indent=2)

            print(f"[METADATA] saved {meta_filename}")

        except Exception as e:

            print("[METADATA] failed:", e)

    # ================================
    # READ METADATA FOR A SNAPSHOT
    # ================================
    def read(self, snapshot_filename):

        meta_filename = snapshot_filename.replace(".json", "_meta.json")

        meta_path = os.path.join(self.pending_dir, meta_filename)

        if not os.path.exists(meta_path):
            return None

        try:

            with open(meta_path, "r") as f:
                return json.load(f)

        except:
            return None