import os
import time
import json


# ================================
# ENGINE HEALTH MONITOR
# ================================

class HealthMonitor:

    def __init__(self):

        self.data_dir = r"C:\AI\hansen_engine\data"
        self.dataset_dir = r"C:\AI\hansen_engine\dataset"

    # ================================
    # CHECK DATA FILES
    # ================================
    def check_data_files(self):

        files = {
            "market_history": os.path.join(self.data_dir, "market_history.json"),
            "metrics": os.path.join(self.data_dir, "metrics.json"),
            "snapshot_state": os.path.join(self.data_dir, "snapshot_state.json")
        }

        result = {}

        for name, path in files.items():

            if os.path.exists(path):

                size = os.path.getsize(path)

                result[name] = {
                    "status": "ok",
                    "size_kb": round(size / 1024, 2)
                }

            else:

                result[name] = {
                    "status": "missing",
                    "size_kb": 0
                }

        return result

    # ================================
    # CHECK DATASET FOLDERS
    # ================================
    def check_dataset_folders(self):

        folders = {
            "pending": os.path.join(self.dataset_dir, "pending"),
            "failed": os.path.join(self.dataset_dir, "failed")
        }

        result = {}

        for name, path in folders.items():

            if os.path.exists(path):

                files = [f for f in os.listdir(path) if f.endswith(".json")]

                result[name] = {
                    "status": "ok",
                    "count": len(files)
                }

            else:

                result[name] = {
                    "status": "missing",
                    "count": 0
                }

        return result

    # ================================
    # LAST SNAPSHOT TIME
    # ================================
    def last_snapshot_time(self):

        state_file = os.path.join(self.data_dir, "snapshot_state.json")

        if not os.path.exists(state_file):
            return None

        try:

            with open(state_file, "r") as f:
                state = json.load(f)

            ts = state.get("last_snapshot", 0)

            elapsed = time.time() - ts

            hours = int(elapsed // 3600)
            minutes = int((elapsed % 3600) // 60)

            return f"{hours}h {minutes}m ago"

        except:
            return None

    # ================================
    # FULL HEALTH REPORT
    # ================================
    def report(self):

        data_files = self.check_data_files()
        dataset_folders = self.check_dataset_folders()
        last_snapshot = self.last_snapshot_time()

        print("\nEngine Health Report\n")

        print("Data Files:")
        for name, info in data_files.items():
            print(f"  {name}: {info['status']} ({info['size_kb']} KB)")

        print("\nDataset Folders:")
        for name, info in dataset_folders.items():
            print(f"  {name}: {info['status']} ({info['count']} files)")

        print("\nLast Snapshot:", last_snapshot or "never")
        print()