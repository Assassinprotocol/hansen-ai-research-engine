import json
import os
import time
import threading
import requests
import hashlib

from config import (
    METRICS_FILE_PATH,
    SYSTEM_NAME,
    SYSTEM_VERSION,
    SYSTEM_STAGE,
    LLM_PROVIDER
)

from memory.state import MemoryManager, STATE_FILE
from modules.research import ResearchModule
from core.logger import SystemLogger
from core.profile import ProfileAnalyzer
from core.insight import InsightAnalyzer
from core.memory.conversation import ConversationMemory
from core.memory.user_profile import UserProfile
from router.router import IntentRouter
from rag.retriever import Retriever
from rag.ingest import DocumentIngestor
from modules.market_data import MarketData
from modules.scheduler import Scheduler
from modules.data_adapter import DataAdapter
from modules.data_index import DataIndex
from modules.insight_engine import InsightEngine
from modules.volatility import VolatilityDetector
from modules.market_storage import MarketStorage
from modules.market_intelligence import MarketIntelligence, SECTOR_MAP
from modules.market_history import MarketHistory
from modules.market_regime import MarketRegimeDetector
from modules.momentum_engine import MomentumEngine
from modules.top_movers import TopMoversDetector
from modules.health_monitor import HealthMonitor
from modules.logger_stats import LoggerStats
from modules.snapshot_stats import SnapshotStats
from modules.upload_tracker import UploadTracker
from modules.snapshot_metadata import SnapshotMetadata
from modules.regime_tagger import RegimeTagger
from modules.volatility_index import VolatilityIndex
from modules.movers_metadata import MoversMetadata
from modules.sector_performance import SectorPerformance
from modules.correlation_matrix import CorrelationMatrix
from modules.alert_engine import AlertEngine
from modules.market_heatmap import MarketHeatmap
from modules.smart_screener import SmartScreener
from modules.sentiment_engine import SentimentEngine
from modules.onchain_intel import OnchainIntel
from modules.ai_reports import AIReports
from modules.market_brain import MarketBrain
from modules.derivatives_collector import get_derivatives_data, start_derivatives_collector
from agents.research_agent import ResearchAgent
from agents.dataset_agent import DatasetAgent
from agents.monitoring_agent import MonitoringAgent
from dashboard.market_dashboard import MarketDashboard
from dashboard.dataset_dashboard import DatasetDashboard
from dashboard.health_dashboard import HealthDashboard
from pipeline.training_pipeline import TrainingPipeline
from pipeline.insight_improver import InsightImprover
from pipeline.research_loop import ResearchLoop

from rich import print


MAX_INPUT_LENGTH = 1000


class HansenEngine:

    def __init__(self):
        self.research_module = ResearchModule()
        self.memory = MemoryManager()
        self.last_topic = None
        self.logger = SystemLogger()
        self.profile_analyzer = ProfileAnalyzer()
        self.insight_analyzer = InsightAnalyzer()
        self.volatility = VolatilityDetector()

        # ---- INTENT ROUTER ----
        self.router = IntentRouter()

        # ---- CONVERSATION MEMORY ----
        self.conversation_memory = ConversationMemory()

        # ---- USER PROFILE ----
        self.user_profile = UserProfile()

        # ---- EXECUTION MODE ----
        self.mode = "strict"

        # ---- RAG SYSTEM ----
        self.retriever = Retriever()
        self.ingestor = DocumentIngestor()
        self.market = MarketData()
        self.scheduler = Scheduler()
        self.adapter = DataAdapter()
        self.index = DataIndex()
        self.insight_engine = InsightEngine()
        self.market_storage = MarketStorage()
        self.market_intel = MarketIntelligence()
        self.regime_detector = MarketRegimeDetector()
        self.momentum_engine = MomentumEngine()
        self.top_movers = TopMoversDetector()
        self.health_monitor = HealthMonitor()
        self.logger_stats = LoggerStats()
        self.snapshot_stats = SnapshotStats()
        self.upload_tracker = UploadTracker()
        self.snapshot_metadata = SnapshotMetadata()
        self.regime_tagger = RegimeTagger()
        self.volatility_index = VolatilityIndex()
        self.movers_metadata = MoversMetadata()
        self.research_agent = ResearchAgent()
        self.dataset_agent = DatasetAgent()
        self.monitoring_agent = MonitoringAgent()
        self.market_dashboard = MarketDashboard()
        self.dataset_dashboard = DatasetDashboard()
        self.health_dashboard = HealthDashboard()
        self.training_pipeline = TrainingPipeline()
        self.insight_improver = InsightImprover()
        self.research_loop = ResearchLoop()
        self.market_history = MarketHistory()
        self.sector_performance = SectorPerformance(market_store=None, market_data=self.market)
        self.correlation_matrix = CorrelationMatrix(market_store=None, market_data=self.market)
        self.alert_engine = AlertEngine(market_data=self.market)
        self.market_heatmap = MarketHeatmap(market_data=self.market)
        self.smart_screener = SmartScreener(market_data=self.market)
        self.sentiment_engine = SentimentEngine(market_data=self.market)
        self.onchain_intel = OnchainIntel(market_data=self.market)
        self.ai_reports = AIReports(market_data=self.market, sector_perf=self.sector_performance, sentiment=self.sentiment_engine, alert_engine=self.alert_engine, onchain=self.onchain_intel, screener=self.smart_screener)
        self.market_brain = MarketBrain(market_data=self.market, sector_perf=self.sector_performance, correlation=self.correlation_matrix, alert_engine=self.alert_engine, sentiment=self.sentiment_engine, onchain=self.onchain_intel, screener=self.smart_screener, regime_detector=self.regime_detector, momentum_engine=self.momentum_engine, volatility_index=self.volatility_index)
        self.ai_reports.market_brain = self.market_brain
        start_derivatives_collector()
        self.market_brain.modules["derivatives_fn"] = get_derivatives_data

        # ---- PERSISTENT METRICS ----
        try:
            if os.path.exists(METRICS_FILE_PATH):
                with open(METRICS_FILE_PATH, "r") as f:
                    self.metrics = json.load(f)
            else:
                raise FileNotFoundError

        except (json.JSONDecodeError, FileNotFoundError):

            self.metrics = {
                "sessions": 0,
                "research_calls": 0,
                "invalid_inputs": 0
            }

            with open(METRICS_FILE_PATH, "w") as f:
                json.dump(self.metrics, f, indent=4)

    # =============================
    # ERROR CLASSIFICATION
    # =============================
    ERROR_TYPES = {
        "INPUT": "INPUT_ERROR",
        "PROCESS": "PROCESS_ERROR",
        "SYSTEM": "SYSTEM_ERROR",
        "CHAT": "CHAT_ERROR"
    }

    # =============================
    # INPUT VALIDATION
    # =============================
    def validate_input(self, user_input: str):
        cleaned = user_input.strip()

        if not cleaned:
            return False, "⚠ Invalid input. Please enter a topic."

        if len(cleaned) > MAX_INPUT_LENGTH:
            return False, f"⚠ Input too long. Limit is {MAX_INPUT_LENGTH} characters."

        if not any(c.isalnum() for c in cleaned):
            return False, "⚠ Input must contain letters or numbers."

        return True, cleaned

    # =============================
    # SAVE METRICS (ATOMIC)
    # =============================
    def _save_metrics(self):

        temp_file = f"{METRICS_FILE_PATH}.tmp"

        with open(temp_file, "w") as f:
            json.dump(self.metrics, f, indent=4)
            f.flush()
            os.fsync(f.fileno())

        os.replace(temp_file, METRICS_FILE_PATH)

    # =============================
    # SET EXECUTION MODE
    # =============================
    def set_mode(self, mode: str):

        allowed_modes = ["strict", "experimental", "hybrid"]

        if mode not in allowed_modes:
            print(f"[red]Invalid mode.[/red] Allowed: {allowed_modes}")
            return

        self.mode = mode
        print(f"[green]Mode set to:[/green] {self.mode}")

    # =============================
    # AUTO TAG RESEARCH TOPIC
    # =============================
    def _auto_tag(self, topic: str):

        topic_lower = topic.lower()

        crypto_keywords = ["btc", "bitcoin", "eth", "crypto", "altcoin"]
        macro_keywords = ["inflation", "rates", "fed", "macro", "cpi"]
        equity_keywords = ["nasdaq", "sp500", "stocks", "equity"]

        if any(word in topic_lower for word in crypto_keywords):
            return "crypto"

        if any(word in topic_lower for word in macro_keywords):
            return "macro"

        if any(word in topic_lower for word in equity_keywords):
            return "equity"

        return "general"

    # =============================
    # TAG DISTRIBUTION ANALYTICS
    # =============================
    def _get_tag_distribution(self):

        from collections import Counter

        tag_counter = Counter()

        for topic_entries in self.memory._load_all_topics().values():
            for entry in topic_entries:
                if isinstance(entry, dict):
                    tag = entry.get("tag", "general")
                    tag_counter[tag] += 1

        return tag_counter

    # =============================
    # RUN RESEARCH (CLI MODE)
    # =============================
    def run_research(self, topic: str):

        try:

            start_time = time.time()

            # ---- INPUT VALIDATION ----
            is_valid, value = self.validate_input(topic)

            if not is_valid:
                self.metrics["invalid_inputs"] += 1
                self._save_metrics()
                self.logger.warn(
                    f"[{self.ERROR_TYPES['INPUT']}] INVALID_INPUT",
                    self.mode
                )
                print(f"[red]{value}[/red]")
                return

            topic = value

            # ---- METRICS ----
            self.metrics["research_calls"] += 1
            self._save_metrics()

            # ---- AUTO TAG ----
            tag = self._auto_tag(topic)

            # ---- CONTEXT CHECK ----
            previous = self.memory.get_topic_history(topic)

            if previous:
                print(f"[yellow]⚠ Previously researched {len(previous)} times.[/yellow]")
                print(
                    f"[yellow]Last discussed at: "
                    f"{previous[-1].get('timestamp', 'OLD_DATA')}[/yellow]\n"
                )

            print(f"[cyan]Researching:[/cyan] {topic}")

            # ---- PROCESS ----
            try:
                result = self.research_module.process(
                    topic,
                    self.router.route
                )

            except Exception as research_error:

                execution_time_ms = (time.time() - start_time) * 1000

                self.logger.error(
                    f"[{self.ERROR_TYPES['PROCESS']}] "
                    f"RESEARCH_PROCESS_ERROR: {str(research_error)}",
                    self.mode
                )

                self.logger.log_execution(
                    provider=LLM_PROVIDER,
                    intent="research",
                    prompt_length=len(topic),
                    status="error",
                    execution_time_ms=execution_time_ms
                )

                print("[red]Research module failed safely.[/red]")
                return

            # ---- SUCCESS TIMING ----
            execution_time_ms = (time.time() - start_time) * 1000

            print(result)
            print(f"[magenta]Tag:[/magenta] {tag}")

            self.logger.log_execution(
                provider=LLM_PROVIDER,
                intent="research",
                prompt_length=len(topic),
                status="success",
                execution_time_ms=execution_time_ms
            )

            # ---- MODE EFFECT ----
            if self.mode == "experimental":
                print("[yellow]⚙ Experimental mode active[/yellow]")
                print(f"[yellow]Topic Length:[/yellow] {len(topic)} characters")

            elif self.mode == "hybrid":
                print("[cyan]🔀 Hybrid mode summary[/cyan]")
                print(f"[cyan]Tag Category:[/cyan] {tag}")

            # ---- SAVE ----
            self.memory.save_research(
                topic,
                {
                    "result": result,
                    "tag": tag
                }
            )

            self.logger.info(
                f"RESEARCH: {topic}",
                self.mode
            )

            # ---- PROFILE ----
            profile = self.profile_analyzer.detect_user_profile(
                self.memory.get_full_history()
            )

            if profile:
                self.logger.info(
                    f"PROFILE_DETECTED: {profile}",
                    self.mode
                )

            if profile == "High":
                print("[yellow]⚠ Pattern detected: You tend to focus on high-risk assets.[/yellow]")
            elif profile == "Medium":
                print("[cyan]Balanced risk research behavior detected.[/cyan]")
            elif profile == "Variable":
                print("[green]Flexible research pattern detected.[/green]")

            print("[green]Saved to memory.[/green]")

        except Exception as system_error:
            self.logger.error(
                f"[{self.ERROR_TYPES['SYSTEM']}] "
                f"RUN_RESEARCH_FATAL: {str(system_error)}",
                self.mode
            )
            print(f"[red]Unexpected system error:[/red] {system_error}")

    # =============================
    # CHAT MODE
    # =============================
    def chat_mode(self):
        print("[green]Hansen AI Chat Mode (type 'exit' to quit)[/green]\n")

        while True:
            user_input = input("You: ")

            if user_input.lower().strip() in ["exit", "quit"]:
                print("[red]Exiting chat mode...[/red]")
                break

            # ---- INPUT VALIDATION ----
            is_valid, value = self.validate_input(user_input)

            if not is_valid:
                self.logger.warn(
                    f"[{self.ERROR_TYPES['INPUT']}] INVALID_INPUT_CHAT",
                    self.mode
                )
                print(f"[red]{value}[/red]\n")
                continue

            user_input = value

            # ---- CONTEXT RESOLUTION ----
            resolved_topic = user_input
            follow_up_keywords = ["and", "what about", "how about", "it"]

            if any(user_input.lower().startswith(k) for k in follow_up_keywords) and self.last_topic:
                resolved_topic = self.last_topic
                print(f"[cyan]↳ Using previous context: {self.last_topic}[/cyan]")

            # ---- MEMORY CONTEXT ----
            previous = self.memory.get_topic_history(resolved_topic)

            if previous:
                print(f"[yellow]⚠ Previously discussed {len(previous)} times.[/yellow]")
                print(f"[yellow]Last discussed at: {previous[-1].get('timestamp', 'OLD_DATA')}[/yellow]")

            # ---- PROCESS (CRASH ISOLATED) ----
            try:
                result = self.research_module.process(
                    resolved_topic,
                    self.router.route
                )
                print(f"Hansen: {result}\n")

            except Exception as chat_error:

                self.logger.error(
                    f"[{self.ERROR_TYPES['CHAT']}] "
                    f"CHAT_PROCESS_ERROR: {str(chat_error)}",
                    self.mode
                )

                print("[red]Chat processing failed safely.[/red]\n")
                continue

            # ---- SAVE + LOG ----
            self.memory.save_research(resolved_topic, result)

            self.logger.info(
                f"CHAT_RESEARCH: {resolved_topic}",
                self.mode
            )

            # ---- UPDATE SESSION ----
            self.last_topic = resolved_topic


    # =============================
    # SINGLE MESSAGE CHAT (LLM MODE)
    # =============================
    def run_chat(self, message: str):

        try:

            # ---- SIMPLE USER NAME DETECTION ----
            lowered = message.lower().strip()

            if lowered.startswith("nama saya "):
                name = message.strip()[10:].strip()
                if name:
                    self.user_profile.set_attribute("name", name)
                    response = f"Baik, {name}. Saya akan mengingat itu."
                    self.conversation_memory.add("user", message)
                    self.conversation_memory.add("assistant", response)
                    return response

            # ---- DIRECT NAME QUERY HANDLING ----
            if lowered in ["siapa nama saya?", "nama saya siapa?"]:
                stored_name = self.user_profile.get_attribute("name")
                if stored_name:
                    response = f"Nama kamu {stored_name}."
                else:
                    response = "Saya belum mengetahui nama kamu."

                self.conversation_memory.add("user", message)
                self.conversation_memory.add("assistant", response)
                return response

            # ---- LOAD HISTORY ----
            history_context = self.conversation_memory.get_formatted_history()

            # ---- LOAD USER PROFILE ----
            profile_context = self.user_profile.get_formatted_profile()

            # ---- MERGE CONTEXT ----
            merged_context = ""

            if profile_context:
                merged_context += f"{profile_context}\n\n"

            if history_context:
                merged_context += f"{history_context}\n\n"

            # ---- GENERATE RESPONSE (ROUTED + CONTEXT) ----
            response = self.router.route(
                message,
                merged_context,
                mode=self.mode
            )

            # ---- SAVE TO MEMORY ----
            self.conversation_memory.add("user", message)
            self.conversation_memory.add("assistant", response)

            return response

        except Exception as e:

            self.logger.error(
                f"[{self.ERROR_TYPES['CHAT']}] "
                f"CHAT_PROCESS_ERROR: {str(e)}",
                self.mode
            )

            print(str(e))
            return "⚠ Chat processing failed safely."


    # =============================
    # STATUS
    # =============================
    def show_status(self):

        print(f"[green]{SYSTEM_NAME} v{SYSTEM_VERSION}[/green]")
        print(f"Stage: {SYSTEM_STAGE}")

        print("Mode: Terminal")
        print("Memory: Hardened")
        print("Input Guard: Active")
        print("Logging: Structured")

    # =============================
    # HEALTH CHECK
    # =============================
    def health_check(self, deep: bool = False):

        print(f"[cyan]{SYSTEM_NAME} Health Check[/cyan]\n")

        # ---- MEMORY CHECK ----
        try:
            data = self.memory._load_all_topics()
            print("Memory File      : OK")
        except Exception:
            print("Memory File      : ERROR")

        # ---- METRICS CHECK ----
        try:
            _ = self.metrics
            print("Metrics File     : OK")
        except Exception:
            print("Metrics File     : ERROR")

        print(f"Mode             : {self.mode}")

        # ---- LOGGER TEST ----
        try:
            self.logger.info("HEALTH_CHECK_OK", self.mode)
            print("Logging          : OK")
        except Exception:
            print("Logging          : ERROR")

        if deep:
            print("\n[magenta]Deep Integrity Scan[/magenta]")

            if os.path.exists(STATE_FILE):
                size = os.path.getsize(STATE_FILE)
                print(f"Memory Size      : {size} bytes")
            else:
                print("Memory Size      : FILE MISSING")

            if os.path.exists(METRICS_FILE_PATH):
                size = os.path.getsize(METRICS_FILE_PATH)
                print(f"Metrics Size     : {size} bytes")
            else:
                print("Metrics Size     : FILE MISSING")

        print()

    # =============================
    # HISTORY
    # =============================
    def show_history(self):
        history = self.memory.get_history()

        if not history:
            print("[red]No research history yet.[/red]")
            return

        for item in history:
            timestamp = item.get("timestamp", "OLD_DATA")
            print(f"[blue]{timestamp}[/blue] | {item['topic']}")

    # =============================
    # STATS
    # =============================
    def show_stats(self):

        stats = self.memory.get_topic_stats()

        if not stats:
            print("[red]No research data yet.[/red]")
        else:
            print("[cyan]Most researched topics:[/cyan]")

            for i, (topic, count) in enumerate(stats, 1):
                print(f"{i}. {topic} ({count} times)")

        # ---- INTERNAL METRICS ----
        print("\n[cyan]System Metrics:[/cyan]")
        print(f"Sessions        : {self.metrics['sessions']}")
        print(f"Research Calls  : {self.metrics['research_calls']}")
        print(f"Invalid Inputs  : {self.metrics['invalid_inputs']}")
        print()

        # ---- TAG DISTRIBUTION ----
        tag_distribution = self._get_tag_distribution()

        if tag_distribution:
            print("[cyan]Tag Distribution:[/cyan]")
            for tag, count in tag_distribution.items():
                print(f" - {tag}: {count}")
            print()

    # =============================
    # INSIGHT
    # =============================
    def generate_insight(self):
        history = self.memory.get_full_history()

        insight = self.insight_analyzer.generate_insight(history)

        if not insight:
            print("[red]No data available for insight.[/red]")
            return

        most_topic = insight["most_topic"]
        count = insight["count"]

        print("[cyan]Research Insight:[/cyan]\n")
        print(f"- Most researched topic: {most_topic} ({count} times)")

    # =============================
    # AGENT EXECUTION
    # =============================
    def run_agent(self, task: str):

        import subprocess
        import os

        try:

            agent_dir = r"C:\AI\hansen_ai"

            command = [
                r"C:\AI\hansen_ai\venv\Scripts\python.exe",
                "main.py",
                "agent",
                task
            ]

            print(f"[cyan]Launching Hansen Agent...[/cyan]")
            print(f"[yellow]Task:[/yellow] {task}")

            subprocess.run(
                command,
                cwd=agent_dir
            )

        except Exception as e:

            self.logger.error(
                f"[SYSTEM_ERROR] AGENT_EXECUTION_FAILED: {str(e)}",
                self.mode
            )

            print("[red]Agent execution failed.[/red]")

    # =============================
    # AUTO TASK ROUTER
    # =============================
    def route_task(self, message: str):

        text = message.lower()


        # -----------------------
        # PRICE REQUEST
        # -----------------------

        price_keywords = ["price", "harga"]

        coins = ["btc", "eth", "sol", "bnb"]

        for coin in coins:

            if coin in text and any(k in text for k in price_keywords):

                print("[cyan]Task detected: MARKET PRICE[/cyan]")

                self.market_price(coin)

                return


        # -----------------------
        # VOLATILITY REQUEST
        # -----------------------

        if "volatility" in text:

            for coin in coins:

                if coin in text:

                    symbol = coin.upper() + "USDT"

                    value = self.volatility.calculate(symbol)

                    print(f"{symbol} volatility: {value}%")

                    return


        # -----------------------
        # MARKET INSIGHT
        # -----------------------

        insight_keywords = ["market", "trend", "condition"]

        if any(k in text for k in insight_keywords):

            insights = self.insight_engine.analyze_market()

            print("\nMarket Insight\n")

            for item in insights:

                print(f"- {item}")

            print()

            return


        # -----------------------
        # AGENT REQUEST
        # -----------------------

        if text.startswith("agent"):

            task = text.replace("agent", "").strip()

            if not task:

                print("Agent task required")

                return

            print("[cyan]Task detected: AGENT[/cyan]")

            self.run_agent(task)

            return


        # -----------------------
        # DEFAULT CHAT
        # -----------------------

        print("[cyan]Task detected: CHAT[/cyan]")

        response = self.run_chat(message)

        print(response)

    # =============================
    # RAG QUERY
    # =============================
    def knowledge(self, query):

        context = self.retriever.retrieve(query)

        if not context:
            print("No knowledge found.")
            return

        print("Knowledge Context:\n")
        print(context)

    # =============================
    # INGEST KNOWLEDGE FOLDER
    # =============================
    def ingest_knowledge(self):

        self.ingestor.ingest_folder()

    # =============================
    # MARKET PRICE
    # =============================
    def market_price(self, symbol="btc"):

        result = self.market.get_price(symbol)

        print(result)

    # =============================
    # MARKET LOGGER
    # =============================
    def market_logger(self, interval=300):

        import time

        print("[cyan]Market logger started...[/cyan]")

        while True:

            try:

                result = self.market.get_btc_price()

                print(result)

            except Exception as e:

                self.logger.error(
                    f"[SYSTEM_ERROR] MARKET_LOGGER_FAILED: {str(e)}",
                    self.mode
                )

            time.sleep(interval)

    # =============================
    # START DATA SCHEDULER
    # =============================
    def start_scheduler(self):

        self.scheduler.add_job(
            self.market_price,
            300
        )

        self.scheduler.run()

    # =============================
    # READ DATA SOURCE
    # =============================
    def read_data(self, path):

        data = self.adapter.read_folder(path)

        print(data)

    # =============================
    # DATA INDEX
    # =============================
    def build_index(self, folder):

        index = self.index.index_folder(folder)

        print(index)

    # =============================
    # MARKET INSIGHT
    # =============================
    def market_insight(self):

        result = self.insight_engine.analyze_market()

        print(result)

    # =============================
    # MARKET VOLATILITY
    # =============================
    def market_volatility(self, symbol="BTC"):

        try:

            value = self.volatility.calculate(symbol)

            print(f"{symbol} volatility: {value}%")

        except Exception as e:

            print("Volatility error:", e)

    # =============================
    # BACKGROUND MARKET LOGGER
    # =============================
    def start_market_logger(self):

        data_dir = r"C:\AI\hansen_engine\data"
        data_file = os.path.join(data_dir, "market_history.json")

        dataset_dir = r"C:\AI\hansen_engine\dataset"
        dataset_pending = os.path.join(dataset_dir, "pending")

        snapshot_interval = 14400
        snapshot_state_file = r"C:\AI\hansen_engine\data\snapshot_state.json"

        if os.path.exists(snapshot_state_file):
            try:
                with open(snapshot_state_file, "r") as f:
                    state = json.load(f)
                last_snapshot = state.get("last_snapshot", 0)
            except:
                last_snapshot = 0
        else:
            last_snapshot = 0

        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(dataset_pending, exist_ok=True)

        if not os.path.exists(data_file):

            with open(data_file, "w") as f:
                json.dump([], f)

        def logger_loop():

            nonlocal last_snapshot

            while True:

                try:

                    # =============================
                    # SAFE MARKET FETCH
                    # =============================

                    data = []

                    try:
                        data = self.market.get_all_prices()
                    except:
                        print("[LOGGER] market API failed")

                    records = []

                    timestamp = time.time()

                    for item in data:

                        try:

                            symbol = item.get("symbol")

                            if not symbol or not symbol.endswith("USDT"):
                                continue

                            price = float(item.get("price"))

                            record = {
                                "timestamp": timestamp,
                                "symbol": symbol,
                                "price": price
                            }

                            records.append(record)

                        except:
                            continue

                    if not records:

                        print("[LOGGER] no records received")

                        time.sleep(300)
                        continue


                    # =============================
                    # LOAD HISTORY
                    # =============================

                    try:

                        with open(data_file, "r") as f:
                            history = json.load(f)

                        if not isinstance(history, list):
                            history = []

                        # LIMIT HISTORY READ
                        if len(history) > 200000:
                            history = history[-200000:]

                    except:

                        history = []


                    # =============================
                    # FILTER OLD DATA (90 DAYS)
                    # =============================

                    cutoff = time.time() - (90 * 24 * 60 * 60)

                    filtered = []

                    for h in history:

                        try:

                            ts = h.get("timestamp")

                            if isinstance(ts, (int, float)):

                                if ts >= cutoff:
                                    filtered.append(h)

                            elif isinstance(ts, str):

                                ts_epoch = time.mktime(
                                    time.strptime(ts, "%Y-%m-%dT%H:%M:%S")
                                )

                                if ts_epoch >= cutoff:
                                    filtered.append(h)

                        except:
                            continue

                    history = filtered


                    # =============================
                    # APPEND NEW RECORDS
                    # =============================

                    history.extend(records)


                    # =============================
                    # LIMIT HISTORY SIZE
                    # =============================

                    if len(history) > 1000000:
                        history = history[-1000000:]


                    # =============================
                    # SAVE UPDATED HISTORY
                    # =============================
                    try:
                        temp_file = data_file + ".tmp"
                        with open(temp_file, "w") as f:
                            json.dump(history, f, separators=(",", ":"))
                            f.flush()
                            os.fsync(f.fileno())
                        for _attempt in range(5):
                            try:
                                os.replace(temp_file, data_file)
                                break
                            except PermissionError:
                                time.sleep(1)
                    except Exception as e:
                        print("[LOGGER] history save failed:", e)

                    print(f"[LOGGER] collected {len(records)} records")


                    # =============================
                    # WRITE DASHBOARD CACHE
                    # =============================
                    try:
                        cutoff_1h = time.time() - 3600
                        recent = [r for r in history if isinstance(r.get("timestamp"), (int, float)) and r["timestamp"] >= cutoff_1h]
                        dashboard_file = os.path.join(data_dir, "dashboard_cache.json")
                        with open(dashboard_file, "w") as f:
                            json.dump(recent, f, separators=(",", ":"))
                    except:
                        pass


                    # =============================
                    # MARKET STORAGE (TEMP DISABLED)
                    # =============================

                    # Disabled to avoid blocking logger thread
                    # try:
                    #     self.market_storage.append(records)
                    # except:
                    #     pass


                    # =============================
                    # SNAPSHOT CREATION
                    # =============================
                    now = time.time()

                    if now - last_snapshot >= snapshot_interval:

                        snapshot_name = f"snapshot_{time.strftime('%Y%m%d_%H%M%S')}.json"

                        snapshot_path = os.path.join(dataset_pending, snapshot_name)

                        try:

                            snapshot_data = history[-30000:]

                            # ENRICH SNAPSHOT
                            try:
                                snapshot_data = self.regime_tagger.tag_snapshot(snapshot_data)
                            except:
                                pass

                            # ATTACH METADATA
                            regime_info = {}
                            vol_report  = {}
                            insights    = []
                            meta        = {}

                            try:
                                meta = self.snapshot_metadata.generate(snapshot_data, snapshot_name)
                                meta = self.movers_metadata.attach(meta)
                                vol_report = self.volatility_index.report()
                                meta["volatility_index"] = vol_report
                                insights = self.insight_engine.analyze_market()
                                meta["market_insight"] = insights
                                regime_info = self.regime_detector.market_regime()
                                meta["market_regime"] = regime_info
                                self.snapshot_metadata.save(snapshot_data, snapshot_name)
                            except:
                                pass

                            # ENRICH WITH MARKET BRAIN
                            brain_context = {}
                            try:
                                brain_context = self.market_brain.collect_full_context()
                            except:
                                pass

                            # ENRICH WITH DERIVATIVES
                            deriv_data = {}
                            try:
                                from modules.derivatives_collector import get_derivatives_data
                                deriv_data = get_derivatives_data() or {}
                            except:
                                pass

                            final_snapshot = {
                                "records": snapshot_data,
                                "market_regime": regime_info,
                                "volatility": vol_report,
                                "market_insight": insights,
                                "top_gainers": meta.get("top_gainers", []),
                                "top_losers": meta.get("top_losers", []),
                                "top_movers": meta.get("top_movers", []),
                                "generated_at": time.strftime('%Y-%m-%dT%H:%M:%S'),
                                "total_records": len(snapshot_data),
                                "unique_symbols": meta.get("unique_symbols", 0),
                                "sector_performance": brain_context.get("sectors", {}),
                                "sector_rotation": brain_context.get("sector_rotation", {}),
                                "sentiment": brain_context.get("sentiment", {}),
                                "active_narratives": brain_context.get("active_narratives", []),
                                "alerts_summary": brain_context.get("alerts", {}),
                                "whale_activity": brain_context.get("whale_activity", {}),
                                "exchange_flow": brain_context.get("exchange_flow", {}),
                                "stablecoin": brain_context.get("stablecoin", {}),
                                "opportunities": brain_context.get("opportunities", {}),
                                "correlation": brain_context.get("correlation", {}),
                                "derivatives": {
                                    "funding_summary": deriv_data.get("funding_summary", {}),
                                    "oi_summary": deriv_data.get("oi_summary", {}),
                                    "liq_summary": deriv_data.get("liq_summary", {}),
                                    "cascade_alert": deriv_data.get("cascade_alert", {}),
                                },
                                "brain_data_sources": brain_context.get("data_sources", []),
                                "brain_total_sources": brain_context.get("total_data_sources", 0),
                            }

                            with open(snapshot_path, "w") as f:
                                json.dump(final_snapshot, f, indent=2, default=str)

                            print(f"[SNAPSHOT] created {snapshot_name}")

                            # =============================
                            # AI LEARNING FROM SNAPSHOT
                            # =============================
                            try:
                                brain_prompt = self.market_brain.get_reasoning_prompt(
                                    question="Analyze this snapshot. What is the current market condition? What patterns do you see? What should be watched?"
                                )

                                import requests as req
                                llm_resp = req.post(
                                    "http://localhost:8080/completion",
                                    json={
                                        "prompt": brain_prompt,
                                        "n_predict": 512,
                                        "temperature": 0.7,
                                        "top_p": 0.9,
                                        "stop": ["\n\n\n"]
                                    },
                                    timeout=60
                                )

                                if llm_resp.status_code == 200:
                                    ai_analysis = llm_resp.json().get("content", "").strip()

                                    if ai_analysis:
                                        # Save AI analysis alongside snapshot
                                        analysis_name = snapshot_name.replace(".json", "_ai_analysis.json")
                                        analysis_path = os.path.join(dataset_pending, analysis_name)

                                        with open(analysis_path, "w") as f:
                                            json.dump({
                                                "snapshot": snapshot_name,
                                                "analysis": ai_analysis,
                                                "brain_sources": brain_context.get("data_sources", []),
                                                "sentiment_score": brain_context.get("sentiment", {}).get("score"),
                                                "generated_at": time.strftime('%Y-%m-%dT%H:%M:%S'),
                                            }, f, indent=2)

                                        # Also save to market insight for dashboard
                                        insight_file = os.path.join(data_dir, "latest_ai_insight.json")
                                        with open(insight_file, "w") as f:
                                            json.dump({
                                                "analysis": ai_analysis,
                                                "sentiment_score": brain_context.get("sentiment", {}).get("score"),
                                                "sentiment_level": brain_context.get("sentiment", {}).get("level"),
                                                "top_sectors": brain_context.get("sectors", {}).get("top_3", []),
                                                "narratives": [n.get("label") for n in brain_context.get("active_narratives", [])],
                                                "whale_signals": brain_context.get("whale_activity", {}).get("total_signals", 0),
                                                "alert_count": brain_context.get("alerts", {}).get("stats", {}).get("last_24h", 0),
                                                "generated_at": time.strftime('%Y-%m-%dT%H:%M:%S'),
                                            }, f, indent=2)

                                        print(f"[AI] analysis generated for {snapshot_name}")

                            except Exception as e:
                                print(f"[AI] learning failed: {e}")

                            with open(snapshot_state_file, "w") as f:
                                json.dump({"last_snapshot": now}, f)

                        except Exception as e:
                            print("[SNAPSHOT] failed:", e)

                        last_snapshot = now

                except Exception as e:

                    self.logger.error(
                        f"[SYSTEM_ERROR] LOGGER_FAILED: {str(e)}",
                        self.mode
                    )

                time.sleep(300)

        thread = threading.Thread(
            target=logger_loop,
            name="market_logger",
            daemon=True
        )

        thread.start()

        print("[LOGGER] background logger thread started")

    # =============================
    # ENGINE COMMAND LOOP
    # =============================
    def command_loop(self):

        print("Hansen Engine Running")
        print("Type command or 'exit'\n")

        while True:

            try:

                cmd = input("> ").strip()

                if cmd == "exit":

                    print("Shutting down engine...")
                    break


                # -----------------------
                # VOLATILITY
                # -----------------------
                elif cmd.startswith("volatility"):

                    parts = cmd.split()

                    if len(parts) > 1:
                        symbol = parts[1]
                    else:
                        symbol = "BTC"

                    value = self.volatility.calculate(symbol)

                    print(f"{symbol.upper()} volatility: {value}%")


                # -----------------------
                # PRICE
                # -----------------------
                elif cmd.startswith("price"):

                    parts = cmd.split()

                    if len(parts) > 1:
                        self.market_price(parts[1])
                    else:
                        self.market_price("btc")


                # -----------------------
                # RESEARCH
                # -----------------------
                elif cmd.startswith("research"):

                    topic = cmd.replace("research", "").strip()

                    if topic:
                        self.run_research(topic)


                # -----------------------
                # CHAT
                # -----------------------
                elif cmd.startswith("chat"):

                    message = cmd.replace("chat", "").strip()

                    if message:

                        response = self.run_chat(message)

                        print(response)


                # -----------------------
                # AGENT
                # -----------------------
                elif cmd.startswith("agent"):

                    task = cmd.replace("agent", "").strip()

                    if task:

                        self.run_agent(task)


                # -----------------------
                # STATUS
                # -----------------------
                elif cmd == "status":

                    self.show_status()


                # -----------------------
                # EDIT FILE
                # -----------------------
                elif cmd.startswith("edit"):

                    file = cmd.replace("edit", "").strip()

                    if file:

                        os.system(f"notepad {file}")


                # -----------------------
                # MARKET INTELLIGENCE
                # -----------------------
                elif cmd == "market":

                    summary = self.market_intel.market_summary()

                    print("\nMarket Intelligence\n")

                    for coin, data in summary.items():

                        vol = data["volatility_1h"]
                        mom = data["momentum_1h"]

                        print(f"{coin}")
                        print(f"  1H Volatility : {vol}%")
                        print(f"  1H Momentum   : {mom}%\n")


                # -----------------------
                # MARKET LEADER (MOMENTUM)
                # -----------------------
                elif cmd == "leader":

                    summary = self.market_intel.market_summary()

                    leader_coin = None
                    leader_value = None

                    for coin, data in summary.items():

                        momentum = data["momentum_1h"]

                        if momentum is None:
                            continue

                        if leader_value is None or momentum > leader_value:

                            leader_coin = coin
                            leader_value = momentum

                    if leader_coin is None:

                        print("Not enough data yet.")

                    else:

                        print("\nMarket Leader (1H Momentum)\n")

                        print(f"{leader_coin}")
                        print(f"  Momentum : {leader_value}%\n")


                # -----------------------
                # MARKET INSIGHT
                # -----------------------
                elif cmd == "insight":

                    insights = self.insight_engine.analyze_market()

                    if not insights:

                        print("No market signals detected.\n")

                    else:

                        print("\nMarket Insight\n")

                        for item in insights:

                            print(f"- {item}")

                        print()


                # -----------------------
                # MARKET DASHBOARD
                # -----------------------
                elif cmd == "dashboard":

                    self.market_dashboard.show()


                # -----------------------
                # DATASET DASHBOARD
                # -----------------------
                elif cmd == "dataset":

                    self.dataset_dashboard.show()


                # -----------------------
                # HEALTH DASHBOARD
                # -----------------------
                elif cmd == "health":

                    self.health_dashboard.show()


                # -----------------------
                # MARKET REGIME
                # -----------------------
                elif cmd == "regime":

                    info = self.regime_detector.market_regime()
                    regime = info.get("regime", "unknown").upper()

                    print(f"\nMarket Regime: {regime}\n")

                    for coin, r in info.get("breakdown", {}).items():
                        print(f"  {coin}: {r}")

                    print()


                # -----------------------
                # VOLATILITY INDEX
                # -----------------------
                elif cmd == "volindex":

                    report = self.volatility_index.report()

                    print(f"\nVolatility Index : {report['index']}")
                    print(f"Level            : {report['level'].upper()}\n")


                # -----------------------
                # MONITORING AGENT
                # -----------------------
                elif cmd == "monitor":

                    self.monitoring_agent.run()


                # -----------------------
                # DATASET AGENT
                # -----------------------
                elif cmd == "enrich":

                    self.dataset_agent.run()


                # -----------------------
                # TRAINING PIPELINE
                # -----------------------
                elif cmd == "train":

                    self.training_pipeline.run()


                # -----------------------
                # INSIGHT IMPROVER
                # -----------------------
                elif cmd == "improve":

                    self.insight_improver.run()


                # -----------------------
                # RESEARCH LOOP
                # -----------------------
                elif cmd == "research":

                    topic = cmd.replace("research", "").strip()

                    if topic:
                        self.run_research(topic)
                    else:
                        self.research_loop.run_once()


                # -----------------------
                # UNKNOWN COMMAND
                # -----------------------
                else:

                    print("Unknown command")


            except Exception as e:

                print("Command error:", e)


    # =============================
    # AI MARKET ANALYSIS LOOP
    # =============================
    def start_ai_analysis(self):

        print("[AI] market intelligence loop started")

        last_hour_summary = 0
        last_four_hour = 0
        last_snapshot_hash = None

        while True:

            try:

                now = time.time()

                insights = []

                try:
                    insights = self.insight_engine.analyze_market()
                except:
                    insights = []

                snapshot = "\n".join(insights)
                snapshot_hash = hashlib.md5(snapshot.encode()).hexdigest()

                # =============================
                # AI 15M MARKET ANALYSIS
                # =============================
                if insights and len(insights) >= 2:

                    if snapshot_hash != last_snapshot_hash:

                        print("\n────────────────────────────")
                        print("AI MARKET INSIGHT (15m)")
                        print("────────────────────────────\n")

                        prompt = f"""
You are Hansen AI, a crypto market intelligence system.

Interpret ONLY the market signals provided.

Output format:

MARKET TONE:
KEY DRIVERS:
VOLATILITY:
MARKET STRUCTURE:

Market Signals:
{snapshot}
"""

                        try:

                            response = requests.post(
                                "http://127.0.0.1:8080/completion",
                                json={
                                    "prompt": prompt,
                                    "n_predict": 120,
                                    "temperature": 0.3,
                                    "top_p": 0.9,
                                    "repeat_penalty": 1.1,
                                    "stop": ["```"]
                                },
                                timeout=180
                            )

                            reasoning = response.json().get("content", "")
                            reasoning = reasoning.strip()

                            reasoning = reasoning.replace("```python", "")
                            reasoning = reasoning.replace("```", "")

                            if "ANSWER:" in reasoning:
                                reasoning = reasoning.split("ANSWER:")[-1]

                            sections = [
                                "MARKET TONE:",
                                "KEY DRIVERS:",
                                "VOLATILITY:",
                                "MARKET STRUCTURE:"
                            ]

                            lines = reasoning.split("\n")
                            clean = []

                            for section in sections:

                                for line in lines:

                                    line = line.strip()

                                    if line.startswith(section):

                                        clean.append(line)
                                        break

                            reasoning = "\n".join(clean)

                            print(reasoning)
                            print()

                        except Exception as e:

                            print("AI reasoning error:", e)

                        last_snapshot_hash = snapshot_hash

                    else:

                        for item in insights:
                            print(f"- {item}")

                        print()

                # =============================
                # MARKET LEADERS
                # =============================
                try:

                    leader = self.market_intel.market_summary()

                    if leader:

                        print("────────────────────────────")
                        print("MARKET LEADERS")
                        print("────────────────────────────\n")

                        for coin, data in leader.items():

                            vol = data.get("volatility_1h")
                            mom = data.get("momentum_1h")

                            print(f"{coin}")
                            print(f"  volatility : {vol}")
                            print(f"  momentum   : {mom}\n")

                except:
                    pass


                # =============================
                # MARKET SIGNAL MODULES
                # =============================

                try:
                    self.detect_top_movers()
                except:
                    pass

                try:
                    self.detect_volatility_spikes()
                except:
                    pass

                try:
                    self.detect_market_anomalies()
                except:
                    pass

                try:
                    self.detect_sector_strength()
                except:
                    pass

                try:
                    self.detect_market_regime()
                except:
                    pass


                # =============================
                # AI 1H MARKET SUMMARY
                # =============================
                if now - last_hour_summary >= 3600:

                    print("\n════════════════════════════")
                    print("AI 1H MARKET SUMMARY")
                    print("════════════════════════════\n")

                    summary = self.market_intel.market_summary()

                    snapshot_lines = []

                    for coin, data in summary.items():

                        vol = data.get("volatility_1h")
                        mom = data.get("momentum_1h")

                        snapshot_lines.append(
                            f"{coin} momentum {mom} volatility {vol}"
                        )

                        print(f"{coin}")
                        print(f"  volatility : {vol}")
                        print(f"  momentum   : {mom}\n")

                    snapshot_lines = snapshot_lines[:15]

                    prompt = f"""
Provide a one hour crypto market summary.

Market Snapshot:
{chr(10).join(snapshot_lines)}
"""

                    try:

                        response = requests.post(
                            "http://127.0.0.1:8080/completion",
                            json={
                                "prompt": prompt,
                                "n_predict": 120,
                                "temperature": 0.3,
                                "top_p": 0.9,
                                "repeat_penalty": 1.1,
                                "stop": ["```"]
                            },
                            timeout=180
                        )

                        reasoning = response.json().get("content", "")
                        reasoning = reasoning.strip()

                        reasoning = reasoning.replace("```python", "")
                        reasoning = reasoning.replace("```", "")

                        if "ANSWER:" in reasoning:
                            reasoning = reasoning.split("ANSWER:")[-1]

                        sections = [
                            "MARKET TONE:",
                            "KEY DRIVERS:",
                            "VOLATILITY:",
                            "MARKET STRUCTURE:"
                        ]

                        lines = reasoning.split("\n")
                        clean = []

                        for section in sections:

                            for line in lines:

                                line = line.strip()

                                if line.startswith(section):

                                    clean.append(line)
                                    break

                        reasoning = "\n".join(clean)

                        print(reasoning)
                        print()

                    except Exception as e:

                        print("AI summary error:", e)

                    last_hour_summary = now


                # =============================
                # AI 4H MARKET OVERVIEW
                # =============================
                if now - last_four_hour >= 14400:

                    print("\n════════════════════════════")
                    print("AI 4H MARKET OVERVIEW")
                    print("════════════════════════════\n")

                    print("Stepping back to look at the broader market picture.\n")

                    summary = self.market_intel.market_summary()

                    snapshot_lines = []

                    for coin, data in summary.items():

                        vol = data.get("volatility_1h")
                        mom = data.get("momentum_1h")

                        snapshot_lines.append(
                            f"{coin} momentum {mom} volatility {vol}"
                        )

                        print(f"{coin}")
                        print(f"  volatility : {vol}")
                        print(f"  momentum   : {mom}\n")

                    snapshot_lines = snapshot_lines[:15]

                    prompt = f"""
Provide a broader four hour crypto market overview.

Market Snapshot:
{chr(10).join(snapshot_lines)}
"""

                    try:

                        response = requests.post(
                            "http://127.0.0.1:8080/completion",
                            json={
                                "prompt": prompt,
                                "n_predict": 120,
                                "temperature": 0.3,
                                "top_p": 0.9,
                                "repeat_penalty": 1.1,
                                "stop": ["```"]
                            },
                            timeout=180
                        )

                        reasoning = response.json().get("content", "")
                        reasoning = reasoning.strip()

                        reasoning = reasoning.replace("```python", "")
                        reasoning = reasoning.replace("```", "")

                        if "ANSWER:" in reasoning:
                            reasoning = reasoning.split("ANSWER:")[-1]

                        sections = [
                            "MARKET TONE:",
                            "KEY DRIVERS:",
                            "VOLATILITY:",
                            "MARKET STRUCTURE:"
                        ]

                        lines = reasoning.split("\n")
                        clean = []

                        for section in sections:

                            for line in lines:

                                line = line.strip()

                                if line.startswith(section):

                                    clean.append(line)
                                    break

                        reasoning = "\n".join(clean)

                        print(reasoning)
                        print()

                    except Exception as e:

                        print("AI overview error:", e)

                    last_four_hour = now


            except Exception as e:

                print("[AI ERROR]", e)

            time.sleep(900)



    # =============================
    # AI TOP MOVERS
    # =============================
    def detect_top_movers(self):

        try:

            data_file = r"C:\AI\hansen_engine\data\market_history.json"

            with open(data_file, "r") as f:
                history = json.load(f)

            coins = {}

            for item in history:

                symbol = item["symbol"]
                price = item["price"]

                if symbol not in coins:
                    coins[symbol] = []

                coins[symbol].append(price)

            changes = []

            for symbol, prices in coins.items():

                if len(prices) < 2:
                    continue

                change = ((prices[-1] - prices[0]) / prices[0]) * 100

                changes.append((symbol, change))

            changes.sort(key=lambda x: x[1], reverse=True)

            print("────────────────────────────")
            print("TOP MOVERS")
            print("────────────────────────────\n")

            for symbol, change in changes[:10]:
                print(f"{symbol} : {change:.2f}%")

            print()

            changes.sort(key=lambda x: x[1])

            print("────────────────────────────")
            print("TOP LOSERS")
            print("────────────────────────────\n")

            for symbol, change in changes[:10]:
                print(f"{symbol} : {change:.2f}%")

            print()

        except Exception as e:

            print("[AI ERROR] top movers:", e)


    # =============================
    # AI VOLATILITY SPIKE
    # =============================
    def detect_volatility_spikes(self):

        try:

            data_file = r"C:\AI\hansen_engine\data\market_history.json"

            with open(data_file, "r") as f:
                history = json.load(f)

            coins = {}

            for item in history:

                symbol = item["symbol"]
                price = item["price"]

                if symbol not in coins:
                    coins[symbol] = []

                coins[symbol].append(price)

            print("────────────────────────────")
            print("VOLATILITY SPIKES")
            print("────────────────────────────\n")

            for symbol, prices in coins.items():

                if len(prices) < 5:
                    continue

                recent = prices[-5:]

                change = max(recent) - min(recent)

                pct = (change / recent[0]) * 100

                if pct > 2:

                    print(f"{symbol} volatility spike {pct:.2f}%")

            print()

        except Exception as e:

            print("[AI ERROR] volatility spike:", e)


    # =============================
    # AI MARKET ANOMALY
    # =============================
    def detect_market_anomalies(self):

        try:

            data_file = r"C:\AI\hansen_engine\data\market_history.json"

            with open(data_file, "r") as f:
                history = json.load(f)

            coins = {}

            for item in history:

                symbol = item["symbol"]
                price = item["price"]

                if symbol not in coins:
                    coins[symbol] = []

                coins[symbol].append(price)

            print("────────────────────────────")
            print("MARKET ANOMALIES")
            print("────────────────────────────\n")

            for symbol, prices in coins.items():

                if len(prices) < 10:
                    continue

                start = prices[-10]
                end = prices[-1]

                change = ((end - start) / start) * 100

                if abs(change) > 5:

                    print(f"{symbol} abnormal move {change:.2f}%")

            print()

        except Exception as e:

            print("[AI ERROR] anomaly:", e)


    # =============================
    # AI SECTOR STRENGTH
    # =============================
    def detect_sector_strength(self):

        try:

            data_file = r"C:\AI\hansen_engine\data\market_history.json"

            with open(data_file, "r") as f:
                history = json.load(f)

            # =============================
            # RECENT DATA WINDOW (1H)
            # =============================

            cutoff = time.time() - (60 * 60)

            filtered_history = []

            for item in history:

                try:

                    ts = item["timestamp"]

                    if ts >= cutoff:
                        filtered_history.append(item)

                except:
                    continue

            history = filtered_history

            # =============================
            # ORGANIZE PRICES PER COIN
            # =============================

            coin_prices = {}

            for item in history:

                symbol = item["symbol"]
                price = item["price"]

                if symbol not in SECTOR_MAP:
                    continue

                if symbol not in coin_prices:
                    coin_prices[symbol] = []

                coin_prices[symbol].append(price)

            # =============================
            # CALCULATE COIN RETURNS
            # =============================

            sector_returns = {}

            for symbol, prices in coin_prices.items():

                if len(prices) < 2:
                    continue

                start = prices[0]
                end = prices[-1]

                if start == 0:
                    continue

                change = ((end - start) / start) * 100

                sector = SECTOR_MAP.get(symbol)

                if sector not in sector_returns:
                    sector_returns[sector] = []

                sector_returns[sector].append(change)

            # =============================
            # AVERAGE RETURNS PER SECTOR
            # =============================

            changes = []

            for sector, returns in sector_returns.items():

                if not returns:
                    continue

                avg_change = sum(returns) / len(returns)

                changes.append((sector, avg_change))

            if not changes:
                return

            strength = sorted(changes, key=lambda x: x[1], reverse=True)
            weakness = sorted(changes, key=lambda x: x[1])

            print("────────────────────────────")
            print("SECTOR STRENGTH")
            print("────────────────────────────\n")

            for sector, change in strength[:3]:
                print(f"{sector} : {change:.2f}%")

            print()

            print("────────────────────────────")
            print("SECTOR WEAKNESS")
            print("────────────────────────────\n")

            for sector, change in weakness[:3]:
                print(f"{sector} : {change:.2f}%")

            print()

        except Exception as e:

            print("[AI ERROR] sector analysis:", e)

    # =============================
    # MARKET REGIME DETECTOR
    # =============================
    def detect_market_regime(self):

        try:

            summary = self.market_intel.market_summary()

            bullish = 0
            bearish = 0
            volatile = 0

            for coin, data in summary.items():

                mom = data.get("momentum_1h")
                vol = data.get("volatility_1h")

                if mom is None or vol is None:
                    continue

                if mom > 0:
                    bullish += 1
                else:
                    bearish += 1

                if vol > 2:
                    volatile += 1

            total = bullish + bearish

            if total == 0:
                return

            if volatile > total * 0.4:

                regime = "VOLATILE"

            elif bullish > bearish * 1.5:

                regime = "TRENDING UP"

            elif bearish > bullish * 1.5:

                regime = "TRENDING DOWN"

            else:

                regime = "RANGE"

            print("────────────────────────────")
            print("MARKET REGIME")
            print("────────────────────────────\n")

            print(f"REGIME : {regime}")
            print(f"BULLISH COINS : {bullish}")
            print(f"BEARISH COINS : {bearish}")
            print(f"HIGH VOLATILITY : {volatile}")
            print()

        except Exception as e:

            print("[AI ERROR] regime:", e)

# =============================
# CLI ENTRYPOINT
# =============================

if __name__ == "__main__":

    import sys

    engine = HansenEngine()

    if len(sys.argv) < 2:
        print("Usage:")
        print(" python engine.py chat")
        print(" python engine.py research \"topic\"")
        print(" python engine.py agent \"task\"")
        print(" python engine.py status")
        print(" python engine.py ask \"message\"")
        print(" python engine.py knowledge \"query\"")
        exit()

    command = sys.argv[1]

    if command == "chat":

        chat_thread = threading.Thread(target=engine.chat_mode)

        chat_thread.daemon = True

        chat_thread.start()

        print("Chat thread started. Engine still running.\n")

        while True:
            time.sleep(1)

    elif command == "research":
        if len(sys.argv) < 3:
            print("Please provide a topic.")
        else:
            topic = " ".join(sys.argv[2:])
            engine.run_research(topic)

    elif command == "agent":
        if len(sys.argv) < 3:
            print("Please provide a task.")
        else:
            task = " ".join(sys.argv[2:])
            engine.run_agent(task)

    elif command == "status":
        engine.show_status()

    elif command == "ask":
        if len(sys.argv) < 3:
            print("Please provide a message.")
        else:
            message = " ".join(sys.argv[2:])
            engine.route_task(message)

    elif command == "knowledge":
        if len(sys.argv) < 3:
            print("Please provide a query.")
        else:
            query = " ".join(sys.argv[2:])
            engine.knowledge(query)

    elif command == "ingest":
        engine.ingest_knowledge()

    elif command == "price":

        if len(sys.argv) < 3:
            symbol = "btc"
        else:
            symbol = sys.argv[2]

        engine.market_price(symbol)

    elif command == "logger":
        engine.market_logger()

    elif command == "scheduler":
        engine.start_scheduler()

    elif command == "read":

        if len(sys.argv) < 3:
            print("Please provide a folder.")
        else:
            path = sys.argv[2]
            engine.read_data(path)

    elif command == "index":

        if len(sys.argv) < 3:
            print("Please provide a folder.")
        else:
            folder = sys.argv[2]
            engine.build_index(folder)

    elif command == "insight":

        engine.market_insight()

    elif command == "volatility":

        engine.market_volatility()

    elif command == "run":

        print("Starting Hansen Engine...\n")

        engine.start_market_logger()

        ai_thread = threading.Thread(
            target=engine.start_ai_analysis,
            daemon=True
        )

        ai_thread.start()

        command_thread = threading.Thread(
            target=engine.command_loop,
            daemon=True
        )

        command_thread.start()

        while True:
            time.sleep(1)

    else:
        print("Unknown command.")