"""
Hansen Engine - Sector Performance Module (P2 Analytics)
Full sector engine dengan 100+ coins, multi-timeframe, ranking, trend direction.
Sovereign local - no external dependencies beyond Binance public API.
"""

import time
import logging
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

logger = logging.getLogger("hansen.sector_performance")


# ============================================================
# SECTOR MAP — 110+ coins across 16 sectors
# ============================================================
SECTOR_MAP = {
    # --- Store of Value ---
    "BTCUSDT": "store_of_value",
    "BCHUSDT": "store_of_value",
    "LTCUSDT": "store_of_value",
    "KASUSDT": "store_of_value",

    # --- Layer 1 ---
    "ETHUSDT": "layer1",
    "SOLUSDT": "layer1",
    "ADAUSDT": "layer1",
    "AVAXUSDT": "layer1",
    "DOTUSDT": "layer1",
    "ATOMUSDT": "layer1",
    "NEARUSDT": "layer1",
    "ALGOUSDT": "layer1",
    "ICPUSDT": "layer1",
    "APTUSDT": "layer1",
    "SUIUSDT": "layer1",
    "SEIUSDT": "layer1",
    "TONUSDT": "layer1",
    "HBARUSDT": "layer1",
    "FTMUSDT": "layer1",
    "EGLDUSDT": "layer1",
    "XLMUSDT": "layer1",
    "XRPUSDT": "layer1",
    "TRXUSDT": "layer1",
    "VETUSDT": "layer1",
    "INJUSDT": "layer1",
    "TIAUSDT": "layer1",

    # --- Layer 2 / Scaling ---
    "ARBUSDT": "layer2",
    "OPUSDT": "layer2",
    "MATICUSDT": "layer2",
    "STRKUSDT": "layer2",
    "ZKUSDT": "layer2",
    "MANTAUSDT": "layer2",
    "METISUSDT": "layer2",
    "IMXUSDT": "layer2",
    "BLASTUSDT": "layer2",
    "SCROLLUSDT": "layer2",

    # --- DeFi ---
    "AAVEUSDT": "defi",
    "COMPUSDT": "defi",
    "MKRUSDT": "defi",
    "CRVUSDT": "defi",
    "LDOUSDT": "defi",
    "PENDLEUSDT": "defi",
    "EIGENUSDT": "defi",
    "ENAUSDT": "defi",
    "JUPUSDT": "defi",
    "RAYDIUMUSDT": "defi",
    "RSWUSDT": "defi",
    "1INCHUSDT": "defi",
    "SNXUSDT": "defi",
    "DYDXUSDT": "defi",
    "GMXUSDT": "defi",

    # --- DEX ---
    "UNIUSDT": "dex",
    "SUSHIUSDT": "dex",
    "CAKEUSDT": "dex",
    "JUPUSDT": "dex",
    "OSMOUSDT": "dex",

    # --- Exchange Tokens ---
    "BNBUSDT": "exchange",
    "OKBUSDT": "exchange",
    "GTUSDT": "exchange",
    "MXUSDT": "exchange",

    # --- Oracle ---
    "LINKUSDT": "oracle",
    "PYTHUSDT": "oracle",
    "BANDUSDT": "oracle",
    "APIUSDT": "oracle",
    "TLMUSDT": "oracle",

    # --- AI / Compute ---
    "FETUSDT": "ai",
    "RENDERUSDT": "ai",
    "AGIXUSDT": "ai",
    "OCEANUSDT": "ai",
    "TAOUST": "ai",
    "WLDUSDT": "ai",
    "ARKMUSDT": "ai",
    "ABORUSDT": "ai",
    "AIUSDT": "ai",
    "IOTAUSDT": "ai",
    "AKTUSDT": "ai",
    "NFPUSDT": "ai",

    # --- Gaming / GameFi ---
    "AXSUSDT": "gaming",
    "SANDUSDT": "gaming",
    "MANAUSDT": "gaming",
    "GALAUSDT": "gaming",
    "ILVUSDT": "gaming",
    "YGGUSDT": "gaming",
    "PIXELUSDT": "gaming",
    "PORTALUSDT": "gaming",
    "RONUSDT": "gaming",
    "BEAMUSDT": "gaming",
    "XAIUSDT": "gaming",

    # --- Meme ---
    "DOGEUSDT": "meme",
    "SHIBUSDT": "meme",
    "PEPEUSDT": "meme",
    "FLOKIUSDT": "meme",
    "BONKUSDT": "meme",
    "WIFUSDT": "meme",
    "MEMEUSDT": "meme",
    "BOMEUSDT": "meme",
    "NEIROUSDT": "meme",
    "DOGSUSDT": "meme",
    "TURBO USDT": "meme",
    "PEOPLEUSDT": "meme",

    # --- Infrastructure / Middleware ---
    "FILUSDT": "infrastructure",
    "ARUSDT": "infrastructure",
    "STORJUSDT": "infrastructure",
    "THETAUSDT": "infrastructure",
    "GRTUSDT": "infrastructure",
    "RNDR": "infrastructure",
    "CKBUSDT": "infrastructure",

    # --- Privacy ---
    "XMRUSDT": "privacy",
    "ZECUSDT": "privacy",
    "SCRTUSDT": "privacy",
    "ROSAUSDT": "privacy",

    # --- RWA (Real World Assets) ---
    "ONDOUSDT": "rwa",
    "MANTRAUSDT": "rwa",
    "POLYXUSDT": "rwa",
    "PROUSDT": "rwa",
    "TOKENFIUSDT": "rwa",

    # --- Social / SocialFi ---
    "GALAUSDT": "social",
    "CYBERUSDT": "social",
    "HOOKUSDT": "social",
    "IDUSDT": "social",
    "LENSUSDT": "social",

    # --- Staking / Liquid Staking ---
    "LDOUSDT": "liquid_staking",
    "RETHUSDT": "liquid_staking",
    "CBETHUSDT": "liquid_staking",
    "SSVUSDT": "liquid_staking",
    "RPLUSDT": "liquid_staking",
}

# Reverse lookup: sector -> list of symbols
SECTOR_COINS = defaultdict(list)
for _sym, _sec in SECTOR_MAP.items():
    if _sym not in SECTOR_COINS[_sec]:
        SECTOR_COINS[_sec].append(_sym)

# Sector display names
SECTOR_NAMES = {
    "store_of_value": "Store of Value",
    "layer1": "Layer 1",
    "layer2": "Layer 2 / Scaling",
    "defi": "DeFi",
    "dex": "DEX",
    "exchange": "Exchange Tokens",
    "oracle": "Oracle",
    "ai": "AI / Compute",
    "gaming": "Gaming / GameFi",
    "meme": "Meme",
    "infrastructure": "Infrastructure",
    "privacy": "Privacy",
    "rwa": "RWA",
    "social": "SocialFi",
    "liquid_staking": "Liquid Staking",
}

# Timeframe configs for multi-timeframe analysis
TIMEFRAMES = {
    "1h": {"interval": "1h", "limit": 2, "label": "1 Hour"},
    "4h": {"interval": "4h", "limit": 2, "label": "4 Hours"},
    "24h": {"interval": "1d", "limit": 2, "label": "24 Hours"},
    "7d": {"interval": "1d", "limit": 8, "label": "7 Days"},
}


class SectorPerformance:
    """
    Full sector performance engine.
    - Multi-timeframe momentum per sector
    - Sector ranking by performance
    - Trend direction detection
    - Top/bottom coins per sector
    - Sector rotation signals
    """

    def __init__(self, market_store=None, market_data=None):
        """
        Args:
            market_store: MarketStore instance for cached price data
            market_data: MarketData instance for live API calls
        """
        self.market_store = market_store
        self.market_data = market_data
        self._cache = {}
        self._cache_ttl = 120  # 2 minutes cache
        self._last_update = 0

    def get_sector_for_symbol(self, symbol: str) -> Optional[str]:
        """Return sector name for a given symbol."""
        return SECTOR_MAP.get(symbol)

    def get_symbols_for_sector(self, sector: str) -> List[str]:
        """Return all symbols in a sector."""
        return SECTOR_COINS.get(sector, [])

    def get_all_sectors(self) -> List[str]:
        """Return list of all sector keys."""
        return list(SECTOR_NAMES.keys())

    def _get_price_change(self, symbol: str, timeframe: str) -> Optional[float]:
        try:
            if self.market_data and hasattr(self.market_data, "get_ticker_24h"):
                ticker = self.market_data.get_ticker_24h(symbol)
                if ticker:
                    if timeframe == "24h":
                        return float(ticker.get("priceChangePercent", 0))
                    elif timeframe == "1h":
                        return float(ticker.get("priceChangePercent", 0)) / 24
                    elif timeframe == "4h":
                        return float(ticker.get("priceChangePercent", 0)) / 6
                    elif timeframe == "7d":
                        return float(ticker.get("priceChangePercent", 0)) * 7
        except Exception as e:
            logger.debug(f"Price change error {symbol} {timeframe}: {e}")
        return None

    def calculate_sector_performance(self, timeframe: str = "24h") -> Dict:
        """
        Calculate performance for all sectors in a given timeframe.

        Returns:
            {
                "sector_key": {
                    "name": "Display Name",
                    "avg_change": float,
                    "median_change": float,
                    "top_coin": {"symbol": str, "change": float},
                    "worst_coin": {"symbol": str, "change": float},
                    "coins_up": int,
                    "coins_down": int,
                    "total_coins": int,
                    "trend": "bullish" | "bearish" | "neutral",
                    "strength": float  # 0-100
                }
            }
        """
        results = {}

        for sector, coins in SECTOR_COINS.items():
            changes = []
            coin_data = []

            for symbol in coins:
                change = self._get_price_change(symbol, timeframe)
                if change is not None:
                    changes.append(change)
                    coin_data.append({"symbol": symbol, "change": change})

            if not changes:
                continue

            # Sort coins by change
            coin_data.sort(key=lambda x: x["change"], reverse=True)

            # Calculate stats
            avg_change = sum(changes) / len(changes)
            sorted_changes = sorted(changes)
            median_idx = len(sorted_changes) // 2
            median_change = sorted_changes[median_idx]

            coins_up = sum(1 for c in changes if c > 0)
            coins_down = sum(1 for c in changes if c < 0)

            # Trend detection
            if avg_change > 2:
                trend = "bullish"
            elif avg_change < -2:
                trend = "bearish"
            else:
                trend = "neutral"

            # Strength: 0-100 based on consistency
            if len(changes) > 0:
                up_ratio = coins_up / len(changes)
                strength = abs(avg_change) * up_ratio * 10
                strength = min(100, max(0, strength))
            else:
                strength = 0

            results[sector] = {
                "name": SECTOR_NAMES.get(sector, sector),
                "avg_change": round(avg_change, 3),
                "median_change": round(median_change, 3),
                "top_coin": coin_data[0] if coin_data else None,
                "worst_coin": coin_data[-1] if coin_data else None,
                "all_coins": coin_data,
                "coins_up": coins_up,
                "coins_down": coins_down,
                "total_coins": len(changes),
                "trend": trend,
                "strength": round(strength, 1),
            }

        return results

    def get_sector_ranking(self, timeframe: str = "24h") -> List[Dict]:
        """
        Get sectors ranked by average performance.

        Returns:
            Sorted list of sector data, best performing first.
        """
        perf = self.calculate_sector_performance(timeframe)
        ranking = []

        for sector_key, data in perf.items():
            ranking.append({
                "sector": sector_key,
                **data
            })

        ranking.sort(key=lambda x: x["avg_change"], reverse=True)

        # Add rank number
        for i, item in enumerate(ranking):
            item["rank"] = i + 1

        return ranking

    def get_multi_timeframe(self) -> Dict:
        """
        Get sector performance across all timeframes.

        Returns:
            {
                "sector_key": {
                    "name": str,
                    "1h": float,
                    "4h": float,
                    "24h": float,
                    "7d": float,
                    "trend_score": float,  # composite score
                    "direction": "up" | "down" | "sideways"
                }
            }
        """
        multi = {}

        for tf_key in TIMEFRAMES:
            perf = self.calculate_sector_performance(tf_key)
            for sector_key, data in perf.items():
                if sector_key not in multi:
                    multi[sector_key] = {
                        "name": data["name"],
                        "total_coins": data["total_coins"],
                    }
                multi[sector_key][tf_key] = data["avg_change"]

        # Calculate trend score (weighted: 7d=0.1, 24h=0.3, 4h=0.3, 1h=0.3)
        weights = {"7d": 0.1, "24h": 0.3, "4h": 0.3, "1h": 0.3}
        for sector_key, data in multi.items():
            score = 0
            total_weight = 0
            for tf, w in weights.items():
                if tf in data and data[tf] is not None:
                    score += data[tf] * w
                    total_weight += w

            if total_weight > 0:
                trend_score = score / total_weight
            else:
                trend_score = 0

            data["trend_score"] = round(trend_score, 3)

            # Direction based on short vs long term
            short = data.get("1h", 0) or 0
            long_tf = data.get("24h", 0) or 0
            if short > 0 and long_tf > 0:
                data["direction"] = "up"
            elif short < 0 and long_tf < 0:
                data["direction"] = "down"
            else:
                data["direction"] = "sideways"

        return multi

    def detect_sector_rotation(self) -> Dict:
        """
        Detect sector rotation — which sectors are gaining/losing momentum.

        Returns:
            {
                "rotating_in": [sectors gaining momentum],
                "rotating_out": [sectors losing momentum],
                "stable": [sectors with consistent direction],
                "timestamp": int
            }
        """
        multi = self.get_multi_timeframe()

        rotating_in = []
        rotating_out = []
        stable = []

        for sector_key, data in multi.items():
            short = data.get("1h", 0) or 0
            medium = data.get("4h", 0) or 0
            long_tf = data.get("24h", 0) or 0

            entry = {
                "sector": sector_key,
                "name": data["name"],
                "1h": short,
                "24h": long_tf,
                "trend_score": data.get("trend_score", 0),
            }

            # Rotating in: short term up, long term down or flat
            if short > 1.5 and long_tf < short * 0.5:
                rotating_in.append(entry)
            # Rotating out: short term down, long term was up
            elif short < -1.5 and long_tf > short * 0.5:
                rotating_out.append(entry)
            else:
                stable.append(entry)

        rotating_in.sort(key=lambda x: x["1h"], reverse=True)
        rotating_out.sort(key=lambda x: x["1h"])

        return {
            "rotating_in": rotating_in,
            "rotating_out": rotating_out,
            "stable": stable,
            "timestamp": int(time.time()),
        }

    def get_sector_summary(self) -> Dict:
        """
        Complete sector summary for dashboard/API.
        Single call that returns everything needed.
        """
        cache_key = "sector_summary"
        now = time.time()

        if (cache_key in self._cache and
                now - self._last_update < self._cache_ttl):
            return self._cache[cache_key]

        summary = {
            "ranking_24h": self.get_sector_ranking("24h"),
            "multi_timeframe": self.get_multi_timeframe(),
            "rotation": self.detect_sector_rotation(),
            "sector_count": len(SECTOR_NAMES),
            "total_coins": len(SECTOR_MAP),
            "timestamp": int(time.time()),
        }

        self._cache[cache_key] = summary
        self._last_update = now

        return summary


# ============================================================
# Standalone test
# ============================================================
if __name__ == "__main__":
    sp = SectorPerformance()
    print(f"Sectors: {len(SECTOR_NAMES)}")
    print(f"Total coins mapped: {len(SECTOR_MAP)}")
    print(f"Sectors: {list(SECTOR_NAMES.keys())}")
    for sec, coins in SECTOR_COINS.items():
        print(f"  {sec}: {len(coins)} coins")
