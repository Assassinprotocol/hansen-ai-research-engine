import os
import json
import time


# ================================
# DATASET TRAINING PIPELINE
# ================================

class TrainingPipeline:

    def __init__(self):

        self.pending_dir = r"C:\AI\hansen_engine\dataset\pending"
        self.processed_dir = r"C:\AI\hansen_engine\dataset\processed"
        self.training_dir = r"C:\AI\hansen_engine\dataset\training"

        os.makedirs(self.processed_dir, exist_ok=True)
        os.makedirs(self.training_dir, exist_ok=True)

    # ================================
    # LOAD SNAPSHOT
    # ================================
    def load_snapshot(self, path):

        try:

            with open(path, "r") as f:
                return json.load(f)

        except:
            return None

    # ================================
    # CONVERT TO TRAINING FORMAT
    # ================================
    def convert(self, snapshot_data, filename):

        if not snapshot_data:
            return None

        samples = []

        symbols = {}

        for item in snapshot_data:

            try:

                symbol = item["symbol"]
                price = float(item["price"])
                ts = item.get("timestamp", 0)
                regime = item.get("market_regime", "unknown")

                if symbol not in symbols:
                    symbols[symbol] = []

                symbols[symbol].append({
                    "price": price,
                    "timestamp": ts,
                    "regime": regime
                })

            except:
                continue

        for symbol, records in symbols.items():

            if len(records) < 5:
                continue

            prices = [r["price"] for r in records]

            start = prices[0]
            end = prices[-1]

            change = ((end - start) / start) * 100

            regime = records[-1].get("regime", "unknown")

            sample = {
                "symbol": symbol,
                "price_start": start,
                "price_end": end,
                "change_pct": round(change, 3),
                "regime": regime,
                "records": len(records),
                "source": filename
            }

            samples.append(sample)

        return samples

    # ================================
    # PROCESS SNAPSHOT
    # ================================
    def process(self, snapshot_path):

        filename = os.path.basename(snapshot_path)

        data = self.load_snapshot(snapshot_path)

        if not data:
            print(f"[PIPELINE] Failed to load: {filename}")
            return False

        samples = self.convert(data, filename)

        if not samples:
            print(f"[PIPELINE] No samples generated: {filename}")
            return False

        training_file = os.path.join(
            self.training_dir,
            filename.replace(".json", "_training.json")
        )

        with open(training_file, "w") as f:
            json.dump(samples, f, indent=2)

        processed_path = os.path.join(self.processed_dir, filename)

        os.rename(snapshot_path, processed_path)

        print(f"[PIPELINE] Processed: {filename} → {len(samples)} samples")

        return True

    # ================================
    # RUN PIPELINE
    # ================================
    def run(self):

        if not os.path.exists(self.pending_dir):
            print("[PIPELINE] Pending folder not found")
            return

        files = [
            f for f in os.listdir(self.pending_dir)
            if f.endswith(".json") and "_meta" not in f
        ]

        if not files:
            print("[PIPELINE] No snapshots to process")
            return

        print(f"\n[PIPELINE] Processing {len(files)} snapshots\n")

        success = 0
        failed = 0

        for filename in files:

            path = os.path.join(self.pending_dir, filename)

            result = self.process(path)

            if result:
                success += 1
            else:
                failed += 1

            time.sleep(1)

        print(f"\n[PIPELINE] Done — Success: {success} | Failed: {failed}\n")