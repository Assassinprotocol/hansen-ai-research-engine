class ResearchModule:

    def __init__(self):
        pass

    def process(self, topic, router):

        try:
            result = router(topic)

            formatted = f"""
=== Hansen Research ===

Topic:
{topic}

Analysis:
{result}

=======================
"""

            return formatted.strip()

        except Exception as e:
            raise RuntimeError(f"Research processing failed: {str(e)}")