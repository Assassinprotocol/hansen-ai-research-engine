class InsightAnalyzer:

    def __init__(self):
        pass

    def generate_insight(self, history):

        if not history:
            return None

        topic_count = {}

        for topic, entries in history.items():
            topic_count[topic] = len(entries)

        most_topic = max(topic_count, key=topic_count.get)

        return {
            "most_topic": most_topic,
            "count": topic_count[most_topic]
        }