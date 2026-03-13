class ProfileAnalyzer:

    def __init__(self):
        pass

    def detect_user_profile(self, history):

        if not history:
            return None

        crypto_count = 0
        macro_count = 0

        for topic, entries in history.items():

            topic_lower = topic.lower()

            if "btc" in topic_lower or "crypto" in topic_lower:
                crypto_count += len(entries)

            if "inflation" in topic_lower or "fed" in topic_lower:
                macro_count += len(entries)

        total = crypto_count + macro_count

        if total == 0:
            return None

        ratio = crypto_count / total

        if ratio > 0.7:
            return "High"

        if ratio > 0.4:
            return "Medium"

        return "Variable"