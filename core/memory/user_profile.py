class UserProfile:

    def __init__(self):
        self.profile = {}

    def set_attribute(self, key, value):
        self.profile[key] = value

    def get_attribute(self, key):
        return self.profile.get(key)

    def get_formatted_profile(self):

        if not self.profile:
            return ""

        lines = []

        for k, v in self.profile.items():
            lines.append(f"{k}: {v}")

        return "\n".join(lines)