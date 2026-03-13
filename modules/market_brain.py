"""
Hansen Engine - Market Brain (Central Intelligence Hub)
Collects ALL market data into one unified context for AI reasoning.
Feeds into AI Reports, LLM prompts, and engine decision-making.
Sovereign local — aggregates from all existing modules.
"""

import time
import json
import logging
from typing import Dict, List, Optional

logger = logging.getLogger("hansen.market_brain")


class MarketBrain:
    """
    Central intelligence hub — merges ALL module data into a single
    reasoning context that the AI/LLM can consume.

    Data sources:
    - MarketData (prices, tickers)
    - SectorPerformance (sector ranking, rotation)
    - CorrelationMatrix (correlation, beta)
    - AlertEngine (alerts, critical events)
    - MarketHeatmap (visual sentiment)
    - SmartScreener (filtered opportunities)
    - SentimentEngine (fear/greed, narratives)
    - OnchainIntel (whale, flow, stablecoin)
    - Derivatives (funding rate, OI, liquidations)
    - MarketRegime (regime detection)
    - MomentumEngine (momentum scores)
    - VolatilityIndex (vol metrics)
    """

    def __init__(self, **modules):
        """
        Accept any module as keyword argument.
        Example: MarketBrain(market_data=md, sector_perf=sp, ...)
        """
        self.modules = modules
        self._cache = {}
        self._cache_ttl = 120  # 2 min
        self._last_update = 0

    def _safe_call(self, module_name: str, method_name: str, *args, **kwargs):
        """Safely call a module method, return None on failure."""
        module = self.modules.get(module_name)
        if not module:
            return None
        method = getattr(module, method_name, None)
        if not method:
            return None
        try:
            return method(*args, **kwargs)
        except Exception as e:
            logger.debug(f"MarketBrain: {module_name}.{method_name} error: {e}")
            return None

    def collect_full_context(self) -> Dict:
        """
        Collect ALL available data into a single reasoning context.
        This is what gets fed to the LLM for analysis.
        """
        cache_key = "full_context"
        now = time.time()

        if (cache_key in self._cache and
                now - self._last_update < self._cache_ttl):
            return self._cache[cache_key]

        context = {
            "timestamp": int(time.time()),
            "data_sources": [],
        }

        # 1. Sector Performance
        sector_ranking = self._safe_call("sector_perf", "get_sector_ranking", "24h")
        if sector_ranking:
            context["sectors"] = {
                "ranking": [
                    {"name": s.get("name"), "change": s.get("avg_change"),
                     "trend": s.get("trend"), "strength": s.get("strength"),
                     "coins_up": s.get("coins_up"), "coins_down": s.get("coins_down")}
                    for s in sector_ranking[:10]
                ],
                "top_3": [s.get("name") for s in sector_ranking[:3]],
                "bottom_3": [s.get("name") for s in sector_ranking[-3:]],
            }
            context["data_sources"].append("sector_performance")

        # Sector rotation
        rotation = self._safe_call("sector_perf", "detect_sector_rotation")
        if rotation:
            context["sector_rotation"] = {
                "rotating_in": [r.get("name") for r in rotation.get("rotating_in", [])],
                "rotating_out": [r.get("name") for r in rotation.get("rotating_out", [])],
            }

        # 2. Sentiment
        fear_greed = self._safe_call("sentiment", "calculate_fear_greed")
        if fear_greed:
            context["sentiment"] = {
                "score": fear_greed.get("score"),
                "level": fear_greed.get("label"),
                "components": {
                    k: {"score": v.get("score"), "detail": v.get("detail")}
                    for k, v in fear_greed.get("components", {}).items()
                },
                "market_breadth": {
                    "total": fear_greed.get("market_stats", {}).get("total_coins"),
                    "green": fear_greed.get("market_stats", {}).get("green_count"),
                    "red": fear_greed.get("market_stats", {}).get("red_count"),
                    "green_ratio": fear_greed.get("market_stats", {}).get("green_ratio"),
                    "avg_change": fear_greed.get("market_stats", {}).get("avg_change"),
                },
            }
            context["data_sources"].append("sentiment")

        # Narratives
        if sector_ranking:
            narratives = self._safe_call("sentiment", "detect_narratives", sector_ranking)
            if narratives:
                context["active_narratives"] = [
                    {"label": n.get("label"), "description": n.get("description"),
                     "strength": n.get("strength"), "sentiment": n.get("sentiment")}
                    for n in narratives
                ]

        # 3. Alerts
        alert_stats = self._safe_call("alert_engine", "get_alert_stats")
        recent_alerts = self._safe_call("alert_engine", "get_recent_alerts", 10)
        if alert_stats:
            context["alerts"] = {
                "stats": alert_stats,
                "recent": [
                    {"type": a.get("type"), "severity": a.get("severity"),
                     "symbol": a.get("symbol"), "message": a.get("message")}
                    for a in (recent_alerts or [])
                ],
            }
            context["data_sources"].append("alerts")

        # 4. Onchain
        whale = self._safe_call("onchain", "detect_whale_activity")
        if whale:
            context["whale_activity"] = {
                "total_signals": whale.get("total_whale_signals"),
                "total_volume": whale.get("whale_volume_usd"),
                "top_whales": [
                    {"symbol": w.get("label"), "direction": w.get("direction"),
                     "score": w.get("whale_score"), "volume": w.get("volume_usd")}
                    for w in whale.get("whale_coins", [])[:5]
                ],
            }
            context["data_sources"].append("whale_activity")

        flow = self._safe_call("onchain", "analyze_exchange_flow")
        if flow:
            context["exchange_flow"] = {
                "net_sentiment": flow.get("net_sentiment"),
                "inflow": flow.get("inflow_count"),
                "outflow": flow.get("outflow_count"),
                "top_flows": [
                    {"symbol": f.get("label"), "type": f.get("flow_type"),
                     "buy_pressure": f.get("buy_pressure")}
                    for f in flow.get("flows", [])[:5]
                ],
            }
            context["data_sources"].append("exchange_flow")

        stable = self._safe_call("onchain", "analyze_stablecoin_flow")
        if stable:
            context["stablecoin"] = {
                "deployment_signal": stable.get("deployment_signal"),
                "total_volume": stable.get("total_volume"),
            }

        # 5. Screener highlights
        momentum = self._safe_call("screener", "screen", preset="momentum_kings", limit=5)
        dips = self._safe_call("screener", "screen", preset="dip_buys", limit=5)
        breakout = self._safe_call("screener", "screen", preset="breakout_candidates", limit=5)

        context["opportunities"] = {}
        if momentum and momentum.get("results"):
            context["opportunities"]["momentum_kings"] = [
                {"symbol": c.get("label"), "change": c.get("change_24h"),
                 "volume": c.get("volume"), "vol_ratio": c.get("volume_ratio")}
                for c in momentum["results"]
            ]
        if dips and dips.get("results"):
            context["opportunities"]["dip_buys"] = [
                {"symbol": c.get("label"), "change": c.get("change_24h"),
                 "volume": c.get("volume")}
                for c in dips["results"]
            ]
        if breakout and breakout.get("results"):
            context["opportunities"]["breakout_candidates"] = [
                {"symbol": c.get("label"), "change": c.get("change_24h"),
                 "vol_ratio": c.get("volume_ratio"), "range": c.get("price_range")}
                for c in breakout["results"]
            ]
        if context["opportunities"]:
            context["data_sources"].append("screener")

        # 6. Derivatives (from collector)
        derivatives_fn = self.modules.get("derivatives_fn")
        if derivatives_fn:
            try:
                deriv_data = derivatives_fn()
                if deriv_data:
                    context["derivatives"] = {}

                    # Funding
                    funding_summary = deriv_data.get("funding_summary", {})
                    funding_list = deriv_data.get("funding", [])
                    if funding_summary:
                        context["derivatives"]["funding"] = {
                            "avg_rate": funding_summary.get("avg_rate"),
                            "sentiment": funding_summary.get("sentiment"),
                            "long_count": funding_summary.get("long_count"),
                            "short_count": funding_summary.get("short_count"),
                            "extreme_positive": [
                                {"symbol": f.get("symbol"), "rate": f.get("rate")}
                                for f in funding_list[:5] if float(f.get("rate", 0)) > 0.05
                            ] if funding_list else [],
                            "extreme_negative": [
                                {"symbol": f.get("symbol"), "rate": f.get("rate")}
                                for f in funding_list if float(f.get("rate", 0)) < -0.03
                            ][:5] if funding_list else [],
                        }

                    # Open Interest
                    oi_summary = deriv_data.get("oi_summary", {})
                    if oi_summary:
                        context["derivatives"]["open_interest"] = {
                            "spikes": oi_summary.get("spikes", 0),
                            "dumps": oi_summary.get("dumps", 0),
                        }

                    # Liquidations
                    liq_summary = deriv_data.get("liq_summary", {})
                    if liq_summary:
                        context["derivatives"]["liquidations"] = {
                            "total_usd": liq_summary.get("total_usd"),
                            "dominance": liq_summary.get("dominance"),
                            "long_pct": liq_summary.get("long_pct"),
                            "short_pct": liq_summary.get("short_pct"),
                        }

                    # Cascade Alert
                    cascade = deriv_data.get("cascade_alert", {})
                    if cascade:
                        context["derivatives"]["cascade_alert"] = cascade

                    context["data_sources"].append("derivatives")
            except Exception as e:
                logger.debug(f"Derivatives data error: {e}")

        # 7. Market Regime
        regime = self._safe_call("regime_detector", "detect_regime")
        if regime:
            context["market_regime"] = regime
            context["data_sources"].append("regime")

        # 8. Momentum
        momentum_data = self._safe_call("momentum_engine", "get_momentum_summary")
        if momentum_data:
            context["momentum"] = momentum_data
            context["data_sources"].append("momentum")

        # 9. Volatility
        vol_data = self._safe_call("volatility_index", "get_volatility_summary")
        if vol_data:
            context["volatility"] = vol_data
            context["data_sources"].append("volatility")

        # 10. Correlation highlights
        corr_summary = self._safe_call("correlation", "get_strongest_correlations", "7d", 5)
        beta_data = self._safe_call("correlation", "get_beta_vs_btc", "7d")
        if corr_summary:
            context["correlation"] = {
                "strongest_pairs": [
                    {"pair": p.get("pair"), "correlation": p.get("correlation")}
                    for p in corr_summary
                ],
            }
            if beta_data:
                context["correlation"]["high_beta"] = [
                    {"symbol": b.get("label"), "beta": b.get("beta")}
                    for b in beta_data[:5] if b.get("beta", 0) > 1.2
                ]
                context["correlation"]["low_beta"] = [
                    {"symbol": b.get("label"), "beta": b.get("beta")}
                    for b in beta_data if b.get("beta", 0) < 0.5
                ][:3]
            context["data_sources"].append("correlation")

        context["total_data_sources"] = len(context["data_sources"])

        self._cache[cache_key] = context
        self._last_update = now

        return context

    def get_reasoning_prompt(self, question: Optional[str] = None) -> str:
        """
        Build a full reasoning prompt for the LLM with ALL context.
        Optionally include a specific question to answer.
        """
        context = self.collect_full_context()

        # Compact the context for LLM consumption
        compact = json.dumps(context, indent=1, default=str)

        prompt = f"""You are Hansen AI, an advanced crypto market intelligence system.
You have access to real-time data from {context.get('total_data_sources', 0)} data sources.

=== CURRENT MARKET DATA ===
{compact}

=== INSTRUCTIONS ===
Analyze the data above and provide actionable intelligence.
Focus on:
1. What is the current market condition? (bullish/bearish/neutral)
2. What are the strongest signals right now?
3. What opportunities exist? (momentum, dips, breakouts)
4. What risks should be watched? (alerts, liquidations, funding)
5. What narrative is driving the market?

Be direct, analytical, and use trading terminology.
"""

        if question:
            prompt += f"\n=== SPECIFIC QUESTION ===\n{question}\n"

        prompt += "\n=== ANALYSIS ===\n"

        return prompt

    def get_brain_summary(self) -> Dict:
        """Summary for dashboard API."""
        context = self.collect_full_context()
        return {
            "total_data_sources": context.get("total_data_sources", 0),
            "data_sources": context.get("data_sources", []),
            "sentiment_score": context.get("sentiment", {}).get("score"),
            "sentiment_level": context.get("sentiment", {}).get("level"),
            "active_narratives": len(context.get("active_narratives", [])),
            "whale_signals": context.get("whale_activity", {}).get("total_signals", 0),
            "alert_count": context.get("alerts", {}).get("stats", {}).get("last_24h", 0),
            "critical_alerts": context.get("alerts", {}).get("stats", {}).get("critical_24h", 0),
            "exchange_flow": context.get("exchange_flow", {}).get("net_sentiment"),
            "top_sectors": context.get("sectors", {}).get("top_3", []),
            "timestamp": context.get("timestamp"),
        }


if __name__ == "__main__":
    mb = MarketBrain()
    ctx = mb.collect_full_context()
    print(f"Data sources: {ctx.get('total_data_sources', 0)}")
    print(f"Sources: {ctx.get('data_sources', [])}")
