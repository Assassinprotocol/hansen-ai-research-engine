import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
VECTOR_FILE = os.path.join(DATA_DIR, "rag_store.json")

os.makedirs(DATA_DIR, exist_ok=True)


class VectorStore:

    def __init__(self):

        if not os.path.exists(VECTOR_FILE):
            with open(VECTOR_FILE, "w") as f:
                json.dump([], f)

    def load(self):

        with open(VECTOR_FILE, "r") as f:
            return json.load(f)

    def save(self, data):

        with open(VECTOR_FILE, "w") as f:
            json.dump(data, f, indent=4)

    def add_document(self, text, source="unknown"):

        data = self.load()

        data.append({
            "text": text,
            "source": source
        })

        self.save(data)

    def search(self, query):

        data = self.load()

        results = []

        for item in data:
            if query.lower() in item["text"].lower():
                results.append(item["text"])

        return results[:5]