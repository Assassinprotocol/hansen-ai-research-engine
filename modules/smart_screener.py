"""
Hansen Engine - Smart Screener Module (P4 Screeners)
Multi-filter coin screener: momentum, volume, funding, volatility.
Sovereign local - no external dependencies.
"""

import time
import logging
from typing import Dict, List, Optional

logger = logging.getLogger("hansen.smart_screener")

# Screener presets
PRESETS = {
    "momentum_kings": {
        "label": "Momentum Kings",
        "description": "Coins with strongest upward momentum",
        "filters": {"min_change_24h": 3.0, "min_volume": 50000000},
        "sort_by": "change_24h",
        "sort_desc": True,
    },
    "dip_buys": {
        "label": "Dip Buys",
        "description": "Oversold coins with high volume (potential reversal)",
        "filters": {"max_change_24h": -5.0, "min_volume": 30000000},
        "sort_by": "change_24h",
        "sort_desc": False,
    },
    "volume_surge": {
        "label": "Volume Surge",
        "description": "Coins with unusual volume activity",
        "filters": {"min_volume_ratio": 2.0},
        "sort_by": "volume_ratio",
        "sort_desc": True,
    },
    "low_funding": {
        "label": "Low Funding",
        "description": "Negative funding = shorts paying longs",
        "filters": {"max_funding": -0.01},
        "sort_by": "funding_rate",
        "sort_desc": False,
    },
    "high_funding": {
        "label": "High Funding",
        "description": "Extreme positive funding = potential squeeze",
        "filters": {"min_funding": 0.05},
        "sort_by": "funding_rate",
        "sort_desc": True,
    },
    "breakout_candidates": {
        "label": "Breakout Candidates",
        "description": "Low volatility + rising volume = potential breakout",
        "filters": {"max_change_24h": 2.0, "min_change_24h": -2.0, "min_volume_ratio": 1.5},
        "sort_by": "volume_ratio",
        "sort_desc": True,
    },
}


class SmartScreener:
    """
    Multi-filter coin screener.
    - Preset filters (momentum, dip, volume, funding, breakout)
    - Custom filter support
    - Real-time data from Binance
    - Sorting and ranking
    """

    def __init__(self, market_data=None):
        self.market_data = market_data
        self._cache = {}
        self._cache_ttl = 120
        self._last_update = 0
        self._ticker_cache = None
        self._ticker_cache_time = 0

    def _get_all_tickers(self) -> List[Dict]:
        """Fetch and cache all 24h tickers."""
        now = time.time()
        if self._ticker_cache and now - self._ticker_cache_time < 60:
            return self._ticker_cache

        if not self.market_data or not hasattr(self.market_data, "get_ticker_24h"):
            return []

        try:
            tickers = self.market_data.get_ticker_24h()
            if tickers:
                self._ticker_cache = tickers
                self._ticker_cache_time = now
                return tickers
        except Exception as e:
            logger.debug(f"Ticker fetch error: {e}")

        return self._ticker_cache or []

    def _enrich_ticker(self, ticker: Dict, avg_volume: float = 0) -> Optional[Dict]:
        """Enrich raw ticker data with calculated fields."""
        try:
            symbol = ticker.get("symbol", "")
            if not symbol.endswith("USDT"):
                return None

            change_24h = float(ticker.get("priceChangePercent", 0))
            price = float(ticker.get("lastPrice", 0))
            volume = float(ticker.get("quoteVolume", 0))
            high = float(ticker.get("highPrice", 0))
            low = float(ticker.get("lowPrice", 0))

            if price <= 0:
                return None

            # Calculate additional metrics
            volume_ratio = (volume / avg_volume) if avg_volume > 0 else 0
            price_range = ((high - low) / low * 100) if low > 0 else 0
            distance_from_high = ((high - price) / high * 100) if high > 0 else 0

            return {
                "symbol": symbol,
                "label": symbol.replace("USDT", ""),
                "price": price,
                "change_24h": round(change_24h, 3),
                "volume": round(volume, 2),
                "volume_ratio": round(volume_ratio, 2),
                "high_24h": high,
                "low_24h": low,
                "price_range": round(price_range, 2),
                "distance_from_high": round(distance_from_high, 2),
                "funding_rate": 0,  # will be enriched if data available
            }
        except (ValueError, TypeError):
            return None

    def _apply_filters(self, coin: Dict, filters: Dict) -> bool:
        """Check if coin passes all filters."""
        for key, value in filters.items():
            if key == "min_change_24h" and coin.get("change_24h", 0) < value:
                return False
            if key == "max_change_24h" and coin.get("change_24h", 0) > value:
                return False
            if key == "min_volume" and coin.get("volume", 0) < value:
                return False
            if key == "min_volume_ratio" and coin.get("volume_ratio", 0) < value:
                return False
            if key == "min_funding" and coin.get("funding_rate", 0) < value:
                return False
            if key == "max_funding" and coin.get("funding_rate", 0) > value:
                return False
            if key == "min_price_range" and coin.get("price_range", 0) < value:
                return False
            if key == "max_price_range" and coin.get("price_range", 0) > value:
                return False
        return True

    def screen(self, preset: Optional[str] = None, custom_filters: Optional[Dict] = None,
               sort_by: str = "change_24h", sort_desc: bool = True,
               limit: int = 30, funding_data: Optional[List] = None) -> Dict:
        """
        Run screener with preset or custom filters.

        Args:
            preset: Preset name from PRESETS dict
            custom_filters: Custom filter dict
            sort_by: Field to sort by
            sort_desc: Sort descending
            limit: Max results
            funding_data: Optional funding rate data to enrich results

        Returns:
            {"results": [...], "total_matched": int, "preset": str, ...}
        """
        tickers = self._get_all_tickers()
        if not tickers:
            return {"results": [], "total_matched": 0, "timestamp": int(time.time())}

        # Calculate average volume
        volumes = []
        for t in tickers:
            try:
                v = float(t.get("quoteVolume", 0))
                if t.get("symbol", "").endswith("USDT"):
                    volumes.append(v)
            except (ValueError, TypeError):
                pass
        avg_volume = sum(volumes) / len(volumes) if volumes else 0

        # Enrich all tickers
        enriched = []
        for t in tickers:
            coin = self._enrich_ticker(t, avg_volume)
            if coin:
                enriched.append(coin)

        # Enrich with funding data if available
        if funding_data:
            funding_map = {}
            for f in funding_data:
                sym = f.get("symbol", "")
                try:
                    rate = float(f.get("funding_rate", f.get("lastFundingRate", 0)))
                    funding_map[sym] = rate * 100
                except (ValueError, TypeError):
                    pass
            for coin in enriched:
                coin["funding_rate"] = funding_map.get(coin["symbol"], 0)

        # Get filters
        filters = {}
        used_preset = None
        if preset and preset in PRESETS:
            p = PRESETS[preset]
            filters = p["filters"]
            sort_by = p.get("sort_by", sort_by)
            sort_desc = p.get("sort_desc", sort_desc)
            used_preset = preset
        elif custom_filters:
            filters = custom_filters

        # Apply filters
        matched = [c for c in enriched if self._apply_filters(c, filters)]

        # Sort
        matched.sort(key=lambda x: x.get(sort_by, 0), reverse=sort_desc)

        return {
            "results": matched[:limit],
            "total_matched": len(matched),
            "total_scanned": len(enriched),
            "preset": used_preset,
            "filters_applied": filters,
            "sort_by": sort_by,
            "sort_desc": sort_desc,
            "timestamp": int(time.time()),
        }

    def get_all_presets(self) -> Dict:
        """Return all available preset configs."""
        return {k: {"label": v["label"], "description": v["description"]}
                for k, v in PRESETS.items()}

    def get_screener_summary(self, funding_data: Optional[List] = None) -> Dict:
        """
        Run all presets and return summary for dashboard.
        """
        cache_key = "screener_summary"
        now = time.time()

        if (cache_key in self._cache and
                now - self._last_update < self._cache_ttl):
            return self._cache[cache_key]

        summary = {
            "presets": {},
            "available_presets": self.get_all_presets(),
            "timestamp": int(time.time()),
        }

        for preset_key in PRESETS:
            result = self.screen(preset=preset_key, limit=10, funding_data=funding_data)
            summary["presets"][preset_key] = {
                "label": PRESETS[preset_key]["label"],
                "description": PRESETS[preset_key]["description"],
                "total_matched": result["total_matched"],
                "top_results": result["results"][:5],
            }

        self._cache[cache_key] = summary
        self._last_update = now

        return summary


if __name__ == "__main__":
    ss = SmartScreener()
    print(f"Available presets: {list(PRESETS.keys())}")
    for k, v in PRESETS.items():
        print(f"  {k}: {v['label']} — {v['description']}")
