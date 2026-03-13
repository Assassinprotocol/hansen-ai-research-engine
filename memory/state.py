import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.join(BASE_DIR, "data")
STATE_FILE = os.path.join(DATA_DIR, "state.json")

os.makedirs(DATA_DIR, exist_ok=True)


class MemoryManager:

    def __init__(self):
        if not os.path.exists(STATE_FILE):
            with open(STATE_FILE, "w") as f:
                json.dump({}, f)

    def _load_all_topics(self):
        try:
            with open(STATE_FILE, "r") as f:
                data = json.load(f)
        except Exception:
            data = {}
        return data

    def _save(self, data):
        with open(STATE_FILE, "w") as f:
            json.dump(data, f, indent=4)

    def save_research(self, topic, entry):

        data = self._load_all_topics()

        if topic not in data:
            data[topic] = []

        if isinstance(entry, dict):
            entry["timestamp"] = datetime.utcnow().isoformat()
        else:
            entry = {
                "result": entry,
                "timestamp": datetime.utcnow().isoformat()
            }

        data[topic].append(entry)

        self._save(data)

    def get_topic_history(self, topic):

        data = self._load_all_topics()

        return data.get(topic, [])

    def get_history(self):

        data = self._load_all_topics()

        history = []

        for topic, entries in data.items():
            for e in entries:
                history.append({
                    "topic": topic,
                    "timestamp": e.get("timestamp", "OLD_DATA")
                })

        history.sort(key=lambda x: x["timestamp"], reverse=True)

        return history

    def get_topic_stats(self):

        data = self._load_all_topics()

        stats = []

        for topic, entries in data.items():
            stats.append((topic, len(entries)))

        stats.sort(key=lambda x: x[1], reverse=True)

        return stats

    def get_full_history(self):

        return self._load_all_topics()