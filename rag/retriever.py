from rag.vector_store import VectorStore


class Retriever:

    def __init__(self):

        self.store = VectorStore()

    def retrieve(self, query):

        results = self.store.search(query)

        if not results:
            return None

        context = "\n".join(results)

        return context