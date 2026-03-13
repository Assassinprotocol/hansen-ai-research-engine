import os
import json
import time
from modules.snapshot_stats import SnapshotStats
from modules.snapshot_metadata import SnapshotMetadata
from modules.regime_tagger import RegimeTagger
from modules.movers_metadata import MoversMetadata
from modules.volatility_index import VolatilityIndex


# ================================
# DATASET AGENT
# ================================

class DatasetAgent:

    def __init__(self):

        self.snapshot_stats = SnapshotStats()
        self.snapshot_metadata = SnapshotMetadata()
        self.regime_tagger = RegimeTagger()
        self.movers_metadata = MoversMetadata()
        self.volatility_index = VolatilityIndex()

        self.pending_dir = r"C:\AI\hansen_engine\dataset\pending"

    # ================================
    # ENRICH SNAPSHOT
    # ================================
    def enrich_snapshot(self, snapshot_path):

        try:

            with open(snapshot_path, "r") as f:
                data = json.load(f)

            filename = os.path.basename(snapshot_path)

            # TAG REGIME
            data = self.regime_tagger.tag_snapshot(data)

            # GENERATE METADATA
            metadata = self.snapshot_metadata.generate(data, filename)

            # ATTACH MOVERS
            metadata = self.movers_metadata.attach(metadata)

            # ATTACH VOLATILITY INDEX
            vol_report = self.volatility_index.report()
            metadata["volatility_index"] = vol_report

            # SAVE ENRICHED SNAPSHOT
            with open(snapshot_path, "w") as f:
                json.dump(data, f, separators=(",", ":"))

            # SAVE METADATA
            self.snapshot_metadata.save(data, filename)

            print(f"[DATASET AGENT] Enriched: {filename}")

            return True

        except Exception as e:

            print(f"[DATASET AGENT] Failed: {e}")

            return False

    # ================================
    # PROCESS ALL PENDING
    # ================================
    def process_pending(self):

        if not os.path.exists(self.pending_dir):
            print("[DATASET AGENT] Pending folder not found")
            return

        files = [
            f for f in os.listdir(self.pending_dir)
            if f.endswith(".json") and "_meta" not in f
        ]

        if not files:
            print("[DATASET AGENT] No pending snapshots")
            return

        print(f"\n[DATASET AGENT] Processing {len(files)} snapshots\n")

        success = 0
        failed = 0

        for filename in files:

            path = os.path.join(self.pending_dir, filename)

            result = self.enrich_snapshot(path)

            if result:
                success += 1
            else:
                failed += 1

            time.sleep(1)

        print(f"\n[DATASET AGENT] Done — Success: {success} | Failed: {failed}\n")

    # ================================
    # RUN AGENT
    # ================================
    def run(self):

        print("\n[DATASET AGENT] Starting\n")

        self.process_pending()