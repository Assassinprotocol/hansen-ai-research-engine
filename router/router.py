class IntentRouter:

    def __init__(self):
        pass

    def route(self, message, context="", mode="strict"):

        message_lower = message.lower()

        if "btc" in message_lower or "bitcoin" in message_lower:
            return f"[Crypto Insight]\nAnalyzing topic: {message}"

        if "inflation" in message_lower or "fed" in message_lower:
            return f"[Macro Insight]\nAnalyzing topic: {message}"

        if "stocks" in message_lower or "nasdaq" in message_lower:
            return f"[Equity Insight]\nAnalyzing topic: {message}"

        return f"[General Analysis]\nProcessing topic: {message}"