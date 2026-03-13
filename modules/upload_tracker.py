import os
import json
import time

class UploadTracker:
    def __init__(self):
        self.tracker_file = r"C:\AI\hansen_engine\data\upload_tracker.json"

    def load(self):
        if not os.path.exists(self.tracker_file):
            return []
        try:
            with open(self.tracker_file, "r") as f:
                data = json.load(f)
            if not isinstance(data, list):
                return []
            return [d for d in data if isinstance(d, dict)]
        except:
            return []

    def save(self, data):
        try:
            with open(self.tracker_file, "w") as f:
                json.dump(data, f, indent=2)
        except:
            pass

    def record(self, filename, status="success", blob=None):
        data = self.load()
        data.append({
            "timestamp": time.time(),
            "filename": filename,
            "status": status,
            "blob": blob or ""
        })
        self.save(data)

    def total_uploads(self):
        data = self.load()
        return len([d for d in data if d.get("status") == "success"])

    def total_failed(self):
        data = self.load()
        return len([d for d in data if d.get("status") == "failed"])

    def recent(self, limit=10):
        data = self.load()
        data.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        return data[:limit]

    def report(self):
        print("\nUpload Tracker\n")
        print(f"Total Uploaded  : {self.total_uploads()}")
        print(f"Total Failed    : {self.total_failed()}")
        recent = self.recent()
        if recent:
            print("\nRecent Uploads:")
            for item in recent:
                ts = time.strftime(
                    "%Y-%m-%d %H:%M",
                    time.localtime(item.get("timestamp", 0))
                )
                print(f"  {ts} | {item['status']} | {item['filename']}")
        print()