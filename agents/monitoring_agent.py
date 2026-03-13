import time
from modules.health_monitor import HealthMonitor
from modules.logger_stats import LoggerStats
from modules.snapshot_stats import SnapshotStats
from modules.upload_tracker import UploadTracker
from modules.volatility_index import VolatilityIndex
from modules.market_regime import MarketRegimeDetector


# ================================
# MONITORING AGENT
# ================================

class MonitoringAgent:

    def __init__(self):

        self.health = HealthMonitor()
        self.logger_stats = LoggerStats()
        self.snapshot_stats = SnapshotStats()
        self.upload_tracker = UploadTracker()
        self.vol_index = VolatilityIndex()
        self.regime = MarketRegimeDetector()

    # ================================
    # SYSTEM STATUS
    # ================================
    def system_status(self):

        print("\n[MONITORING AGENT] System Status\n")

        self.health.report()
        self.logger_stats.report()
        self.snapshot_stats.report()
        self.upload_tracker.report()

    # ================================
    # MARKET STATUS
    # ================================
    def market_status(self):

        print("\n[MONITORING AGENT] Market Status\n")

        regime_info = self.regime.market_regime()
        vol = self.vol_index.calculate()
        vol_level = self.vol_index.level()

        print(f"Market Regime   : {regime_info.get('regime', 'unknown').upper()}")
        print(f"Volatility Index: {vol}")
        print(f"Volatility Level: {vol_level.upper()}")

        print("\nRegime Breakdown:")

        for coin, r in regime_info.get("breakdown", {}).items():
            print(f"  {coin}: {r}")

        print()

    # ================================
    # FULL REPORT
    # ================================
    def full_report(self):

        self.system_status()
        self.market_status()

    # ================================
    # WATCH LOOP
    # ================================
    def watch(self, interval=300):

        print("\n[MONITORING AGENT] Watch loop started\n")

        while True:

            try:

                self.full_report()

            except Exception as e:

                print(f"[MONITORING AGENT] Error: {e}")

            time.sleep(interval)

    # ================================
    # RUN AGENT
    # ================================
    def run(self):

        print("\n[MONITORING AGENT] Starting\n")

        self.full_report()