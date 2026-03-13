"""
Hansen Engine - AI Reports Module (P7)
Daily/weekly market report generator using local llama.cpp LLM server.
Sovereign local — uses localhost:8080 llama server, no external API.
"""

import json
import os
import time
import logging
import requests
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger("hansen.ai_reports")

# Report storage
REPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "reports")
LLM_URL = "http://localhost:8080/completion"
LLM_TIMEOUT = 60

# Report types
REPORT_DAILY = "daily"
REPORT_WEEKLY = "weekly"
REPORT_FLASH = "flash"


class AIReports:
    """
    AI-powered market report generator.
    - Collects data from all modules (sector, sentiment, alerts, onchain, screener)
    - Sends structured prompt to local llama.cpp
    - Generates daily/weekly/flash reports
    - Stores report history as JSON
    """

    def __init__(self, market_data=None, sector_perf=None, sentiment=None,
                 alert_engine=None, onchain=None, screener=None, market_brain=None):
        self.market_data = market_data
        self.sector_perf = sector_perf
        self.sentiment = sentiment
        self.alert_engine = alert_engine
        self.onchain = onchain
        self.screener = screener
        self.market_brain = market_brain
        self._cache = {}
        self._cache_ttl = 600  # 10 min cache
        self._last_update = 0

        os.makedirs(REPORT_DIR, exist_ok=True)

    def _call_llm(self, prompt: str, max_tokens: int = 1024) -> Optional[str]:
        """Call local llama.cpp server for text generation."""
        try:
            payload = {
                "prompt": prompt,
                "n_predict": max_tokens,
                "temperature": 0.7,
                "top_p": 0.9,
                "stop": ["</report>", "\n\n\n"],
            }
            resp = requests.post(LLM_URL, json=payload, timeout=LLM_TIMEOUT)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("content", "").strip()
            else:
                logger.warning(f"LLM server returned {resp.status_code}")
                return None
        except requests.exceptions.ConnectionError:
            logger.warning("LLM server not reachable at localhost:8080")
            return None
        except Exception as e:
            logger.debug(f"LLM call error: {e}")
            return None

    def _collect_market_snapshot(self) -> Dict:
        """Collect current market data from all modules."""
        if self.market_brain:
            return self.market_brain.collect_full_context()
        snapshot = {
            "timestamp": int(time.time()),
            "datetime": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }

        # Sector performance
        if self.sector_perf:
            try:
                ranking = self.sector_perf.get_sector_ranking("24h")
                snapshot["top_sectors"] = [
                    {"name": s["name"], "change": s["avg_change"], "trend": s["trend"]}
                    for s in ranking[:5]
                ]
                snapshot["bottom_sectors"] = [
                    {"name": s["name"], "change": s["avg_change"], "trend": s["trend"]}
                    for s in ranking[-3:]
                ]
            except Exception as e:
                logger.debug(f"Sector data error: {e}")

        # Sentiment
        if self.sentiment:
            try:
                fg = self.sentiment.calculate_fear_greed()
                snapshot["fear_greed_score"] = fg.get("score", 50)
                snapshot["fear_greed_level"] = fg.get("label", "Neutral")
                snapshot["green_ratio"] = fg.get("market_stats", {}).get("green_ratio", 50)
            except Exception as e:
                logger.debug(f"Sentiment data error: {e}")

        # Alerts
        if self.alert_engine:
            try:
                stats = self.alert_engine.get_alert_stats()
                snapshot["alerts_24h"] = stats.get("last_24h", 0)
                snapshot["critical_alerts"] = stats.get("critical_24h", 0)
                recent = self.alert_engine.get_recent_alerts(5)
                snapshot["top_alerts"] = [
                    {"message": a["message"], "severity": a["severity"]}
                    for a in recent
                ]
            except Exception as e:
                logger.debug(f"Alert data error: {e}")

        # Onchain
        if self.onchain:
            try:
                whale = self.onchain.detect_whale_activity()
                snapshot["whale_signals"] = whale.get("total_whale_signals", 0)
                flow = self.onchain.analyze_exchange_flow()
                snapshot["exchange_flow"] = flow.get("net_sentiment", "neutral")
                snapshot["inflow_count"] = flow.get("inflow_count", 0)
                snapshot["outflow_count"] = flow.get("outflow_count", 0)
            except Exception as e:
                logger.debug(f"Onchain data error: {e}")

        # Screener highlights
        if self.screener:
            try:
                momentum = self.screener.screen(preset="momentum_kings", limit=3)
                dips = self.screener.screen(preset="dip_buys", limit=3)
                snapshot["momentum_kings"] = [
                    {"symbol": c["label"], "change": c["change_24h"]}
                    for c in momentum.get("results", [])
                ]
                snapshot["dip_buys"] = [
                    {"symbol": c["label"], "change": c["change_24h"]}
                    for c in dips.get("results", [])
                ]
            except Exception as e:
                logger.debug(f"Screener data error: {e}")

        return snapshot

    def _build_prompt(self, snapshot: Dict, report_type: str) -> str:
        """Build LLM prompt from market snapshot."""
        data_str = json.dumps(snapshot, indent=2, default=str)

        if report_type == REPORT_FLASH:
            prompt = f"""You are Hansen AI, a crypto market analyst. Write a brief flash report (3-5 sentences) based on this data:

{data_str}

Focus on the most important signal right now. Be direct and actionable. Use trading terminology.

Flash Report:"""

        elif report_type == REPORT_DAILY:
            prompt = f"""You are Hansen AI, a professional crypto market analyst. Write a daily market report based on this data:

{data_str}

Structure:
1. MARKET OVERVIEW (2-3 sentences on overall market condition)
2. SECTOR HIGHLIGHTS (top performing and worst sectors)
3. KEY SIGNALS (sentiment, whale activity, exchange flow)
4. WATCHLIST (momentum kings and dip buy opportunities)
5. RISK ASSESSMENT (alerts, volatility, funding concerns)
6. DERIVATIVES (funding rate sentiment, OI spikes, liquidation cascade risk)

Keep it concise but insightful. Use trading terminology. No disclaimers needed.

Daily Report:"""

        else:  # weekly
            prompt = f"""You are Hansen AI, a professional crypto market analyst. Write a weekly market summary based on this data:

{data_str}

Structure:
1. WEEKLY OVERVIEW (market trend and sentiment shift)
2. SECTOR ROTATION (which sectors gained/lost momentum)
3. NOTABLE EVENTS (major alerts, whale movements, liquidations)
4. OPPORTUNITIES (breakout candidates, undervalued sectors)
5. OUTLOOK (what to watch next week)

Be analytical and forward-looking. Use trading terminology.

Weekly Report:"""

        return prompt

    def generate_report(self, report_type: str = REPORT_DAILY, use_llm: bool = True) -> Dict:
        """
        Generate a market report.

        Args:
            report_type: "daily", "weekly", or "flash"
            use_llm: If True, use LLM to generate narrative. If False, return raw data.

        Returns:
            {"report_type": str, "content": str, "snapshot": dict, "generated_by": str, ...}
        """
        snapshot = self._collect_market_snapshot()

        report = {
            "report_type": report_type,
            "snapshot": snapshot,
            "timestamp": int(time.time()),
            "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        if use_llm:
            prompt = self._build_prompt(snapshot, report_type)
            llm_response = self._call_llm(prompt, max_tokens=1024 if report_type != REPORT_FLASH else 256)

            if llm_response:
                report["content"] = llm_response
                report["generated_by"] = "llama_local"
            else:
                # Fallback: generate structured report without LLM
                report["content"] = self._generate_fallback_report(snapshot, report_type)
                report["generated_by"] = "fallback_template"
        else:
            report["content"] = self._generate_fallback_report(snapshot, report_type)
            report["generated_by"] = "template"

        # Save report
        self._save_report(report)

        return report

    def _generate_fallback_report(self, snapshot: Dict, report_type: str) -> str:
        """Generate a template-based report when LLM is unavailable."""
        lines = []
        dt = snapshot.get("datetime", "N/A")

        if report_type == REPORT_FLASH:
            fg = snapshot.get("fear_greed_score", 50)
            level = snapshot.get("fear_greed_level", "Neutral")
            green = snapshot.get("green_ratio", 50)
            flow = snapshot.get("exchange_flow", "neutral")
            lines.append(f"[FLASH {dt}] Market sentiment: {level} ({fg}/100). "
                        f"Green ratio: {green}%. Exchange flow: {flow}. "
                        f"Whale signals: {snapshot.get('whale_signals', 0)}. "
                        f"Critical alerts: {snapshot.get('critical_alerts', 0)}.")

        elif report_type == REPORT_DAILY:
            lines.append(f"═══ HANSEN AI — DAILY REPORT ({dt}) ═══\n")

            # Overview
            fg = snapshot.get("fear_greed_score", 50)
            level = snapshot.get("fear_greed_level", "Neutral")
            green = snapshot.get("green_ratio", 50)
            lines.append(f"MARKET OVERVIEW")
            lines.append(f"Fear & Greed: {fg}/100 ({level})")
            lines.append(f"Market breadth: {green}% green\n")

            # Sectors
            top = snapshot.get("top_sectors", [])
            bottom = snapshot.get("bottom_sectors", [])
            if top:
                lines.append("TOP SECTORS")
                for s in top:
                    lines.append(f"  {s['name']}: {s['change']:+.2f}% [{s['trend']}]")
            if bottom:
                lines.append("\nWEAKEST SECTORS")
                for s in bottom:
                    lines.append(f"  {s['name']}: {s['change']:+.2f}% [{s['trend']}]")

            # Signals
            lines.append(f"\nKEY SIGNALS")
            lines.append(f"  Exchange flow: {snapshot.get('exchange_flow', 'neutral')}")
            lines.append(f"  Whale signals: {snapshot.get('whale_signals', 0)}")
            lines.append(f"  Inflow/Outflow: {snapshot.get('inflow_count', 0)}/{snapshot.get('outflow_count', 0)}")
            lines.append(f"  Alerts 24h: {snapshot.get('alerts_24h', 0)} (critical: {snapshot.get('critical_alerts', 0)})")

            # Watchlist
            kings = snapshot.get("momentum_kings", [])
            dips = snapshot.get("dip_buys", [])
            if kings:
                lines.append("\nMOMENTUM KINGS")
                for c in kings:
                    lines.append(f"  {c['symbol']}: {c['change']:+.2f}%")
            if dips:
                lines.append("\nDIP BUY CANDIDATES")
                for c in dips:
                    lines.append(f"  {c['symbol']}: {c['change']:+.2f}%")

        else:  # weekly
            lines.append(f"═══ HANSEN AI — WEEKLY REPORT ({dt}) ═══\n")
            lines.append("Weekly data snapshot compiled. LLM analysis unavailable.")
            lines.append(f"Fear & Greed: {snapshot.get('fear_greed_score', 50)}/100")
            lines.append(f"Market breadth: {snapshot.get('green_ratio', 50)}% green")
            lines.append(f"Total alerts: {snapshot.get('alerts_24h', 0)}")

        return "\n".join(lines)

    def _save_report(self, report: Dict):
        """Save report to JSON file."""
        try:
            filename = f"{report['report_type']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = os.path.join(REPORT_DIR, filename)
            with open(filepath, "w") as f:
                json.dump(report, f, indent=2, default=str)
        except Exception as e:
            logger.debug(f"Report save error: {e}")

    def get_recent_reports(self, limit: int = 10, report_type: Optional[str] = None) -> List[Dict]:
        """Get recent saved reports."""
        reports = []
        try:
            if not os.path.exists(REPORT_DIR):
                return []

            files = sorted(os.listdir(REPORT_DIR), reverse=True)
            for fname in files:
                if not fname.endswith(".json"):
                    continue
                if report_type and not fname.startswith(report_type):
                    continue

                filepath = os.path.join(REPORT_DIR, fname)
                try:
                    with open(filepath, "r") as f:
                        report = json.load(f)
                        reports.append({
                            "filename": fname,
                            "report_type": report.get("report_type", "unknown"),
                            "content": report.get("content", ""),
                            "generated_by": report.get("generated_by", "unknown"),
                            "datetime": report.get("datetime", ""),
                            "timestamp": report.get("timestamp", 0),
                        })
                except Exception:
                    continue

                if len(reports) >= limit:
                    break

        except Exception as e:
            logger.debug(f"Report listing error: {e}")

        return reports

    def get_reports_summary(self) -> Dict:
        """Complete reports summary for dashboard/API."""
        cache_key = "reports_summary"
        now = time.time()

        if (cache_key in self._cache and
                now - self._last_update < self._cache_ttl):
            return self._cache[cache_key]

        recent = self.get_recent_reports(5)

        # Try generate a flash report
        flash = self.generate_report(REPORT_FLASH, use_llm=True)

        summary = {
            "flash_report": flash,
            "recent_reports": recent,
            "total_reports": len(os.listdir(REPORT_DIR)) if os.path.exists(REPORT_DIR) else 0,
            "llm_status": "online" if self._check_llm_status() else "offline",
            "timestamp": int(time.time()),
        }

        self._cache[cache_key] = summary
        self._last_update = now

        return summary

    def _check_llm_status(self) -> bool:
        """Check if local LLM server is reachable."""
        try:
            resp = requests.get("http://localhost:8080/health", timeout=3)
            return resp.status_code == 200
        except Exception:
            return False


if __name__ == "__main__":
    ar = AIReports()
    print(f"Report dir: {REPORT_DIR}")
    print(f"LLM status: {'online' if ar._check_llm_status() else 'offline'}")
