import time
from rich.console import Console
from rich.table import Table
from rich import print as rprint
from modules.market_regime import MarketRegimeDetector
from modules.momentum_engine import MomentumEngine
from modules.top_movers import TopMoversDetector
from modules.volatility_index import VolatilityIndex
from modules.market_intelligence import MarketIntelligence
from modules.insight_engine import InsightEngine

console = Console()


# ================================
# MARKET DASHBOARD
# ================================

class MarketDashboard:

    def __init__(self):

        self.regime = MarketRegimeDetector()
        self.momentum = MomentumEngine()
        self.movers = TopMoversDetector()
        self.vol_index = VolatilityIndex()
        self.intel = MarketIntelligence()
        self.insight = InsightEngine()

    # ================================
    # HEADER
    # ================================
    def _header(self, title):

        console.print(f"\n[cyan]{'─' * 30}[/cyan]")
        console.print(f"[bold cyan]{title}[/bold cyan]")
        console.print(f"[cyan]{'─' * 30}[/cyan]")

    # ================================
    # REGIME SECTION
    # ================================
    def show_regime(self):

        self._header("MARKET REGIME")

        info = self.regime.market_regime()
        regime = info.get("regime", "unknown").upper()

        color = "green" if regime == "BULL" else "red" if regime == "BEAR" else "yellow"

        console.print(f"Overall : [{color}]{regime}[/{color}]\n")

        for coin, r in info.get("breakdown", {}).items():
            color = "green" if r == "bull" else "red" if r == "bear" else "yellow"
            console.print(f"  {coin}: [{color}]{r}[/{color}]")

    # ================================
    # VOLATILITY SECTION
    # ================================
    def show_volatility(self):

        self._header("VOLATILITY INDEX")

        index = self.vol_index.calculate()
        level = self.vol_index.level()

        color = "red" if level == "high" else "yellow" if level == "medium" else "green"

        console.print(f"Index : {index}")
        console.print(f"Level : [{color}]{level.upper()}[/{color}]")

    # ================================
    # MOMENTUM SECTION
    # ================================
    def show_momentum(self):

        self._header("TOP GAINERS")

        gainers = self.momentum.top_gainers(5)

        for g in gainers:
            console.print(f"  {g['symbol']} : [green]+{g['momentum']}%[/green]")

        self._header("TOP LOSERS")

        losers = self.momentum.top_losers(5)

        for l in losers:
            console.print(f"  {l['symbol']} : [red]{l['momentum']}%[/red]")

    # ================================
    # MARKET SUMMARY SECTION
    # ================================
    def show_summary(self):

        self._header("MARKET SUMMARY")

        summary = self.intel.market_summary()

        for coin, data in summary.items():

            vol = data.get("volatility_1h")
            mom = data.get("momentum_1h")

            mom_color = "green" if mom and mom > 0 else "red"

            console.print(f"[bold]{coin}[/bold]")
            console.print(f"  volatility : {vol}%")
            console.print(f"  momentum   : [{mom_color}]{mom}%[/{mom_color}]\n")

    # ================================
    # INSIGHT SECTION
    # ================================
    def show_insight(self):

        self._header("MARKET INSIGHT")

        insights = self.insight.analyze_market()

        for item in insights:
            console.print(f"[yellow]- {item}[/yellow]")

    # ================================
    # FULL DASHBOARD
    # ================================
    def show(self):

        console.print(f"\n[bold cyan]{'═' * 30}[/bold cyan]")
        console.print(f"[bold cyan]  HANSEN AI — MARKET DASHBOARD[/bold cyan]")
        console.print(f"[bold cyan]{'═' * 30}[/bold cyan]")
        console.print(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")

        self.show_regime()
        self.show_volatility()
        self.show_momentum()
        self.show_summary()
        self.show_insight()

        console.print(f"\n[bold cyan]{'═' * 30}[/bold cyan]\n")