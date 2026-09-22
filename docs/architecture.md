# Hansen AI Research Engine — System Architecture

## 1. Executive Summary

Hansen AI is a sovereign, locally-operated quantitative intelligence system designed for continuous ingestion, multi-factor analysis, cryptographic packaging, and decentralized persistence of high-throughput cryptocurrency market telemetry.

The architecture eliminates reliance on third-party cloud infrastructure by enforcing a **Local-First, Sovereign Processing Model**. Ingestion, inference, and encryption execute locally on host infrastructure, with decentralized persistence anchored to the **Shelby Protocol (shelbynet)** and cryptographic attestation verified on **Aptos Move**.

---

## 2. 6-Tier Architecture Overview

```
+-------------------------------------------------------------------------+
|                       TIER 1: MARKET INGESTION                          |
|   718 Binance Futures Pairs · Real-time Websockets · 5s Tick Ingestion  |
+-------------------------------------------------------------------------+
                                    │
                                    ▼
+-------------------------------------------------------------------------+
|                    TIER 2: PIPELINE AGGREGATION                         |
|   Market Collector (Tick Aggregator) · Depth Collector (Orderbook HFT)  |
+-------------------------------------------------------------------------+
                                    │
                                    ▼
+-------------------------------------------------------------------------+
|                    TIER 3: INTELLIGENCE ENGINE                          |
|   Central Market Brain · 30+ Factor Modules · Local LLM (Qwen 2.5 7B)   |
+-------------------------------------------------------------------------+
                                    │
                                    ▼
+-------------------------------------------------------------------------+
|                       TIER 4: DUAL-STREAM SPLIT                         |
|   Public Tier: Enriched Snapshot (~5.1 MB JSON, ~30,000 Records)        |
|   Encrypted Tier: Orderbook Depth Archive (~21 MB, AES-256-GCM)         |
+-------------------------------------------------------------------------+
                                    │
                                    ▼
+-------------------------------------------------------------------------+
|               TIER 5: DECENTRALIZED DATA LAKE (SHELBY)                  |
|   Shelby Protocol · Clay Erasure Codes · Multi-Location Node Routing   |
|   Availability Probing (HTTP Range bytes=0-31) · Dynamic Replication    |
+-------------------------------------------------------------------------+
                                    │
                                    ▼
+-------------------------------------------------------------------------+
|                  TIER 6: ON-CHAIN PROOF & CONSUMPTION                   |
|   Aptos Move Registry Attestation · Downstream Reader CLI               |
+-------------------------------------------------------------------------+
```

---

## 3. Dual-Stream Pipeline Specification

### Stream A: Public Enriched Market Snapshots
* **Frequency:** Every ~4 hours (cadence-driven).
* **Payload Size:** ~5.1 MB per snapshot.
* **Format:** Uncompressed structured JSON containing price data, funding rates, open interest, sector performance, correlation matrices, and LLM market intelligence.
* **Volume:** 30,000+ normalized records across 718 pairs.
* **Namespace:** `hansen_ai/market_pipeline/snapshots/snapshot_<timestamp>.json`
* **Retention:** 90-day rolling expiration on Shelbynet.

### Stream B: Encrypted High-Frequency Orderbook Depth Archives
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

2. **Storage Verification & Availability SLA:**
   - Immediately following blob upload to Shelbynet, the uploader enqueues an asynchronous verification task.
   - The probe requests byte slices (`Range: bytes=0-31`) from distributed RPC nodes to guarantee that data has been distributed across storage providers and is retrievable over HTTP.
   - Files failing multi-attempt verification are automatically recycled to `failed/` for retransmission, preventing local data loss.

3. **On-Chain Ledger Attestation:**
   - Every uploaded blob name and SHA-256 Merkle root digest is permanently anchored to the Aptos blockchain via the `hansen::registry` smart contract.
   - External researchers and consumer nodes can verify that downloaded snapshots match the exact digest signed by Hansen Engine at the time of creation.
