import os
from rag.vector_store import VectorStore


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KNOWLEDGE_DIR = os.path.join(BASE_DIR, "knowledge")


class DocumentIngestor:

    def __init__(self):

        self.store = VectorStore()

    def ingest(self, text):

        self.store.add_document(text, file)

        print("Document stored in RAG.")

    def ingest_folder(self):

        if not os.path.exists(KNOWLEDGE_DIR):
            print("Knowledge folder not found.")
            return

        files = os.listdir(KNOWLEDGE_DIR)

        for file in files:

            path = os.path.join(KNOWLEDGE_DIR, file)

            if not file.endswith(".txt"):
                continue

            with open(path, "r", encoding="utf-8") as f:
                text = f.read()

            self.store.add_document(text, file)

            print(f"Ingested: {file}")