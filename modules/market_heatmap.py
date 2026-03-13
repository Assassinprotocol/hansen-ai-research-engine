"""
Hansen Engine - Market Heatmap Module (P3 Heatmap)
Heatmap data generator grouped by sector with color intensity.
Sovereign local - no external dependencies.
"""

import time
import logging
from typing import Dict, List, Optional
from collections import defaultdict

logger = logging.getLogger("hansen.market_heatmap")

# Import sector map from sector_performance
try:
    from modules.sector_performance import SECTOR_MAP, SECTOR_COINS, SECTOR_NAMES
except ImportError:
    try:
        from sector_performance import SECTOR_MAP, SECTOR_COINS, SECTOR_NAMES
    except ImportError:
        SECTOR_MAP = {}
        SECTOR_COINS = defaultdict(list)
        SECTOR_NAMES = {}


class MarketHeatmap:
    """
    Market heatmap data generator.
    - Groups coins by sector
    - Calculates color intensity based on price change
    - Multi-timeframe support
    - Volume-weighted sizing
    - Returns structured data for frontend grid rendering
    """

    def __init__(self, market_data=None):
        self.market_data = market_data
        self._cache = {}
        self._cache_ttl = 120  # 2 min cache
        self._last_update = 0

    def _get_ticker_data(self) -> Dict:
        """Fetch all 24h ticker data and index by symbol."""
        if not self.market_data or not hasattr(self.market_data, "get_ticker_24h"):
            return {}

        try:
            tickers = self.market_data.get_ticker_24h()
            if not tickers:
                return {}
            return {t["symbol"]: t for t in tickers if "symbol" in t}
        except Exception as e:
            logger.debug(f"Ticker fetch error: {e}")
            return {}

    def _calc_intensity(self, change: float) -> float:
        """
        Calculate color intensity from -1.0 to 1.0.
        Positive = green, Negative = red, 0 = neutral.
        Capped at ±20% for max intensity.
        """
        if change == 0:
            return 0.0
        cap = 20.0
        clamped = max(-cap, min(cap, change))
        return round(clamped / cap, 4)

    def _calc_size_weight(self, volume: float, max_volume: float) -> float:
        """Calculate relative size weight based on volume (0.3 to 1.0)."""
        if max_volume <= 0:
            return 0.5
        ratio = volume / max_volume
        return round(max(0.3, min(1.0, ratio)), 4)

    def _change_to_color(self, intensity: float) -> str:
        """Convert intensity to hex color string."""
        if intensity > 0:
            alpha = int(min(255, intensity * 255))
            return f"rgba(0, 230, 118, {alpha / 255:.2f})"
        elif intensity < 0:
            alpha = int(min(255, abs(intensity) * 255))
            return f"rgba(255, 85, 85, {alpha / 255:.2f})"
        else:
            return "rgba(74, 85, 104, 0.3)"

    def generate_heatmap(self, timeframe: str = "24h") -> Dict:
        """
        Generate full heatmap data grouped by sector.

        Returns:
            {
                "sectors": [
                    {
                        "sector": "layer1",
                        "name": "Layer 1",
                        "avg_change": float,
                        "coins": [
                            {
                                "symbol": "BTCUSDT",
                                "label": "BTC",
                                "change": float,
                                "price": float,
                                "volume": float,
                                "intensity": float,
                                "size_weight": float,
                                "color": str,
                            }
                        ]
                    }
                ],
                "total_coins": int,
                "max_gainer": {...},
                "max_loser": {...},
                "timestamp": int
            }
        """
        cache_key = f"heatmap_{timeframe}"
        now = time.time()

        if (cache_key in self._cache and
                now - self._last_update < self._cache_ttl):
            return self._cache[cache_key]

        ticker_index = self._get_ticker_data()
        if not ticker_index:
            return {"sectors": [], "total_coins": 0, "timestamp": int(time.time())}

        # Find max volume for size weighting
        all_volumes = []
        for symbol in SECTOR_MAP:
            if symbol in ticker_index:
                try:
                    vol = float(ticker_index[symbol].get("quoteVolume", 0))
                    all_volumes.append(vol)
                except (ValueError, TypeError):
                    pass
        max_volume = max(all_volumes) if all_volumes else 1.0

        # Build sector groups
        sectors_data = []
        all_coins = []
        max_gainer = None
        max_loser = None

        for sector_key, coin_list in SECTOR_COINS.items():
            sector_coins = []

            for symbol in coin_list:
                if symbol not in ticker_index:
                    continue

                ticker = ticker_index[symbol]
                try:
                    change = float(ticker.get("priceChangePercent", 0))
                    price = float(ticker.get("lastPrice", 0))
                    volume = float(ticker.get("quoteVolume", 0))
                except (ValueError, TypeError):
                    continue

                # Adjust change based on timeframe
                if timeframe == "1h":
                    change = change / 24
                elif timeframe == "4h":
                    change = change / 6

                intensity = self._calc_intensity(change)
                size_weight = self._calc_size_weight(volume, max_volume)
                color = self._change_to_color(intensity)

                coin_entry = {
                    "symbol": symbol,
                    "label": symbol.replace("USDT", ""),
                    "change": round(change, 3),
                    "price": price,
                    "volume": round(volume, 2),
                    "intensity": intensity,
                    "size_weight": size_weight,
                    "color": color,
                }

                sector_coins.append(coin_entry)
                all_coins.append(coin_entry)

                # Track max gainer/loser
                if max_gainer is None or change > max_gainer["change"]:
                    max_gainer = coin_entry
                if max_loser is None or change < max_loser["change"]:
                    max_loser = coin_entry

            if sector_coins:
                # Sort coins within sector by change descending
                sector_coins.sort(key=lambda x: x["change"], reverse=True)
                avg_change = sum(c["change"] for c in sector_coins) / len(sector_coins)

                sectors_data.append({
                    "sector": sector_key,
                    "name": SECTOR_NAMES.get(sector_key, sector_key),
                    "avg_change": round(avg_change, 3),
                    "total_coins": len(sector_coins),
                    "coins": sector_coins,
                })

        # Sort sectors by avg_change descending
        sectors_data.sort(key=lambda x: x["avg_change"], reverse=True)

        result = {
            "sectors": sectors_data,
            "total_coins": len(all_coins),
            "total_sectors": len(sectors_data),
            "max_gainer": max_gainer,
            "max_loser": max_loser,
            "timeframe": timeframe,
            "timestamp": int(time.time()),
        }

        self._cache[cache_key] = result
        self._last_update = now

        return result

    def get_flat_heatmap(self, timeframe: str = "24h", limit: int = 100) -> List[Dict]:
        """
        Get flat list of all coins for simple heatmap grid.
        Sorted by absolute change (most volatile first).
        """
        data = self.generate_heatmap(timeframe)
        all_coins = []
        for sector in data.get("sectors", []):
            for coin in sector.get("coins", []):
                coin_with_sector = {**coin, "sector": sector["name"]}
                all_coins.append(coin_with_sector)

        all_coins.sort(key=lambda x: abs(x["change"]), reverse=True)
        return all_coins[:limit]

    def get_heatmap_summary(self, timeframe: str = "24h") -> Dict:
        """Complete heatmap summary for dashboard/API."""
        data = self.generate_heatmap(timeframe)
        flat = self.get_flat_heatmap(timeframe, 80)

        green_count = sum(1 for c in flat if c["change"] > 0)
        red_count = sum(1 for c in flat if c["change"] < 0)

        return {
            "heatmap": data,
            "flat_grid": flat,
            "green_count": green_count,
            "red_count": red_count,
            "sentiment": "bullish" if green_count > red_count else "bearish" if red_count > green_count else "neutral",
            "timestamp": int(time.time()),
        }


if __name__ == "__main__":
    hm = MarketHeatmap()
    print(f"Sectors available: {len(SECTOR_NAMES)}")
    print(f"Total coins in map: {len(SECTOR_MAP)}")
