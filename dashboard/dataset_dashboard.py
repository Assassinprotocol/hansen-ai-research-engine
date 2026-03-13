import time
from rich.console import Console
from modules.snapshot_stats import SnapshotStats
from modules.logger_stats import LoggerStats
from modules.upload_tracker import UploadTracker

console = Console()


# ================================
# DATASET DASHBOARD
# ================================

class DatasetDashboard:

    def __init__(self):

        self.snapshot_stats = SnapshotStats()
        self.logger_stats = LoggerStats()
        self.upload_tracker = UploadTracker()

    # ================================
    # HEADER
    # ================================
    def _header(self, title):

        console.print(f"\n[cyan]{'─' * 30}[/cyan]")
        console.print(f"[bold cyan]{title}[/bold cyan]")
        console.print(f"[cyan]{'─' * 30}[/cyan]")

    # ================================
    # LOGGER SECTION
    # ================================
    def show_logger(self):

        self._header("LOGGER STATISTICS")

        console.print(f"Total Records   : [green]{self.logger_stats.total_records()}[/green]")
        console.print(f"Unique Symbols  : [cyan]{self.logger_stats.unique_symbols()}[/cyan]")
        console.print(f"Oldest Record   : {self.logger_stats.oldest_record() or 'unknown'}")

    # ================================
    # SNAPSHOT SECTION
    # ================================
    def show_snapshots(self):

        self._header("SNAPSHOT STATISTICS")

        pending = self.snapshot_stats.count_pending()
        failed = self.snapshot_stats.count_failed()
        eta = self.snapshot_stats.next_snapshot_eta()

        console.print(f"Pending         : [yellow]{pending}[/yellow]")
        console.print(f"Failed          : [red]{failed}[/red]")
        console.print(f"Next ETA        : [cyan]{eta}[/cyan]")

        sizes = self.snapshot_stats.snapshot_sizes()

        if sizes:

            console.print("\nPending Files:")

            for s in sizes[:5]:
                console.print(f"  [yellow]{s['file']}[/yellow]: {s['size_kb']} KB")

    # ================================
    # UPLOAD SECTION
    # ================================
    def show_uploads(self):

        self._header("UPLOAD TRACKER")

        console.print(f"Total Uploaded  : [green]{self.upload_tracker.total_uploads()}[/green]")
        console.print(f"Total Failed    : [red]{self.upload_tracker.total_failed()}[/red]")

        recent = self.upload_tracker.recent(5)

        if recent:

            console.print("\nRecent:")

            for item in recent:

                ts = time.strftime(
                    "%Y-%m-%d %H:%M",
                    time.localtime(item.get("timestamp", 0))
                )

                color = "green" if item["status"] == "success" else "red"

                console.print(f"  {ts} | [{color}]{item['status']}[/{color}] | {item['filename']}")

    # ================================
    # FULL DASHBOARD
    # ================================
    def show(self):

        console.print(f"\n[bold cyan]{'═' * 30}[/bold cyan]")
        console.print(f"[bold cyan]  HANSEN AI — DATASET DASHBOARD[/bold cyan]")
        console.print(f"[bold cyan]{'═' * 30}[/bold cyan]")
        console.print(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")

        self.show_logger()
        self.show_snapshots()
        self.show_uploads()

        console.print(f"\n[bold cyan]{'═' * 30}[/bold cyan]\n")