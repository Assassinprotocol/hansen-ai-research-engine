import os


class DataIndex:

    def index_folder(self, folder):

        index = []

        if not os.path.exists(folder):
            return index

        for file in os.listdir(folder):

            path = os.path.join(folder, file)

            info = {
                "file": file,
                "path": path
            }

            index.append(info)

        return index