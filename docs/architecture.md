# Hansen AI Research Engine — System Architecture

## 1. Executive Summary

Hansen AI is a sovereign, locally-operated quantitative intelligence system designed for continuous ingestion, multi-factor analysis, cryptographic packaging, and decentralized persistence of high-throughput cryptocurrency market telemetry.

The architecture eliminates reliance on third-party cloud infrastructure by enforcing a **Local-First, Sovereign Processing Model**. Ingestion, inference, and encryption execute locally on host infrastructure, with decentralized persistence anchored to the **Shelby Protocol (shelbynet)** and cryptographic attestation verified on **Aptos Move**.

---

## 2. 6-Tier Architecture Overview

```
+-------------------------------------------------------------------------+
|                       TIER 1: MARKET INGESTION                          |
|   740+ Binance Futures Pairs (741 Active Cluster) · Websockets · 5s     |
+-------------------------------------------------------------------------+
                                    │
                                    ▼
+-------------------------------------------------------------------------+
|                    TIER 2: PIPELINE AGGREGATION                         |
|   Market Collector (Go Aggregator) · Depth Collector (Microstructure)   |
+-------------------------------------------------------------------------+
                                    │
                                    ▼
+-------------------------------------------------------------------------+
|                    TIER 3: INTELLIGENCE ENGINE                          |
|   Market Brain · 10 Interconnected Sources · Local LLM + Groq Failover  |
+-------------------------------------------------------------------------+
                                    │
                                    ▼
+-------------------------------------------------------------------------+
|                 TIER 4: TRIPLE-TIER PERSISTENCE SPLIT                   |
|   Hot Header Tier: _meta.json (<50 KB, uncompressed, <300ms SLA)        |
|   Cold Lake Tier: snapshot_*.json.gz (40K+ records, ~730 KB gzip)       |
|   Encrypted Tier: depth_*.parquet.enc (~21 MB/day, AES-256-GCM)         |
+-------------------------------------------------------------------------+
                                    │
                                    ▼
+-------------------------------------------------------------------------+
|               TIER 5: DECENTRALIZED DATA LAKE (SHELBY)                  |
|   Shelby Protocol · Clay Erasure Codes · Multi-Location Node Routing   |
|   ShelbyUSD Storage Credits · Asynchronous SLA Verification Probe       |
+-------------------------------------------------------------------------+
                                    │
                                    ▼
+-------------------------------------------------------------------------+
|                  TIER 6: ON-CHAIN PROOF & ACTIVE RAG                    |
|   Aptos Move Registry Attestation · Active RAG (<300ms) · Reader CLI    |
+-------------------------------------------------------------------------+
```

---

## 3. Triple-Tier Pipeline Specification

### Stream A: Hot Companion Microstructure Headers
* **Frequency:** Every ~4.5 hours (co-generated alongside market snapshots).
* **Payload Size:** <50 KB uncompressed JSON.
* **Format:** Uncompressed structured JSON exposing the institutional `lake_header` microstructure indicators:
  - `market_phase` (CHOP, TREND, ACCUMULATION, DISTRIBUTION, VOLATILE)
  - `energy_level` (LOW, MEDIUM, HIGH, EXTREME)
  - `liquidity_magnet` (Dynamic liquidation density and magnet zones)
  - `systemic_risk` (NORMAL, ELEVATED, EXTREME)
  - `positioning_imbalance` (Funding z-scores, positioning asymmetries, OI momentum)
  - `forensic_narrative` (Dense quant microstructure narrative)
* **Performance:** Direct HTTP 206 byte-range slicing (<300ms TTFB) for active RAG prompt augmentation without the overhead of decompressing multi-megabyte payloads.
* **Namespace:** `hansen_ai/market_pipeline/snapshots/snapshot_<timestamp>_meta.json`
* **Retention:** 90-day rolling expiration on Shelbynet.

### Stream B: Cold Dense Market Snapshots
* **Frequency:** Every ~4.5 hours (cadence-driven).
* **Payload Size:** ~730 KB per snapshot (Gzip-compressed from ~5.1 MB raw JSON, 85.6% storage reduction).
* **Format:** Native Gzip-compressed structured JSON containing price records, funding rates, open interest, sector performance, correlation matrices, and 10-source market intelligence.
* **Volume:** 40,000+ normalized records across 740+ pairs (dynamic rolling window).
* **Namespace:** `hansen_ai/market_pipeline/snapshots/snapshot_<timestamp>.json.gz`
* **Retention:** 90-day rolling expiration on Shelbynet.

### Stream C: Encrypted High-Frequency Orderbook Depth Archives
* **Frequency:** Daily cumulative rolling archive.
* **Payload Size:** ~21 MB per daily archive.
* **Encryption Standard:** Client-side **AES-256-GCM** (Galois/Counter Mode).
* **Key Derivation & Structure:**
  - 96-bit (12-byte) Cryptographic Nonce (IV) randomly generated per upload.
  - 128-bit (16-byte) Authentication Tag.
  - Additional Authenticated Data (AAD): `hansen_depth_v1`.
  - Wire Format: `[IV (12B)] + [Tag (16B)] + [Ciphertext (NB)]`.
* **Namespace:** `hansen_ai/market_pipeline/depth/depth_<timestamp>.parquet.enc`
* **Security Model:** Zero-knowledge persistence. Node operators and Shelby storage providers store encrypted ciphertext and cannot decrypt market microstructure data.

---

## 4. Trust Boundaries & Security Architecture

1. **Signer & Private Key Isolation:**
   - Aptos Ed25519 signer keys are stored locally with strict filesystem permissions (`0600`) at `.aptos_key` or supplied via ephemeral environment variables (`APTOS_PRIVATE_KEY`).
   - The signer account pays testnet gas for blob commitment registration and Move entry function invocations.
   - Enforces an automated balance floor (0.2 APT) and max gas ceiling (5,000 Octas) to prevent wallet exhaustion.

2. **Storage Verification & Availability SLA:**
   - Immediately following blob upload to Shelbynet, the uploader enqueues an asynchronous verification task (20s delay).
   - The probe requests byte slices (`Range: bytes=0-31`) from distributed RPC nodes to guarantee that data has been distributed across storage providers and is retrievable over HTTP.
   - Files failing multi-attempt verification are automatically recycled to `failed/` for retransmission, preventing local data loss.
   - Empirical SLA benchmarks confirm 100% Availability with <300ms TTFB on hot slices.

3. **On-Chain Ledger Attestation:**
   - Every uploaded blob name and SHA-256 payload digest (anchored in the historical `merkle_root` field) is permanently recorded to the Aptos blockchain via the `hansen::registry` smart contract.
   - External researchers and consumer nodes can verify that downloaded snapshots match the exact digest signed by Hansen Engine at the time of creation.

4. **Active RAG Prompt Augmentation:**
   - Internal inference routines query Shelby Hot Storage via `modules/shelby_reader.py` using zero-decompression HTTP 206 byte slices.
   - Historical lake headers feed directly into prompt context windows for multi-day regime awareness with automatic fallback to local disk if network is unreachable.
