# Hansen AI Research Engine

<p align="center">
  <img src="assets/logo/hansen-ai-banner.png" alt="Hansen AI Banner" />
</p>

<p align="center">
  <a href="https://x.com/M0neyHeistHunt">
    <img src="https://img.shields.io/badge/X-%40MoneyHeistHunt-black?logo=x&logoColor=white" />
  </a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.14-blue" />
  <img src="https://img.shields.io/badge/LLM-llama.cpp-orange" />
  <img src="https://img.shields.io/badge/Dataset-Shelby_Protocol-green" />
  <img src="https://img.shields.io/badge/status-active-success" />
  <img src="https://img.shields.io/badge/license-proprietary-red" />
  <img src="https://img.shields.io/badge/modules-30+-purple" />
</p>

---

> **Sovereign market intelligence infrastructure for AI-driven crypto research.**

Hansen AI is a sovereign, locally-operated market intelligence system designed to collect, analyze, and store crypto market data for AI-driven research and trading.

The engine combines:
- Continuous market data collection  
- Autonomous AI analysis  
- Enriched dataset generation  
- Decentralized storage via Shelby Protocol  

**Local-first AI architecture. Zero mandatory cloud.**  
Powered by local LLMs with optional Groq API fallback for high-availability. Only relies on Binance Futures public data and Shelby Protocol.

---

## 🎥 Demo

https://youtu.be/YyaH22LkkEA


\---

## Key Features

* Fully local AI market intelligence engine — sovereign, no cloud
* 718 Binance Futures pairs monitored in real-time
* 90-day rolling historical dataset (1M+ records)
* 8 interconnected intelligence modules feeding central AI brain
* Local LLM reasoning via llama.cpp (Qwen 2.5 7B)
* Automated enriched dataset generation every \~4 hours
* On-chain verifiable dataset storage via Shelby Protocol
* Real-time web dashboard with 15+ panels
* AI-generated market reports (flash/daily/weekly)
* Automatic narrative detection (12 market narratives)
* Multi-chain crypto payments (BSC/ARB/ETH/SOL/BTC/Aptos)

\---

## Tech Stack

|Layer|Technology|
|-|-|
|Language|Python 3.14|
|Web Framework|Flask|
|LLM Inference|llama.cpp (local) + Groq Cloud failover|
|Database|SQLite|
|Uploader|Node.js|
|Market Data|Binance Futures API (public)|
|Dataset Storage|Shelby Protocol (Aptos testnet)|
|Frontend|Vanilla HTML/CSS/JS, Font Awesome, Sora + JetBrains Mono|

\---

## Quick Start

**Clone repository:**

```bash
# Clone the repository
git clone https://github.com/Assassinprotocol/hansen-ai-research-engine.git
cd hansen-ai-research-engine
```

**Create virtual environment:**

```bash
python -m venv venv
activate venv
pip install -r requirements.txt
```

**Run LLM server:**

```bash
cd ~/AI/llama.cpp
./build/bin/llama-server -m models/Qwen2.5-7B-Instruct-Q4_K_M.gguf --port 8080 --ctx-size 4096 --threads 6
```

**Start engine:**

```bash
source ~/AI/hansen_engine/venv/bin/activate
cd ~/AI/hansen_engine
python engine.py run
```

**Start dashboard:**

```bash
python -m dashboard.web\_dashboard
```

**Open Browser (Frontend & Backend):**

```bash
# Next.js Frontend (UI in active development)
cd ~/AI/hansen-web && npm run dev
# Browser: http://localhost:3000

# Flask Backend API
# Browser: http://localhost:5000
```

**Optional — Shelby publisher:**

```bash
cd ./shelby_uploader
node uploader.js
```

\---

## Architecture Overview

```mermaid
graph TD
    %% TIER 1: INGESTION
    FEED["Binance Futures Market Feed<br/>718 active pairs · real-time L2 websocket"]

    %% TIER 2: PARALLEL AGGREGATION
    FEED -->|5s tick stream| TICK["Market Collector<br/>tick aggregator"]
    FEED -->|microstructure| DEPTH["Depth Collector<br/>orderbook sampler"]

    %% TIER 3: INTELLIGENCE CORE
    TICK --> BRAIN["Market Brain<br/>multi-source state aggregator"]
    BRAIN --> LLM["Local LLM Inference<br/>Qwen 2.5 7B · local runtime"]

    %% TIER 4: OUTPUT SPLIT
    LLM --> DASH["Web Dashboard<br/>live telemetry"]
    LLM --> EXEC["Trade Engine<br/>order router"]
    LLM -->|public tier · 4h| SNAP["Market Snapshots<br/>~5.1 MB JSON"]
    DEPTH -->|encrypted tier · daily| ARCH["Depth Archives<br/>AES-256-GCM · ~21 MB"]

    %% TIER 5: DECENTRALIZED PERSISTENCE
    SNAP --> SHELBY[("Shelby Protocol<br/>Decentralized Data Lake")]
    ARCH --> SHELBY

    %% TIER 6: CONSUMPTION & PROOF
    SHELBY --> CLI["Reader CLI<br/>query & decrypt"]
    SHELBY -.-> APTOS["Aptos Move Contract<br/>on-chain attestation"]

    classDef default font-family:sans-serif,font-size:12px;
    classDef nodeBase fill:#161b22,stroke:#30363d,color:#e6edf3,stroke-width:1px;
    classDef nodeFeed fill:#0d1926,stroke:#1f6feb,color:#e6edf3,stroke-width:1.5px;
    classDef nodeExec fill:#072214,stroke:#238636,color:#e6edf3,stroke-width:1px;
    classDef nodeShelby fill:#21180a,stroke:#d29922,color:#f0e6d2,stroke-width:1.5px;

    class FEED nodeFeed;
    class TICK,DEPTH,BRAIN,LLM,DASH,SNAP,ARCH,CLI,APTOS nodeBase;
    class EXEC nodeExec;
    class SHELBY nodeShelby;
```

\---

## Intelligence Modules

### P1 — Data Depth

* **Funding Rate**: Real-time rates with long/short sentiment scoring
* **Open Interest**: OI spike and dump detection
* **Liquidation Feed**: Cascade monitoring with dominance analysis
* **Derivatives Collector**: Unified background data collection

### P2 — Analytics

* **Sector Performance**: 110+ coins across 16 sectors. Multi-timeframe ranking (1h/4h/24h/7d), rotation detection, strength scoring
* **Correlation Matrix**: 25-coin Pearson correlation (pure Python, no numpy). Multi-window (24h/7d/14d/30d)
* **Beta vs BTC**: Per-coin beta relative to Bitcoin

### P3 — Alerts + Heatmap

* **Alert Engine**: Price pump/dump, funding spikes, liquidation surges, volume anomalies. Severity levels, cooldown, persistent history
* **Market Heatmap**: Sector-grouped color grid with intensity based on price change

### P4 — Smart Screener

6 preset filters: Momentum Kings, Dip Buys, Volume Surge, Low Funding, High Funding, Breakout Candidates. Custom filter support with real-time scanning.

### P5 — Sentiment + Narrative

* **Fear \& Greed Index**: 4-component composite (momentum 40%, volatility 20%, volume 20%, breadth 20%)
* **12 Narratives**: Alt Season, BTC Dominance, Meme Mania, DeFi Revival, AI Narrative, L2 Pump, Market Fear, Capitulation, Accumulation, Gaming Surge, RWA Momentum, High Funding Warning

### P6 — Onchain Intelligence

* **Whale Activity**: Volume spike detection on 20 major coins, accumulation/distribution scoring
* **Exchange Flow**: Buy/sell pressure from OHLC, net inflow/outflow
* **Stablecoin Flow**: USDC/FDUSD/DAI/TUSD tracking, peg monitoring

### P7 — AI Reports

* **Flash**: 3-5 sentence market snapshot
* **Daily**: 5-section structured report
* **Weekly**: Forward-looking analysis
* Local LLM generates from Market Brain context. Fallback template when offline.

### Market Brain

Central hub aggregating all 8 data sources into unified reasoning context. Powers AI reports, snapshot enrichment, and the `/api/v1/brain/context` endpoint.

\---

## Web Dashboard

### Dashboard Panels

|Panel|Description|
|-|-|
|Market Regime|Bull/Bear/Sideways per coin|
|Volatility Index|Market-wide volatility level|
|System Stats|Records, symbols, snapshot ETA, uploads|
|Top Gainers/Losers|Real-time price movers|
|Market Summary|BTC/ETH/BNB/SOL overview|
|Derivatives Intelligence|Funding, OI, Liquidations|
|Sector Performance|16-sector ranking + rotation|
|Correlation Matrix|25-coin heatmap + beta vs BTC|
|Alert Center|Severity-based alert feed|
|Market Heatmap|Visual sector color grid|
|Smart Screener|6-preset coin scanner|
|Market Sentiment|Fear/Greed + active narratives|
|Onchain Intelligence|Whale, flow, stablecoin|
|AI Reports|Flash/daily/weekly + LLM status|
|AI Market Insight|Latest LLM-generated analysis|

### Landing Page

Professional scrollytelling design with 3D rotating logo, parallax scroll, glassmorphism, Font Awesome icons, live sector ticker, and multi-chain payment modal.

### Admin Panel

User management, payment tracking, audit log, role-based access (Viewer/Analyst/Admin).

\---

## API Endpoints

|Method|Endpoint|Description|
|-|-|-|
|GET|`/api/v1/movers`|Top movers|
|GET|`/api/v1/system`|System statistics|
|GET|`/api/v1/derivatives`|Funding, OI, liquidations|
|GET|`/api/v1/sector-performance`|Sector summary + rotation|
|GET|`/api/v1/sector-ranking?tf=24h`|Ranking by timeframe|
|GET|`/api/v1/correlation?window=7d`|Correlation + beta|
|GET|`/api/v1/alerts`|Alerts + stats|
|GET|`/api/v1/heatmap?tf=24h`|Market heatmap|
|GET|`/api/v1/screener`|All screener presets|
|GET|`/api/v1/sentiment`|Fear/Greed + narratives|
|GET|`/api/v1/onchain`|Whale, flow, stablecoin|
|GET|`/api/v1/reports`|Report summary|
|GET|`/api/v1/reports/generate?type=daily`|Generate report|
|GET|`/api/v1/brain`|Brain summary|
|GET|`/api/v1/brain/context`|Full AI context|
|GET|`/api/v1/ai-insight`|Latest AI analysis|

\---

## Enriched Snapshot Structure

Each snapshot uploaded to Shelby contains the full market intelligence context:

```json
{
  "records": \["...30,000 price records..."],
  "market\_regime": {"regime": "sideways", "breakdown": {}},
  "volatility": {"index": 0.32, "level": "medium"},
  "market\_insight": \["BTC holds relative momentum..."],
  "top\_gainers": \[{"symbol": "PLAY", "change\_pct": 6.97}],
  "top\_losers": \[{"symbol": "LYN", "change\_pct": -7.89}],
  "sector\_performance": {
    "ranking": \["...16 sectors ranked..."],
    "top\_3": \["AI / Compute", "Infrastructure", "Meme"]
  },
  "sector\_rotation": {"rotating\_in": \[], "rotating\_out": \[]},
  "sentiment": {"score": 41.9, "level": "Cautious", "components": {}},
  "active\_narratives": \[
    {"label": "Accumulation Phase", "strength": 93.3},
    {"label": "AI Narrative Hot", "strength": 10.9}
  ],
  "alerts\_summary": {"stats": {"last\_24h": 643, "critical\_24h": 263}},
  "whale\_activity": {"total\_signals": 6},
  "exchange\_flow": {"net\_sentiment": "neutral"},
  "opportunities": {
    "momentum\_kings": \[],
    "dip\_buys": \[],
    "breakout\_candidates": \[]
  },
  "correlation": {"strongest\_pairs": \[], "high\_beta": \[]},
  "derivatives": {
    "funding\_summary": {},
    "oi\_summary": {},
    "liq\_summary": {},
    "cascade\_alert": {}
  },
  "brain\_data\_sources": 8,
  "generated\_at": "2026-03-13T08:30:00"
}
```

\---

## Module Structure

```
hansen\_engine/
├── engine.py                        # Core engine + Market Brain + market logger
├── config.py                        # System configuration
│
├── modules/                         # 30+ intelligence modules
│   ├── market\_data.py               # Binance API (prices, ticker, klines)
│   ├── market\_brain.py              # Central AI reasoning hub
│   ├── sector\_performance.py        # 16-sector analysis (110+ coins)
│   ├── correlation\_matrix.py        # 25-coin correlation + beta
│   ├── alert\_engine.py              # Multi-type alert system
│   ├── market\_heatmap.py            # Sector heatmap generator
│   ├── smart\_screener.py            # 6-preset screener
│   ├── sentiment\_engine.py          # Fear/Greed + narratives
│   ├── onchain\_intel.py             # Whale, flow, stablecoin
│   ├── ai\_reports.py                # LLM report generator
│   ├── derivatives\_collector.py     # Funding, OI, liquidation
│   ├── market\_regime.py             # Regime detection
│   ├── momentum\_engine.py           # Momentum ranking
│   ├── volatility\_index.py          # Volatility index
│   ├── top\_movers.py                # Top movers detection
│   ├── market\_intelligence.py       # Legacy sector analysis
│   ├── funding\_rate.py              # Funding tracker
│   ├── open\_interest.py             # OI history
│   ├── liquidation\_feed.py          # Liquidation monitor
│   └── ...                          # + 15 more utility modules
│
├── dashboard/                       # Web + CLI dashboards
│   ├── web\_dashboard.py             # Flask dashboard (15+ panels)
│   ├── landing\_page.py              # Scrollytelling landing page
│   ├── dashboard\_config.py          # Configuration
│   ├── db\_manager.py                # SQLite user DB
│   ├── email\_service.py             # Gmail SMTP
│   ├── payment\_detector.py          # Multi-chain payments
│   └── ...                          # + CLI dashboards
│
├── agents/                          # Autonomous agents
├── pipeline/                        # Training + research pipelines
├── core/                            # Logger, profile, insight
├── router/                          # Intent routing
├── rag/                             # Retrieval-augmented generation
├── data/                            # Runtime data + AI reports
└── dataset/                         # Snapshot lifecycle
    ├── pending/                     # Awaiting upload
    ├── uploaded/                    # Successfully uploaded
    ├── failed/                      # Failed uploads
    ├── processed/                   # Processed for training
    └── training/                    # Training-ready datasets
```

\---

## CLI Usage

```bash
python engine.py run          # Start engine

# Market
dashboard                     # Full market dashboard
market                        # Market leaders
insight                       # AI market insight
regime                        # Market regime
volindex                      # Volatility index
price btc                     # BTC price

# System
health                        # System health
dataset                       # Dataset statistics
monitor                       # Monitoring report

# Agents
agent "analyze market trend"  # Run agent task
enrich                        # Enrich snapshots
train                         # Training pipeline
research "topic"              # Research topic
```

\---

## Roadmap

* \[x] AI Trade Signals
* \[x] Advanced regime detection
* \[x] Multi-timeframe analysis (15m / 1h / 4h)
* \[x] High-frequency depth collection
* \[/] Multi-exchange support (partial)
* \[ ] Next.js dashboard frontend
* \[ ] Public dataset explorer
* \[ ] Shelby mainnet dataset publishing
* \[ ] Discord bot + webhook alerts (P8)
* \[ ] API monetization layer

\---

## Decentralized Data Lake (Shelby Protocol)

Hansen AI uses [Shelby Protocol](https://shelby.xyz) as its decentralized storage layer for verifiable market intelligence data.

**Dual-Stream Pipeline:**
- **Public Tier:** Enriched market snapshots (~30,000 records, ~5.1 MB each) uploaded every ~4 hours.
- **Encrypted Tier:** High-frequency depth archives (~21 MB/day) encrypted client-side using **AES-256-GCM** before upload.
- **On-Chain Proof:** Attestation via Aptos Move smart contract (`contract/`).
- **Downstream Tooling:** Reader CLI (`scripts/shelby_reader.py`) supporting inspection, byte-range queries, and authenticated decryption.

The background TypeScript uploader automatically publishes datasets to the `hansen_ai/market_pipeline/` namespace on the Shelby network.

\---

## System Requirements

* Python 3.14+
* Node.js (Shelby uploader)
* llama.cpp server at `http://127.0.0.1:8080`
* WSL with Shelby CLI (dataset upload)
* Binance Futures API access (public, no key required)

\---

## License

Proprietary. All rights reserved.

