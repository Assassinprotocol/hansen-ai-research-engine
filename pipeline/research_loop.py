import time
from agents.research_agent import ResearchAgent
from modules.insight_engine import InsightEngine
from modules.market_regime import MarketRegimeDetector
from modules.momentum_engine import MomentumEngine


# ================================
# AUTONOMOUS RESEARCH LOOP
# ================================

class ResearchLoop:

    def __init__(self):

        self.agent = ResearchAgent()
        self.insight = InsightEngine()
        self.regime = MarketRegimeDetector()
        self.momentum = MomentumEngine()

    # ================================
    # BUILD CONTEXT
    # ================================
    def build_context(self):

        signals = self.insight.analyze_market()
        regime_info = self.regime.market_regime()
        gainers = self.momentum.top_gainers(3)
        losers = self.momentum.top_losers(3)

        regime = regime_info.get("regime", "unknown").upper()

        context = f"Market Regime: {regime}\n"

        if gainers:
            context += "\nTop Gainers:\n"
            for g in gainers:
                context += f"  {g['symbol']}: +{g['momentum']}%\n"

        if losers:
            context += "\nTop Losers:\n"
            for l in losers:
                context += f"  {l['symbol']}: {l['momentum']}%\n"

        if signals:
            context += "\nMarket Signals:\n"
            for s in signals:
                context += f"  - {s}\n"

        return context

    # ================================
    # GENERATE TOPICS
    # ================================
    def generate_topics(self):

        regime_info = self.regime.market_regime()
        regime = regime_info.get("regime", "unknown")

        gainers = self.momentum.top_gainers(3)

        topics = [f"crypto market {regime} regime analysis"]

        for g in gainers:
            symbol = g["symbol"].replace("USDT", "")
            topics.append(f"{symbol} price momentum analysis")

        return topics

    # ================================
    # RUN ONCE
    # ================================
    def run_once(self):

        print("\n[RESEARCH LOOP] Building context\n")

        context = self.build_context()
        topics = self.generate_topics()

        print(f"[RESEARCH LOOP] Topics: {topics}\n")

        results = self.agent.run(topics, context)

        return results

    # ================================
    # RUN LOOP
    # ================================
    def run(self, interval=3600):

        print("\n[RESEARCH LOOP] Autonomous loop started\n")

        while True:

            try:

                self.run_once()

            except Exception as e:

                print(f"[RESEARCH LOOP] Error: {e}")

            print(f"[RESEARCH LOOP] Next run in {interval//60} minutes\n")

            time.sleep(interval)