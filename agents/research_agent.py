import time
import requests


# ================================
# RESEARCH AGENT
# ================================

class ResearchAgent:

    def __init__(self):

        self.llm_url = "http://127.0.0.1:8080/completion"

    # ================================
    # QUERY LLM
    # ================================
    def query(self, prompt, max_tokens=300):

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
    # RESEARCH TASK
    # ================================
    def research(self, topic, context=""):

        prompt = f"""You are Hansen AI, a crypto market research assistant.

Research the following topic and provide a structured analysis.

Format:
SUMMARY:
KEY POINTS:
RISK:
CONCLUSION:

Topic: {topic}

Market Context:
{context}
"""

        print(f"\n[RESEARCH AGENT] Researching: {topic}\n")

        result = self.query(prompt)

        print(result)
        print()

        return result

    # ================================
    # AUTONOMOUS RESEARCH LOOP
    # ================================
    def run(self, topics, context=""):

        print("\n[RESEARCH AGENT] Starting autonomous research loop\n")

        results = {}

        for topic in topics:

            print(f"[RESEARCH AGENT] Topic: {topic}")

            result = self.research(topic, context)

            results[topic] = result

            time.sleep(2)

        print("[RESEARCH AGENT] Research loop complete\n")

        return results