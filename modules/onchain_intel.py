"""
Hansen Engine - Onchain Intelligence Module (P6)
Whale detection, exchange flow proxy, stablecoin flow analysis.
Derived from Binance market data — sovereign local, no external onchain API.
"""

import time
import logging
from typing import Dict, List, Optional

logger = logging.getLogger("hansen.onchain_intel")

# Stablecoin pairs to track for flow analysis
STABLECOINS = ["USDCUSDT", "FDUSDUSDT", "DAIUSDT", "TUSDUSDT"]

# Major coins for whale tracking
WHALE_WATCHLIST = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "ARBUSDT",
    "OPUSDT", "APTUSDT", "SUIUSDT", "TONUSDT", "DOGEUSDT",
    "SHIBUSDT", "PEPEUSDT", "FETUSDT", "NEARUSDT", "INJUSDT",
]

# Whale thresholds (USD equivalent)
WHALE_THRESHOLDS = {
    "BTCUSDT": 1000000,
    "ETHUSDT": 500000,
    "default": 200000,
}


class OnchainIntel:
    """
    Onchain intelligence derived from Binance data.
    - Whale activity detection (large volume spikes per coin)
    - Exchange flow proxy (volume direction analysis)
    - Stablecoin flow tracking
    - All sovereign local — no Etherscan/Dune/Glassnode needed
    """

    def __init__(self, market_data=None):
        self.market_data = market_data
        self._cache = {}
        self._cache_ttl = 180
        self._last_update = 0
        self._whale_alerts = []
        self._max_whale_history = 200

    def _get_all_tickers(self) -> Dict:
        """Fetch all 24h tickers indexed by symbol."""
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

    def detect_whale_activity(self) -> Dict:
        """
        Detect whale-like activity from volume and trade count anomalies.
        Large volume relative to average = potential whale activity.

        Returns:
            {
                "whale_coins": [...],
                "total_whale_signals": int,
                "whale_volume_usd": float,
            }
        """
        tickers = self._get_all_tickers()
        if not tickers:
            return {"whale_coins": [], "total_whale_signals": 0, "whale_volume_usd": 0}

        # Calculate average volume for USDT pairs
        volumes = []
        for sym, t in tickers.items():
            if sym.endswith("USDT"):
                try:
                    vol = float(t.get("quoteVolume", 0))
                    volumes.append(vol)
                except (ValueError, TypeError):
                    pass

        avg_vol = sum(volumes) / len(volumes) if volumes else 0

        whale_coins = []
        total_whale_vol = 0

        for symbol in WHALE_WATCHLIST:
            if symbol not in tickers:
                continue

            t = tickers[symbol]
            try:
                volume = float(t.get("quoteVolume", 0))
                price = float(t.get("lastPrice", 0))
                change = float(t.get("priceChangePercent", 0))
                trades = int(t.get("count", 0))
                high = float(t.get("highPrice", 0))
                low = float(t.get("lowPrice", 0))
            except (ValueError, TypeError):
                continue

            threshold = WHALE_THRESHOLDS.get(symbol, WHALE_THRESHOLDS["default"])
            vol_ratio = volume / avg_vol if avg_vol > 0 else 0

            # Whale signal: volume significantly above average
            if volume > threshold * 10 and vol_ratio > 3.0:
                avg_trade_size = volume / trades if trades > 0 else 0

                # Determine direction from price action
                if change > 1.0:
                    direction = "accumulation"
                    direction_label = "Buying Pressure"
                elif change < -1.0:
                    direction = "distribution"
                    direction_label = "Selling Pressure"
                else:
                    direction = "neutral"
                    direction_label = "Mixed Activity"

                whale_entry = {
                    "symbol": symbol,
                    "label": symbol.replace("USDT", ""),
                    "volume_usd": round(volume, 2),
                    "volume_ratio": round(vol_ratio, 2),
                    "avg_trade_size": round(avg_trade_size, 2),
                    "trade_count": trades,
                    "price": price,
                    "change_24h": round(change, 3),
                    "direction": direction,
                    "direction_label": direction_label,
                    "price_range": round((high - low) / low * 100, 2) if low > 0 else 0,
                    "whale_score": round(min(100, vol_ratio * 15), 1),
                }

                whale_coins.append(whale_entry)
                total_whale_vol += volume

        whale_coins.sort(key=lambda x: x["whale_score"], reverse=True)

        return {
            "whale_coins": whale_coins[:15],
            "total_whale_signals": len(whale_coins),
            "whale_volume_usd": round(total_whale_vol, 2),
            "timestamp": int(time.time()),
        }

    def analyze_exchange_flow(self) -> Dict:
        """
        Proxy exchange flow analysis from volume + price direction.
        - Rising price + high volume = inflow (buying/accumulation)
        - Falling price + high volume = outflow (selling/distribution)
        - Low volume + flat price = neutral

        Returns flow analysis for major coins.
        """
        tickers = self._get_all_tickers()
        if not tickers:
            return {"flows": [], "net_sentiment": "neutral"}

        flows = []
        inflow_count = 0
        outflow_count = 0
        total_inflow_vol = 0
        total_outflow_vol = 0

        for symbol in WHALE_WATCHLIST:
            if symbol not in tickers:
                continue

            t = tickers[symbol]
            try:
                volume = float(t.get("quoteVolume", 0))
                change = float(t.get("priceChangePercent", 0))
                price = float(t.get("lastPrice", 0))
                taker_buy_vol = float(t.get("volume", 0)) * 0.5  # estimate
            except (ValueError, TypeError):
                continue

            # Determine flow direction
            if change > 0.5 and volume > 50000000:
                flow_type = "inflow"
                flow_label = "Net Inflow"
                inflow_count += 1
                total_inflow_vol += volume
            elif change < -0.5 and volume > 50000000:
                flow_type = "outflow"
                flow_label = "Net Outflow"
                outflow_count += 1
                total_outflow_vol += volume
            else:
                flow_type = "neutral"
                flow_label = "Neutral"

            # Buy/sell pressure estimate from price vs OHLC
            try:
                open_p = float(t.get("openPrice", price))
                close_p = float(t.get("lastPrice", price))
                high_p = float(t.get("highPrice", price))
                low_p = float(t.get("lowPrice", price))

                if high_p != low_p:
                    buy_pressure = ((close_p - low_p) / (high_p - low_p)) * 100
                else:
                    buy_pressure = 50
            except (ValueError, TypeError, ZeroDivisionError):
                buy_pressure = 50

            flows.append({
                "symbol": symbol,
                "label": symbol.replace("USDT", ""),
                "volume_usd": round(volume, 2),
                "change_24h": round(change, 3),
                "flow_type": flow_type,
                "flow_label": flow_label,
                "buy_pressure": round(buy_pressure, 1),
                "price": price,
            })

        flows.sort(key=lambda x: x["volume_usd"], reverse=True)

        # Net sentiment
        if inflow_count > outflow_count * 1.5:
            net_sentiment = "bullish"
        elif outflow_count > inflow_count * 1.5:
            net_sentiment = "bearish"
        else:
            net_sentiment = "neutral"

        return {
            "flows": flows,
            "inflow_count": inflow_count,
            "outflow_count": outflow_count,
            "neutral_count": len(flows) - inflow_count - outflow_count,
            "total_inflow_vol": round(total_inflow_vol, 2),
            "total_outflow_vol": round(total_outflow_vol, 2),
            "net_sentiment": net_sentiment,
            "timestamp": int(time.time()),
        }

    def analyze_stablecoin_flow(self) -> Dict:
        """
        Analyze stablecoin volume and activity.
        Rising stablecoin volume = capital ready to deploy.
        """
        tickers = self._get_all_tickers()
        if not tickers:
            return {"stablecoins": [], "total_volume": 0}

        stables = []
        total_vol = 0

        for symbol in STABLECOINS:
            if symbol not in tickers:
                continue

            t = tickers[symbol]
            try:
                volume = float(t.get("quoteVolume", 0))
                change = float(t.get("priceChangePercent", 0))
                price = float(t.get("lastPrice", 0))
            except (ValueError, TypeError):
                continue

            total_vol += volume

            # Peg status
            if 0.995 <= price <= 1.005:
                peg_status = "stable"
            elif price < 0.995:
                peg_status = "depeg_low"
            else:
                peg_status = "depeg_high"

            stables.append({
                "symbol": symbol,
                "label": symbol.replace("USDT", ""),
                "price": price,
                "change_24h": round(change, 4),
                "volume_usd": round(volume, 2),
                "peg_status": peg_status,
            })

        stables.sort(key=lambda x: x["volume_usd"], reverse=True)

        # Capital deployment signal
        if total_vol > 500000000:
            deployment_signal = "high"
        elif total_vol > 100000000:
            deployment_signal = "moderate"
        else:
            deployment_signal = "low"

        return {
            "stablecoins": stables,
            "total_volume": round(total_vol, 2),
            "deployment_signal": deployment_signal,
            "timestamp": int(time.time()),
        }

    def get_onchain_summary(self) -> Dict:
        """Complete onchain intelligence summary for dashboard/API."""
        cache_key = "onchain_summary"
        now = time.time()

        if (cache_key in self._cache and
                now - self._last_update < self._cache_ttl):
            return self._cache[cache_key]

        summary = {
            "whale_activity": self.detect_whale_activity(),
            "exchange_flow": self.analyze_exchange_flow(),
            "stablecoin_flow": self.analyze_stablecoin_flow(),
            "timestamp": int(time.time()),
        }

        self._cache[cache_key] = summary
        self._last_update = now

        return summary


if __name__ == "__main__":
    oi = OnchainIntel()
    print(f"Whale watchlist: {len(WHALE_WATCHLIST)} coins")
    print(f"Stablecoins tracked: {len(STABLECOINS)}")
