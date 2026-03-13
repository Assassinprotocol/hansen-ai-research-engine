import requests
import time
from modules.insight_engine import InsightEngine
from modules.market_regime import MarketRegimeDetector
from modules.volatility_index import VolatilityIndex


# ================================
# AI INSIGHT IMPROVER
# ================================

class InsightImprover:

    def __init__(self):

        self.insight = InsightEngine()
        self.regime = MarketRegimeDetector()
        self.vol_index = VolatilityIndex()
        self.llm_url = "http://127.0.0.1:8080/completion"

    # ================================
    # QUERY LLM
    # ================================
    def query(self, prompt, max_tokens=250):

        try:

            response = requests.post(
                self.llm_url,
                json={
                    "prompt": prompt,
                    "n_predict": max_tokens,
                    "temperature": 0.3,
                    "top_p": 0.9,
                    "repeat_penalty": 1.1,
                    "stop": ["```", "User:", "Human:"]
                },
                timeout=180
            )

            return response.json().get("content", "").strip()

        except Exception as e:

            return f"LLM error: {e}"

    # ================================
    # IMPROVE INSIGHTS
    # ================================
    def improve(self):

        signals = self.insight.analyze_market()

        if not signals:
            print("[INSIGHT] No signals available")
            return

        regime_info = self.regime.market_regime()
        regime = regime_info.get("regime", "unknown")

        vol = self.vol_index.calculate()
        vol_level = self.vol_index.level()

        signals_text = "\n".join(f"- {s}" for s in signals)

        prompt = f"""You are Hansen AI, a crypto market analyst.

Interpret the following market signals and provide a concise improved analysis.

Format:
TONE:
STRUCTURE:
RISK:
BIAS:

Market Regime: {regime.upper()}
Volatility Level: {vol_level.upper()} ({vol})

Signals:
{signals_text}
"""

        print("\n[INSIGHT IMPROVER] Generating improved analysis\n")

        result = self.query(prompt)

        print(result)
        print()

        return result

    # ================================
    # RUN
    # ================================
    def run(self):

        print("\n[INSIGHT IMPROVER] Starting\n")

        self.improve()