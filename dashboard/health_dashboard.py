import time
from rich.console import Console
from modules.health_monitor import HealthMonitor
from modules.logger_stats import LoggerStats
from modules.snapshot_stats import SnapshotStats
from modules.upload_tracker import UploadTracker
from modules.volatility_index import VolatilityIndex
from modules.market_regime import MarketRegimeDetector

console = Console()


# ================================
# SYSTEM HEALTH DASHBOARD
# ================================

class HealthDashboard:

    def __init__(self):

        self.health = HealthMonitor()
        self.logger_stats = LoggerStats()
        self.snapshot_stats = SnapshotStats()
        self.upload_tracker = UploadTracker()
        self.vol_index = VolatilityIndex()
        self.regime = MarketRegimeDetector()

    # ================================
    # HEADER
    # ================================
    def _header(self, title):

        console.print(f"\n[cyan]{'─' * 30}[/cyan]")
        console.print(f"[bold cyan]{title}[/bold cyan]")
        console.print(f"[cyan]{'─' * 30}[/cyan]")

    # ================================
    # DATA FILES SECTION
    # ================================
    def show_data_files(self):

        self._header("DATA FILES")

        files = self.health.check_data_files()

        for name, info in files.items():
            color = "green" if info["status"] == "ok" else "red"
            console.print(f"  {name}: [{color}]{info['status']}[/{color}] ({info['size_kb']} KB)")

    # ================================
    # DATASET FOLDERS SECTION
    # ================================
    def show_dataset_folders(self):

        self._header("DATASET FOLDERS")

        folders = self.health.check_dataset_folders()

        for name, info in folders.items():
            color = "green" if info["status"] == "ok" else "red"
            console.print(f"  {name}: [{color}]{info['status']}[/{color}] ({info['count']} files)")

    # ================================
    # SNAPSHOT SECTION
    # ================================
    def show_snapshot(self):

        self._header("SNAPSHOT STATUS")

        last = self.health.last_snapshot_time()
        eta = self.snapshot_stats.next_snapshot_eta()

        console.print(f"  Last Snapshot : [yellow]{last or 'never'}[/yellow]")
        console.print(f"  Next ETA      : [cyan]{eta}[/cyan]")

    # ================================
    # MARKET HEALTH SECTION
    # ================================
    def show_market_health(self):

        self._header("MARKET HEALTH")

        try:

            vol = self.vol_index.calculate()
            level = self.vol_index.level()
            regime = self.regime.market_regime().get("regime", "unknown")

            regime_color = "green" if regime == "bull" else "red" if regime == "bear" else "yellow"
            vol_color = "red" if level == "high" else "yellow" if level == "medium" else "green"

            console.print(f"  Regime          : [{regime_color}]{regime.upper()}[/{regime_color}]")
            console.print(f"  Volatility Index: {vol}")
            console.print(f"  Volatility Level: [{vol_color}]{level.upper()}[/{vol_color}]")

        except Exception as e:

            console.print(f"  [red]Market data unavailable: {e}[/red]")

    # ================================
    # FULL DASHBOARD
    # ================================
    def show(self):

        console.print(f"\n[bold cyan]{'═' * 30}[/bold cyan]")
        console.print(f"[bold cyan]  HANSEN AI — SYSTEM HEALTH[/bold cyan]")
        console.print(f"[bold cyan]{'═' * 30}[/bold cyan]")
        console.print(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")

        self.show_data_files()
        self.show_dataset_folders()
        self.show_snapshot()
        self.show_market_health()

        console.print(f"\n[bold cyan]{'═' * 30}[/bold cyan]\n")