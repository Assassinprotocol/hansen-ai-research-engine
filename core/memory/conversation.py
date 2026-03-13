class ConversationMemory:

    def __init__(self):
        self.history = []

    def add(self, role, message):

        self.history.append({
            "role": role,
            "message": message
        })

    def get_formatted_history(self):

        if not self.history:
            return ""

        lines = []

        for entry in self.history[-10:]:
            role = entry["role"]
            message = entry["message"]

            lines.append(f"{role}: {message}")

        return "\n".join(lines)