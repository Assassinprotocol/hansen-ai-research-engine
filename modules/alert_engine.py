"""
Hansen Engine - Alert Engine Module (P3 Alerts)
Price alerts, funding rate spikes, liquidation surges, volume anomaly detection.
Sovereign local - no external dependencies.
"""

import json
import os
import time
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger("hansen.alert_engine")

# Alert storage path
ALERT_HISTORY_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "alert_history.json")

# Severity levels
SEVERITY_INFO = "info"
SEVERITY_WARNING = "warning"
SEVERITY_CRITICAL = "critical"

# Alert type constants
ALERT_PRICE_PUMP = "price_pump"
ALERT_PRICE_DUMP = "price_dump"
ALERT_FUNDING_SPIKE = "funding_spike"
ALERT_FUNDING_NEGATIVE = "funding_negative"
ALERT_LIQUIDATION_SURGE = "liquidation_surge"
ALERT_VOLUME_ANOMALY = "volume_anomaly"
ALERT_VOLATILITY_SPIKE = "volatility_spike"
ALERT_SECTOR_ROTATION = "sector_rotation"

# Thresholds
THRESHOLDS = {
    "price_pump_warning": 5.0,
    "price_pump_critical": 10.0,
    "price_dump_warning": -5.0,
    "price_dump_critical": -10.0,
    "funding_spike_warning": 0.05,
    "funding_spike_critical": 0.1,
    "funding_negative_warning": -0.03,
    "funding_negative_critical": -0.08,
    "liquidation_surge_warning": 5000000,
    "liquidation_surge_critical": 20000000,
    "volume_anomaly_multiplier": 2.5,
}

# Max alerts to keep in history
MAX_ALERT_HISTORY = 500


class AlertEngine:
    """
    Real-time alert engine for crypto market events.
    - Price pump/dump detection
    - Funding rate spike alerts
    - Liquidation surge monitoring
    - Volume anomaly detection
    - Persistent alert history (JSON)
    - Severity levels: info, warning, critical
    - Cooldown to prevent alert spam
    """

    def __init__(self, market_data=None):
        self.market_data = market_data
        self._alerts = []
        self._active_alerts = []
        self._cooldowns = {}
        self._cooldown_seconds = 300  # 5 min cooldown per symbol per type
        self._last_scan = 0
        self._scan_interval = 60  # scan every 60 seconds
        self._load_history()

    def _load_history(self):
        """Load alert history from JSON file."""
        try:
            if os.path.exists(ALERT_HISTORY_PATH):
                with open(ALERT_HISTORY_PATH, "r") as f:
                    data = json.load(f)
                    self._alerts = data if isinstance(data, list) else []
            else:
                self._alerts = []
        except Exception as e:
            logger.debug(f"Alert history load error: {e}")
            self._alerts = []

    def _save_history(self):
        """Save alert history to JSON file."""
        try:
            os.makedirs(os.path.dirname(ALERT_HISTORY_PATH), exist_ok=True)
            trimmed = self._alerts[-MAX_ALERT_HISTORY:]
            with open(ALERT_HISTORY_PATH, "w") as f:
                json.dump(trimmed, f, indent=2)
        except Exception as e:
            logger.debug(f"Alert history save error: {e}")

    def _check_cooldown(self, symbol: str, alert_type: str) -> bool:
        """Check if alert is in cooldown period."""
        key = f"{symbol}:{alert_type}"
        now = time.time()
        if key in self._cooldowns:
            if now - self._cooldowns[key] < self._cooldown_seconds:
                return True
        return False

    def _set_cooldown(self, symbol: str, alert_type: str):
        """Set cooldown for an alert."""
        key = f"{symbol}:{alert_type}"
        self._cooldowns[key] = time.time()

    def _create_alert(self, alert_type: str, severity: str, symbol: str,
                      message: str, value: float, threshold: float,
                      extra: Optional[Dict] = None) -> Dict:
        """Create a new alert entry."""
        alert = {
            "id": f"{int(time.time())}_{symbol}_{alert_type}",
            "type": alert_type,
            "severity": severity,
            "symbol": symbol,
            "message": message,
            "value": round(value, 4),
            "threshold": round(threshold, 4),
            "timestamp": int(time.time()),
            "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "acknowledged": False,
        }
        if extra:
            alert["extra"] = extra
        return alert

    def _emit_alert(self, alert: Dict):
        """Store alert and set cooldown."""
        self._alerts.append(alert)
        self._active_alerts.append(alert)
        self._set_cooldown(alert["symbol"], alert["type"])
        self._save_history()
        logger.info(f"[ALERT] {alert['severity'].upper()} | {alert['symbol']} | {alert['message']}")

    def scan_price_alerts(self) -> List[Dict]:
        """Scan for price pump/dump alerts using 24h ticker data."""
        new_alerts = []
        if not self.market_data or not hasattr(self.market_data, "get_ticker_24h"):
            return new_alerts

        try:
            tickers = self.market_data.get_ticker_24h()
            if not tickers:
                return new_alerts

            for ticker in tickers:
                symbol = ticker.get("symbol", "")
                if not symbol.endswith("USDT"):
                    continue

                try:
                    change = float(ticker.get("priceChangePercent", 0))
                except (ValueError, TypeError):
                    continue

                # Price pump
                if change >= THRESHOLDS["price_pump_critical"]:
                    if not self._check_cooldown(symbol, ALERT_PRICE_PUMP):
                        alert = self._create_alert(
                            ALERT_PRICE_PUMP, SEVERITY_CRITICAL, symbol,
                            f"{symbol} pumped {change:+.2f}% in 24h",
                            change, THRESHOLDS["price_pump_critical"],
                            {"price": float(ticker.get("lastPrice", 0)),
                             "volume": float(ticker.get("quoteVolume", 0))}
                        )
                        self._emit_alert(alert)
                        new_alerts.append(alert)
                elif change >= THRESHOLDS["price_pump_warning"]:
                    if not self._check_cooldown(symbol, ALERT_PRICE_PUMP):
                        alert = self._create_alert(
                            ALERT_PRICE_PUMP, SEVERITY_WARNING, symbol,
                            f"{symbol} up {change:+.2f}% in 24h",
                            change, THRESHOLDS["price_pump_warning"]
                        )
                        self._emit_alert(alert)
                        new_alerts.append(alert)

                # Price dump
                if change <= THRESHOLDS["price_dump_critical"]:
                    if not self._check_cooldown(symbol, ALERT_PRICE_DUMP):
                        alert = self._create_alert(
                            ALERT_PRICE_DUMP, SEVERITY_CRITICAL, symbol,
                            f"{symbol} dumped {change:+.2f}% in 24h",
                            change, THRESHOLDS["price_dump_critical"],
                            {"price": float(ticker.get("lastPrice", 0)),
                             "volume": float(ticker.get("quoteVolume", 0))}
                        )
                        self._emit_alert(alert)
                        new_alerts.append(alert)
                elif change <= THRESHOLDS["price_dump_warning"]:
                    if not self._check_cooldown(symbol, ALERT_PRICE_DUMP):
                        alert = self._create_alert(
                            ALERT_PRICE_DUMP, SEVERITY_WARNING, symbol,
                            f"{symbol} down {change:+.2f}% in 24h",
                            change, THRESHOLDS["price_dump_warning"]
                        )
                        self._emit_alert(alert)
                        new_alerts.append(alert)

        except Exception as e:
            logger.debug(f"Price alert scan error: {e}")

        return new_alerts

    def scan_funding_alerts(self, funding_data: Optional[List] = None) -> List[Dict]:
        """Scan for funding rate spike alerts."""
        new_alerts = []
        if not funding_data:
            return new_alerts

        try:
            for item in funding_data:
                symbol = item.get("symbol", "")
                try:
                    rate = float(item.get("funding_rate", item.get("lastFundingRate", 0)))
                except (ValueError, TypeError):
                    continue

                rate_pct = rate * 100

                # Positive funding spike
                if rate_pct >= THRESHOLDS["funding_spike_critical"]:
                    if not self._check_cooldown(symbol, ALERT_FUNDING_SPIKE):
                        alert = self._create_alert(
                            ALERT_FUNDING_SPIKE, SEVERITY_CRITICAL, symbol,
                            f"{symbol} funding rate extreme: {rate_pct:+.4f}%",
                            rate_pct, THRESHOLDS["funding_spike_critical"]
                        )
                        self._emit_alert(alert)
                        new_alerts.append(alert)
                elif rate_pct >= THRESHOLDS["funding_spike_warning"]:
                    if not self._check_cooldown(symbol, ALERT_FUNDING_SPIKE):
                        alert = self._create_alert(
                            ALERT_FUNDING_SPIKE, SEVERITY_WARNING, symbol,
                            f"{symbol} funding rate elevated: {rate_pct:+.4f}%",
                            rate_pct, THRESHOLDS["funding_spike_warning"]
                        )
                        self._emit_alert(alert)
                        new_alerts.append(alert)

                # Negative funding
                if rate_pct <= THRESHOLDS["funding_negative_critical"]:
                    if not self._check_cooldown(symbol, ALERT_FUNDING_NEGATIVE):
                        alert = self._create_alert(
                            ALERT_FUNDING_NEGATIVE, SEVERITY_CRITICAL, symbol,
                            f"{symbol} funding deeply negative: {rate_pct:+.4f}%",
                            rate_pct, THRESHOLDS["funding_negative_critical"]
                        )
                        self._emit_alert(alert)
                        new_alerts.append(alert)
                elif rate_pct <= THRESHOLDS["funding_negative_warning"]:
                    if not self._check_cooldown(symbol, ALERT_FUNDING_NEGATIVE):
                        alert = self._create_alert(
                            ALERT_FUNDING_NEGATIVE, SEVERITY_WARNING, symbol,
                            f"{symbol} funding negative: {rate_pct:+.4f}%",
                            rate_pct, THRESHOLDS["funding_negative_warning"]
                        )
                        self._emit_alert(alert)
                        new_alerts.append(alert)

        except Exception as e:
            logger.debug(f"Funding alert scan error: {e}")

        return new_alerts

    def scan_liquidation_alerts(self, liq_data: Optional[List] = None) -> List[Dict]:
        """Scan for liquidation surge alerts."""
        new_alerts = []
        if not liq_data:
            return new_alerts

        try:
            for item in liq_data:
                symbol = item.get("symbol", "")
                try:
                    total_liq = float(item.get("total_usd", item.get("amount", 0)))
                except (ValueError, TypeError):
                    continue

                if total_liq >= THRESHOLDS["liquidation_surge_critical"]:
                    if not self._check_cooldown(symbol, ALERT_LIQUIDATION_SURGE):
                        alert = self._create_alert(
                            ALERT_LIQUIDATION_SURGE, SEVERITY_CRITICAL, symbol,
                            f"{symbol} massive liquidation: ${total_liq:,.0f}",
                            total_liq, THRESHOLDS["liquidation_surge_critical"],
                            {"side": item.get("side", "unknown")}
                        )
                        self._emit_alert(alert)
                        new_alerts.append(alert)
                elif total_liq >= THRESHOLDS["liquidation_surge_warning"]:
                    if not self._check_cooldown(symbol, ALERT_LIQUIDATION_SURGE):
                        alert = self._create_alert(
                            ALERT_LIQUIDATION_SURGE, SEVERITY_WARNING, symbol,
                            f"{symbol} liquidation surge: ${total_liq:,.0f}",
                            total_liq, THRESHOLDS["liquidation_surge_warning"]
                        )
                        self._emit_alert(alert)
                        new_alerts.append(alert)

        except Exception as e:
            logger.debug(f"Liquidation alert scan error: {e}")

        return new_alerts

    def scan_volume_anomalies(self) -> List[Dict]:
        """Scan for volume anomaly alerts using 24h ticker."""
        new_alerts = []
        if not self.market_data or not hasattr(self.market_data, "get_ticker_24h"):
            return new_alerts

        try:
            tickers = self.market_data.get_ticker_24h()
            if not tickers:
                return new_alerts

            volumes = {}
            for ticker in tickers:
                symbol = ticker.get("symbol", "")
                if not symbol.endswith("USDT"):
                    continue
                try:
                    vol = float(ticker.get("quoteVolume", 0))
                    volumes[symbol] = vol
                except (ValueError, TypeError):
                    continue

            if not volumes:
                return new_alerts

            avg_vol = sum(volumes.values()) / len(volumes) if volumes else 0
            threshold_vol = avg_vol * THRESHOLDS["volume_anomaly_multiplier"]

            for symbol, vol in volumes.items():
                if vol >= threshold_vol and vol > 100000000:
                    if not self._check_cooldown(symbol, ALERT_VOLUME_ANOMALY):
                        multiplier = vol / avg_vol if avg_vol > 0 else 0
                        alert = self._create_alert(
                            ALERT_VOLUME_ANOMALY, SEVERITY_WARNING, symbol,
                            f"{symbol} volume {multiplier:.1f}x above average (${vol:,.0f})",
                            vol, threshold_vol,
                            {"multiplier": round(multiplier, 2)}
                        )
                        self._emit_alert(alert)
                        new_alerts.append(alert)

        except Exception as e:
            logger.debug(f"Volume anomaly scan error: {e}")

        return new_alerts

    def run_full_scan(self, funding_data=None, liq_data=None) -> List[Dict]:
        """Run all alert scans at once."""
        now = time.time()
        if now - self._last_scan < self._scan_interval:
            return []

        self._last_scan = now
        self._active_alerts = []

        results = []
        results.extend(self.scan_price_alerts())
        results.extend(self.scan_funding_alerts(funding_data))
        results.extend(self.scan_liquidation_alerts(liq_data))
        results.extend(self.scan_volume_anomalies())

        return results

    def get_recent_alerts(self, limit: int = 50, severity: Optional[str] = None,
                          alert_type: Optional[str] = None) -> List[Dict]:
        """Get recent alerts with optional filters."""
        filtered = self._alerts.copy()

        if severity:
            filtered = [a for a in filtered if a.get("severity") == severity]
        if alert_type:
            filtered = [a for a in filtered if a.get("type") == alert_type]

        filtered.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        return filtered[:limit]

    def get_alert_stats(self) -> Dict:
        """Get alert statistics."""
        now = time.time()
        last_hour = [a for a in self._alerts if now - a.get("timestamp", 0) < 3600]
        last_24h = [a for a in self._alerts if now - a.get("timestamp", 0) < 86400]

        critical_count = len([a for a in last_24h if a.get("severity") == SEVERITY_CRITICAL])
        warning_count = len([a for a in last_24h if a.get("severity") == SEVERITY_WARNING])

        return {
            "total_alerts": len(self._alerts),
            "last_hour": len(last_hour),
            "last_24h": len(last_24h),
            "critical_24h": critical_count,
            "warning_24h": warning_count,
            "active_cooldowns": len(self._cooldowns),
        }

    def get_alert_summary(self) -> Dict:
        """Complete alert summary for dashboard/API."""
        return {
            "alerts": self.get_recent_alerts(30),
            "stats": self.get_alert_stats(),
            "thresholds": THRESHOLDS,
            "timestamp": int(time.time()),
        }

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Mark an alert as acknowledged."""
        for alert in self._alerts:
            if alert.get("id") == alert_id:
                alert["acknowledged"] = True
                self._save_history()
                return True
        return False

    def clear_history(self):
        """Clear all alert history."""
        self._alerts = []
        self._save_history()


if __name__ == "__main__":
    ae = AlertEngine()
    print(f"Thresholds: {json.dumps(THRESHOLDS, indent=2)}")
    print(f"Alert history: {len(ae._alerts)} entries")
    print(f"Stats: {ae.get_alert_stats()}")
