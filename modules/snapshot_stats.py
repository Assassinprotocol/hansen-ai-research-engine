import os
import json
import time


# ================================
# SNAPSHOT STATISTICS
# ================================

class SnapshotStats:

    def __init__(self):

        self.pending_dir = r"C:\AI\hansen_engine\dataset\pending"
        self.failed_dir = r"C:\AI\hansen_engine\dataset\failed"
        self.state_file = r"C:\AI\hansen_engine\data\snapshot_state.json"

    # ================================
    # COUNT FILES
    # ================================
    def count_pending(self):

        if not os.path.exists(self.pending_dir):
            return 0

        return len([f for f in os.listdir(self.pending_dir) if f.endswith(".json")])

    def count_failed(self):

        if not os.path.exists(self.failed_dir):
            return 0

        return len([f for f in os.listdir(self.failed_dir) if f.endswith(".json")])

    # ================================
    # SNAPSHOT SIZES
    # ================================
    def snapshot_sizes(self):

        if not os.path.exists(self.pending_dir):
            return []

        sizes = []

        for f in os.listdir(self.pending_dir):

            if not f.endswith(".json"):
                continue

            path = os.path.join(self.pending_dir, f)

            size_kb = round(os.path.getsize(path) / 1024, 2)

            sizes.append({
                "file": f,
                "size_kb": size_kb
            })

        sizes.sort(key=lambda x: x["size_kb"], reverse=True)

        return sizes

    # ================================
    # NEXT SNAPSHOT ETA
    # ================================
    def next_snapshot_eta(self):

        if not os.path.exists(self.state_file):
            return "unknown"

        try:

            with open(self.state_file, "r") as f:
                state = json.load(f)

            last = state.get("last_snapshot", 0)

            next_ts = last + 14400

            remaining = next_ts - time.time()

            if remaining <= 0:
                return "due now"

            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)

            return f"{hours}h {minutes}m"

        except:
            return "unknown"

    # ================================
    # FULL REPORT
    # ================================
    def report(self):

        print("\nSnapshot Statistics\n")

        print(f"Pending Snapshots : {self.count_pending()}")
        print(f"Failed Snapshots  : {self.count_failed()}")
        print(f"Next Snapshot ETA : {self.next_snapshot_eta()}")

        sizes = self.snapshot_sizes()

        if sizes:

            print("\nPending Files:")

            for s in sizes:
                print(f"  {s['file']}: {s['size_kb']} KB")

        print()