"""
Hansen Engine - Sentiment & Narrative Module (P5)
Market sentiment scoring, fear/greed calculation, narrative detection.
All derived from on-hand market data — sovereign local, no external API needed.
"""

import time
import logging
from typing import Dict, List, Optional

logger = logging.getLogger("hansen.sentiment_engine")

# Narrative templates — auto-detected from market conditions
NARRATIVES = {
    "btc_dominance_rise": {
        "label": "BTC Dominance Rising",
        "description": "Capital rotating from alts to BTC — risk-off mode",
        "sentiment": "cautious",
    },
    "alt_season": {
        "label": "Alt Season Signal",
        "description": "Altcoins outperforming BTC — risk-on mode",
        "sentiment": "greedy",
    },
    "meme_mania": {
        "label": "Meme Mania",
        "description": "Meme coins pumping hard — retail FOMO in full swing",
        "sentiment": "extreme_greed",
    },
    "defi_revival": {
        "label": "DeFi Revival",
        "description": "DeFi sector outperforming — smart money rotating in",
        "sentiment": "greedy",
    },
    "ai_narrative": {
        "label": "AI Narrative Hot",
        "description": "AI/Compute tokens leading — narrative-driven momentum",
        "sentiment": "greedy",
    },
    "layer2_pump": {
        "label": "L2 Pump",
        "description": "Layer 2 tokens surging — scaling narrative active",
        "sentiment": "greedy",
    },
    "market_fear": {
        "label": "Market Fear",
        "description": "Broad sell-off across sectors — fear dominating",
        "sentiment": "fearful",
    },
    "high_funding_warning": {
        "label": "High Funding Warning",
        "description": "Elevated funding rates — overleveraged longs, potential squeeze",
        "sentiment": "cautious",
    },
    "capitulation": {
        "label": "Capitulation Signal",
        "description": "Heavy liquidations + negative funding — potential bottom forming",
        "sentiment": "extreme_fear",
    },
    "accumulation": {
        "label": "Accumulation Phase",
        "description": "Low volatility + rising volume — smart money loading",
        "sentiment": "neutral",
    },
    "gaming_surge": {
        "label": "Gaming Surge",
        "description": "GameFi tokens outperforming — gaming narrative active",
        "sentiment": "greedy",
    },
    "rwa_momentum": {
        "label": "RWA Momentum",
        "description": "Real World Asset tokens gaining — institutional interest",
        "sentiment": "greedy",
    },
}

# Sentiment levels
SENTIMENT_LEVELS = {
    "extreme_fear": {"score_range": (0, 15), "color": "#ff1744", "label": "Extreme Fear"},
    "fearful": {"score_range": (15, 35), "color": "#ff5555", "label": "Fear"},
    "cautious": {"score_range": (35, 45), "color": "#ff9800", "label": "Cautious"},
    "neutral": {"score_range": (45, 55), "color": "#4a5568", "label": "Neutral"},
    "greedy": {"score_range": (55, 75), "color": "#00e676", "label": "Greed"},
    "extreme_greed": {"score_range": (75, 100), "color": "#00e5ff", "label": "Extreme Greed"},
}


class SentimentEngine:
    """
    Market sentiment & narrative engine.
    - Composite fear/greed score (0-100) from market data
    - Automatic narrative detection from sector performance
    - Sentiment history tracking
    - All derived locally — no external sentiment API
    """

    def __init__(self, market_data=None):
        self.market_data = market_data
        self._cache = {}
        self._cache_ttl = 180  # 3 min cache
        self._last_update = 0
        self._sentiment_history = []
        self._max_history = 288  # 24h at 5min intervals

    def _get_ticker_data(self) -> List[Dict]:
        """Fetch all 24h tickers."""
        if not self.market_data or not hasattr(self.market_data, "get_ticker_24h"):
            return []
        try:
            tickers = self.market_data.get_ticker_24h()
            return [t for t in (tickers or []) if t.get("symbol", "").endswith("USDT")]
        except Exception as e:
            logger.debug(f"Ticker fetch error: {e}")
            return []

    def calculate_fear_greed(self) -> Dict:
        """
        Calculate composite fear/greed score (0-100).
        Components:
        - Price momentum (40%): % of coins in green vs red
        - Volatility (20%): avg price range — high vol = fear
        - Volume (20%): volume trend relative to average
        - Funding sentiment (20%): avg funding rate direction
        """
        tickers = self._get_ticker_data()
        if not tickers:
            return {"score": 50, "level": "neutral", "components": {}}

        changes = []
        volumes = []
        ranges = []

        for t in tickers:
            try:
                change = float(t.get("priceChangePercent", 0))
                volume = float(t.get("quoteVolume", 0))
                high = float(t.get("highPrice", 0))
                low = float(t.get("lowPrice", 0))

                changes.append(change)
                if volume > 0:
                    volumes.append(volume)
                if low > 0:
                    price_range = (high - low) / low * 100
                    ranges.append(price_range)
            except (ValueError, TypeError):
                continue

        if not changes:
            return {"score": 50, "level": "neutral", "components": {}}

        # Component 1: Price Momentum (40%)
        green_count = sum(1 for c in changes if c > 0)
        green_ratio = green_count / len(changes)
        avg_change = sum(changes) / len(changes)
        momentum_score = min(100, max(0, (green_ratio * 60) + (avg_change * 4) + 20))

        # Component 2: Volatility (20%) — inverse: high vol = more fear
        avg_range = sum(ranges) / len(ranges) if ranges else 0
        vol_score = max(0, min(100, 100 - (avg_range * 5)))

        # Component 3: Volume (20%)
        avg_vol = sum(volumes) / len(volumes) if volumes else 0
        high_vol_count = sum(1 for v in volumes if v > avg_vol * 1.5)
        vol_ratio = high_vol_count / len(volumes) if volumes else 0
        volume_score = min(100, max(0, 50 + (vol_ratio * 50) + (avg_change * 2)))

        # Component 4: Market breadth as funding proxy (20%)
        strong_green = sum(1 for c in changes if c > 3)
        strong_red = sum(1 for c in changes if c < -3)
        breadth = (strong_green - strong_red) / max(1, len(changes))
        breadth_score = min(100, max(0, 50 + (breadth * 200)))

        # Composite score
        composite = (
            momentum_score * 0.40 +
            vol_score * 0.20 +
            volume_score * 0.20 +
            breadth_score * 0.20
        )
        composite = round(min(100, max(0, composite)), 1)

        # Determine level
        level = "neutral"
        for lvl, config in SENTIMENT_LEVELS.items():
            low, high = config["score_range"]
            if low <= composite < high:
                level = lvl
                break

        result = {
            "score": composite,
            "level": level,
            "label": SENTIMENT_LEVELS.get(level, {}).get("label", "Neutral"),
            "color": SENTIMENT_LEVELS.get(level, {}).get("color", "#4a5568"),
            "components": {
                "momentum": {"score": round(momentum_score, 1), "weight": 0.40,
                             "detail": f"{green_count}/{len(changes)} green, avg {avg_change:+.2f}%"},
                "volatility": {"score": round(vol_score, 1), "weight": 0.20,
                               "detail": f"Avg range {avg_range:.2f}%"},
                "volume": {"score": round(volume_score, 1), "weight": 0.20,
                           "detail": f"{high_vol_count} above avg volume"},
                "breadth": {"score": round(breadth_score, 1), "weight": 0.20,
                            "detail": f"{strong_green} strong green, {strong_red} strong red"},
            },
            "market_stats": {
                "total_coins": len(changes),
                "green_count": green_count,
                "red_count": len(changes) - green_count,
                "avg_change": round(avg_change, 3),
                "green_ratio": round(green_ratio * 100, 1),
            },
        }

        # Track history
        self._sentiment_history.append({
            "score": composite,
            "level": level,
            "timestamp": int(time.time()),
        })
        if len(self._sentiment_history) > self._max_history:
            self._sentiment_history = self._sentiment_history[-self._max_history:]

        return result

    def detect_narratives(self, sector_data: Optional[Dict] = None) -> List[Dict]:
        """
        Detect active market narratives from sector performance data.

        Args:
            sector_data: Sector ranking data from SectorPerformance module

        Returns:
            List of active narrative dicts
        """
        active = []

        if not sector_data:
            return active

        # Build sector change map
        sector_changes = {}
        if isinstance(sector_data, list):
            for s in sector_data:
                sector_changes[s.get("sector", "")] = s.get("avg_change", 0)
        elif isinstance(sector_data, dict):
            for key, val in sector_data.items():
                if isinstance(val, dict):
                    sector_changes[key] = val.get("avg_change", 0)

        btc_change = sector_changes.get("store_of_value", 0)
        avg_all = sum(sector_changes.values()) / max(1, len(sector_changes))

        # Detect: Alt Season — alts outperforming BTC
        alt_changes = [v for k, v in sector_changes.items() if k != "store_of_value"]
        avg_alt = sum(alt_changes) / max(1, len(alt_changes))
        if avg_alt > btc_change + 1.5 and avg_alt > 1.0:
            n = NARRATIVES["alt_season"].copy()
            n["strength"] = round(avg_alt - btc_change, 2)
            n["active"] = True
            active.append(n)

        # Detect: BTC Dominance Rising
        if btc_change > avg_alt + 2.0 and btc_change > 0:
            n = NARRATIVES["btc_dominance_rise"].copy()
            n["strength"] = round(btc_change - avg_alt, 2)
            n["active"] = True
            active.append(n)

        # Detect: Meme Mania
        meme_change = sector_changes.get("meme", 0)
        if meme_change > 5.0:
            n = NARRATIVES["meme_mania"].copy()
            n["strength"] = round(meme_change, 2)
            n["active"] = True
            active.append(n)

        # Detect: DeFi Revival
        defi_change = sector_changes.get("defi", 0)
        if defi_change > avg_all + 2.0 and defi_change > 2.0:
            n = NARRATIVES["defi_revival"].copy()
            n["strength"] = round(defi_change, 2)
            n["active"] = True
            active.append(n)

        # Detect: AI Narrative
        ai_change = sector_changes.get("ai", 0)
        if ai_change > avg_all + 2.0 and ai_change > 2.0:
            n = NARRATIVES["ai_narrative"].copy()
            n["strength"] = round(ai_change, 2)
            n["active"] = True
            active.append(n)

        # Detect: L2 Pump
        l2_change = sector_changes.get("layer2", 0)
        if l2_change > avg_all + 2.0 and l2_change > 2.0:
            n = NARRATIVES["layer2_pump"].copy()
            n["strength"] = round(l2_change, 2)
            n["active"] = True
            active.append(n)

        # Detect: Gaming Surge
        gaming_change = sector_changes.get("gaming", 0)
        if gaming_change > avg_all + 2.0 and gaming_change > 2.0:
            n = NARRATIVES["gaming_surge"].copy()
            n["strength"] = round(gaming_change, 2)
            n["active"] = True
            active.append(n)

        # Detect: RWA Momentum
        rwa_change = sector_changes.get("rwa", 0)
        if rwa_change > avg_all + 1.5 and rwa_change > 1.5:
            n = NARRATIVES["rwa_momentum"].copy()
            n["strength"] = round(rwa_change, 2)
            n["active"] = True
            active.append(n)

        # Detect: Market Fear — majority of sectors red
        red_sectors = sum(1 for v in sector_changes.values() if v < -1.0)
        if red_sectors >= len(sector_changes) * 0.7 and avg_all < -2.0:
            n = NARRATIVES["market_fear"].copy()
            n["strength"] = round(abs(avg_all), 2)
            n["active"] = True
            active.append(n)

        # Detect: Accumulation — low volatility + neutral change
        if -1.0 <= avg_all <= 1.0 and len(sector_changes) > 5:
            tight_sectors = sum(1 for v in sector_changes.values() if -2.0 <= v <= 2.0)
            if tight_sectors >= len(sector_changes) * 0.7:
                n = NARRATIVES["accumulation"].copy()
                n["strength"] = round(tight_sectors / len(sector_changes) * 100, 1)
                n["active"] = True
                active.append(n)

        # Sort by strength
        active.sort(key=lambda x: x.get("strength", 0), reverse=True)

        return active

    def get_sentiment_history(self) -> List[Dict]:
        """Return sentiment score history."""
        return self._sentiment_history

    def get_sentiment_summary(self, sector_data: Optional[Dict] = None) -> Dict:
        """Complete sentiment summary for dashboard/API."""
        cache_key = "sentiment_summary"
        now = time.time()

        if (cache_key in self._cache and
                now - self._last_update < self._cache_ttl):
            return self._cache[cache_key]

        fear_greed = self.calculate_fear_greed()
        narratives = self.detect_narratives(sector_data)

        summary = {
            "fear_greed": fear_greed,
            "narratives": narratives,
            "active_narrative_count": len(narratives),
            "history": self._sentiment_history[-48:],  # last ~4h
            "sentiment_levels": {k: v["label"] for k, v in SENTIMENT_LEVELS.items()},
            "timestamp": int(time.time()),
        }

        self._cache[cache_key] = summary
        self._last_update = now

        return summary


if __name__ == "__main__":
    se = SentimentEngine()
    print(f"Narratives available: {len(NARRATIVES)}")
    print(f"Sentiment levels: {list(SENTIMENT_LEVELS.keys())}")
    for k, v in NARRATIVES.items():
        print(f"  {k}: {v['label']}")
