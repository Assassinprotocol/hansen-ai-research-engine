"""
Hansen Engine - Correlation Matrix Module (P2 Analytics)
Korelasi antar major coins menggunakan price history lokal.
Sovereign local - no external dependencies, pure Python math.
"""

import time
import math
import logging
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

logger = logging.getLogger("hansen.correlation_matrix")


# ============================================================
# DEFAULT CORRELATION PAIRS — Major coins to track
# ============================================================
DEFAULT_PAIRS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "MATICUSDT",
    "ATOMUSDT", "NEARUSDT", "ARBUSDT", "OPUSDT", "APTUSDT",
    "SUIUSDT", "INJUSDT", "FETUSDT", "RENDERUSDT", "DOGEUSDT",
    "SHIBUSDT", "PEPEUSDT", "TONUSDT", "TIAUSDT", "WLDUSDT",
]

# Short labels for display
SYMBOL_LABELS = {
    "BTCUSDT": "BTC",
    "ETHUSDT": "ETH",
    "BNBUSDT": "BNB",
    "SOLUSDT": "SOL",
    "XRPUSDT": "XRP",
    "ADAUSDT": "ADA",
    "AVAXUSDT": "AVAX",
    "DOTUSDT": "DOT",
    "LINKUSDT": "LINK",
    "MATICUSDT": "MATIC",
    "ATOMUSDT": "ATOM",
    "NEARUSDT": "NEAR",
    "ARBUSDT": "ARB",
    "OPUSDT": "OP",
    "APTUSDT": "APT",
    "SUIUSDT": "SUI",
    "INJUSDT": "INJ",
    "FETUSDT": "FET",
    "RENDERUSDT": "RENDER",
    "DOGEUSDT": "DOGE",
    "SHIBUSDT": "SHIB",
    "PEPEUSDT": "PEPE",
    "TONUSDT": "TON",
    "TIAUSDT": "TIA",
    "WLDUSDT": "WLD",
}

# Timeframe options for correlation window
CORRELATION_WINDOWS = {
    "24h": 24,      # 24 data points (hourly)
    "7d": 168,      # 168 hourly data points
    "14d": 336,     # 336 hourly data points
    "30d": 720,     # 720 hourly data points
}


def _mean(values: List[float]) -> float:
    """Calculate mean of a list."""
    if not values:
        return 0.0
    return sum(values) / len(values)


def _std_dev(values: List[float]) -> float:
    """Calculate standard deviation."""
    if len(values) < 2:
        return 0.0
    avg = _mean(values)
    variance = sum((x - avg) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(variance)


def _pearson_correlation(x: List[float], y: List[float]) -> Optional[float]:
    """
    Calculate Pearson correlation coefficient between two lists.
    Returns value between -1.0 and 1.0, or None if calculation fails.
    """
    if len(x) != len(y) or len(x) < 3:
        return None

    n = len(x)
    mean_x = _mean(x)
    mean_y = _mean(y)
    std_x = _std_dev(x)
    std_y = _std_dev(y)

    if std_x == 0 or std_y == 0:
        return None

    covariance = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n)) / (n - 1)
    correlation = covariance / (std_x * std_y)

    # Clamp to [-1, 1] to handle floating point errors
    return max(-1.0, min(1.0, correlation))


def _price_to_returns(prices: List[float]) -> List[float]:
    """Convert price series to percentage returns."""
    if len(prices) < 2:
        return []
    returns = []
    for i in range(1, len(prices)):
        if prices[i - 1] > 0:
            ret = (prices[i] - prices[i - 1]) / prices[i - 1] * 100
            returns.append(ret)
        else:
            returns.append(0.0)
    return returns


class CorrelationMatrix:
    """
    Correlation matrix engine for crypto pairs.
    - Pearson correlation between price returns
    - Multi-window analysis (24h, 7d, 14d, 30d)
    - Strongest/weakest correlation detection
    - Decorrelation alerts
    - Beta calculation vs BTC
    """

    def __init__(self, market_store=None, market_data=None):
        """
        Args:
            market_store: MarketStore instance for cached price history
            market_data: MarketData instance for live API calls
        """
        self.market_store = market_store
        self.market_data = market_data
        self.pairs = DEFAULT_PAIRS.copy()
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes cache
        self._last_update = 0

    def set_pairs(self, pairs: List[str]):
        """Override default pairs list."""
        self.pairs = pairs

    def _get_price_series(self, symbol: str, window: int) -> List[float]:
        """
        Get price series for a symbol.
        Tries market_store first, then falls back to market_data.

        Args:
            symbol: Trading pair symbol
            window: Number of data points needed

        Returns:
            List of close prices
        """
        prices = []

        try:
            # Try from market_store
            if self.market_store:
                history = self.market_store.get_price_history(symbol)
                if history and len(history) >= window:
                    prices = [h["close"] for h in history[-window:]]
                    return prices
                elif history:
                    prices = [h["close"] for h in history]
                    if len(prices) >= 3:
                        return prices

            # Fallback: market_data API (klines)
            if self.market_data and hasattr(self.market_data, "get_klines"):
                klines = self.market_data.get_klines(
                    symbol=symbol,
                    interval="1h",
                    limit=min(window, 1000)
                )
                if klines:
                    prices = [float(k[4]) for k in klines]  # close price
                    return prices

        except Exception as e:
            logger.debug(f"Price series error {symbol}: {e}")

        return prices

    def calculate_correlation(self, symbol_a: str, symbol_b: str,
                              window: str = "7d") -> Optional[float]:
        """
        Calculate correlation between two symbols.

        Args:
            symbol_a: First symbol
            symbol_b: Second symbol
            window: Time window key (24h, 7d, 14d, 30d)

        Returns:
            Pearson correlation coefficient or None
        """
        data_points = CORRELATION_WINDOWS.get(window, 168)

        prices_a = self._get_price_series(symbol_a, data_points)
        prices_b = self._get_price_series(symbol_b, data_points)

        if not prices_a or not prices_b:
            return None

        # Align lengths
        min_len = min(len(prices_a), len(prices_b))
        if min_len < 3:
            return None

        prices_a = prices_a[-min_len:]
        prices_b = prices_b[-min_len:]

        # Convert to returns
        returns_a = _price_to_returns(prices_a)
        returns_b = _price_to_returns(prices_b)

        return _pearson_correlation(returns_a, returns_b)

    def build_matrix(self, window: str = "7d",
                     pairs: Optional[List[str]] = None) -> Dict:
        """
        Build full NxN correlation matrix.

        Args:
            window: Time window
            pairs: Custom pairs list (uses self.pairs if None)

        Returns:
            {
                "labels": ["BTC", "ETH", ...],
                "symbols": ["BTCUSDT", "ETHUSDT", ...],
                "matrix": [[1.0, 0.85, ...], [0.85, 1.0, ...], ...],
                "window": str,
                "timestamp": int
            }
        """
        cache_key = f"matrix_{window}"
        now = time.time()

        if (cache_key in self._cache and
                now - self._last_update < self._cache_ttl):
            return self._cache[cache_key]

        use_pairs = pairs or self.pairs
        n = len(use_pairs)
        labels = [SYMBOL_LABELS.get(s, s.replace("USDT", "")) for s in use_pairs]

        # Initialize NxN matrix with None
        matrix = [[None] * n for _ in range(n)]

        # Pre-fetch all return series
        return_cache = {}
        data_points = CORRELATION_WINDOWS.get(window, 168)

        for symbol in use_pairs:
            prices = self._get_price_series(symbol, data_points)
            if prices and len(prices) >= 3:
                return_cache[symbol] = _price_to_returns(prices)
            else:
                return_cache[symbol] = None

        # Build matrix
        for i in range(n):
            for j in range(n):
                if i == j:
                    matrix[i][j] = 1.0
                elif j > i:
                    # Calculate only upper triangle
                    sym_a = use_pairs[i]
                    sym_b = use_pairs[j]
                    ret_a = return_cache.get(sym_a)
                    ret_b = return_cache.get(sym_b)

                    if ret_a and ret_b:
                        min_len = min(len(ret_a), len(ret_b))
                        if min_len >= 3:
                            corr = _pearson_correlation(
                                ret_a[-min_len:],
                                ret_b[-min_len:]
                            )
                            if corr is not None:
                                matrix[i][j] = round(corr, 4)
                                matrix[j][i] = round(corr, 4)
                else:
                    # Lower triangle — mirror from upper
                    if matrix[i][j] is None and matrix[j][i] is not None:
                        matrix[i][j] = matrix[j][i]

        result = {
            "labels": labels,
            "symbols": use_pairs,
            "matrix": matrix,
            "window": window,
            "data_points": data_points,
            "timestamp": int(time.time()),
        }

        self._cache[cache_key] = result
        self._last_update = now

        return result

    def get_strongest_correlations(self, window: str = "7d",
                                    top_n: int = 10) -> List[Dict]:
        """
        Get the strongest correlated pairs (highest positive correlation).

        Returns:
            [{"pair": "BTC/ETH", "correlation": 0.95, ...}, ...]
        """
        data = self.build_matrix(window)
        pairs_list = []

        symbols = data["symbols"]
        labels = data["labels"]
        matrix = data["matrix"]
        n = len(symbols)

        for i in range(n):
            for j in range(i + 1, n):
                corr = matrix[i][j]
                if corr is not None:
                    pairs_list.append({
                        "pair": f"{labels[i]}/{labels[j]}",
                        "symbol_a": symbols[i],
                        "symbol_b": symbols[j],
                        "correlation": corr,
                        "strength": abs(corr),
                    })

        # Sort by absolute correlation descending
        pairs_list.sort(key=lambda x: x["strength"], reverse=True)
        return pairs_list[:top_n]

    def get_weakest_correlations(self, window: str = "7d",
                                  top_n: int = 10) -> List[Dict]:
        """
        Get the most decorrelated pairs (closest to 0 or negative).
        Useful for diversification / hedging.

        Returns:
            [{"pair": "BTC/DOGE", "correlation": -0.15, ...}, ...]
        """
        data = self.build_matrix(window)
        pairs_list = []

        symbols = data["symbols"]
        labels = data["labels"]
        matrix = data["matrix"]
        n = len(symbols)

        for i in range(n):
            for j in range(i + 1, n):
                corr = matrix[i][j]
                if corr is not None:
                    pairs_list.append({
                        "pair": f"{labels[i]}/{labels[j]}",
                        "symbol_a": symbols[i],
                        "symbol_b": symbols[j],
                        "correlation": corr,
                        "strength": abs(corr),
                    })

        # Sort by absolute correlation ascending (closest to 0)
        pairs_list.sort(key=lambda x: x["strength"])
        return pairs_list[:top_n]

    def get_beta_vs_btc(self, window: str = "7d") -> List[Dict]:
        """
        Calculate beta of each coin vs BTC.
        Beta > 1 = more volatile than BTC
        Beta < 1 = less volatile than BTC
        Beta < 0 = inverse to BTC

        Returns:
            [{"symbol": "ETHUSDT", "label": "ETH", "beta": 1.2, "correlation": 0.85}, ...]
        """
        data_points = CORRELATION_WINDOWS.get(window, 168)
        btc_prices = self._get_price_series("BTCUSDT", data_points)

        if not btc_prices or len(btc_prices) < 3:
            return []

        btc_returns = _price_to_returns(btc_prices)
        btc_std = _std_dev(btc_returns)

        if btc_std == 0:
            return []

        results = []
        for symbol in self.pairs:
            if symbol == "BTCUSDT":
                results.append({
                    "symbol": "BTCUSDT",
                    "label": "BTC",
                    "beta": 1.0,
                    "correlation": 1.0,
                })
                continue

            prices = self._get_price_series(symbol, data_points)
            if not prices or len(prices) < 3:
                continue

            min_len = min(len(btc_returns), len(_price_to_returns(prices)))
            if min_len < 3:
                continue

            coin_returns = _price_to_returns(prices)[-min_len:]
            btc_ret_aligned = btc_returns[-min_len:]

            corr = _pearson_correlation(coin_returns, btc_ret_aligned)
            if corr is None:
                continue

            coin_std = _std_dev(coin_returns)
            btc_std_aligned = _std_dev(btc_ret_aligned)

            if btc_std_aligned > 0:
                beta = corr * (coin_std / btc_std_aligned)
            else:
                beta = 0

            results.append({
                "symbol": symbol,
                "label": SYMBOL_LABELS.get(symbol, symbol.replace("USDT", "")),
                "beta": round(beta, 3),
                "correlation": round(corr, 4),
            })

        results.sort(key=lambda x: x["beta"], reverse=True)
        return results

    def get_correlation_summary(self, window: str = "7d") -> Dict:
        """
        Complete correlation summary for dashboard/API.
        Single call that returns everything needed.
        """
        cache_key = f"corr_summary_{window}"
        now = time.time()

        if (cache_key in self._cache and
                now - self._last_update < self._cache_ttl):
            return self._cache[cache_key]

        summary = {
            "matrix": self.build_matrix(window),
            "strongest": self.get_strongest_correlations(window, 10),
            "weakest": self.get_weakest_correlations(window, 10),
            "beta_vs_btc": self.get_beta_vs_btc(window),
            "available_windows": list(CORRELATION_WINDOWS.keys()),
            "current_window": window,
            "total_pairs": len(self.pairs),
            "timestamp": int(time.time()),
        }

        self._cache[cache_key] = summary
        self._last_update = now

        return summary


# ============================================================
# Standalone test
# ============================================================
if __name__ == "__main__":
    cm = CorrelationMatrix()
    print(f"Tracking {len(cm.pairs)} pairs")
    print(f"Labels: {[SYMBOL_LABELS.get(s, s) for s in cm.pairs]}")
    print(f"Windows: {list(CORRELATION_WINDOWS.keys())}")

    # Test pure math functions
    test_x = [1.0, 2.0, 3.0, 4.0, 5.0]
    test_y = [1.1, 2.2, 2.9, 4.1, 5.0]
    corr = _pearson_correlation(test_x, test_y)
    print(f"Test correlation: {corr:.4f}")  # Should be ~0.999
