import json
import os


class DataAdapter:

    def read_json(self, path):

        if not os.path.exists(path):
            return None

        with open(path, "r") as f:
            return json.load(f)

    def read_text(self, path):

        if not os.path.exists(path):
            return None

        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def read_folder(self, folder):

        data = {}

        if not os.path.exists(folder):
            return data

        for file in os.listdir(folder):

            path = os.path.join(folder, file)

            if file.endswith(".txt"):
                data[file] = self.read_text(path)

            elif file.endswith(".json"):
                data[file] = self.read_json(path)

        return data