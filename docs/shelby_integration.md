# Shelby Protocol Integration Specification

## 1. Overview

Hansen AI utilizes the **Shelby Protocol (shelbynet)** as the decentralized persistence layer for high-throughput market intelligence and orderbook telemetry. This document details the technical implementation, protocol ergonomics, data encoding, verification SLA, and smart contract anchoring.

---

## 2. Shelby Protocol Ergonomics & SDK Architecture

The uploader service leverages `@shelby-protocol/sdk` (v0.7.0) and `@aptos-labs/ts-sdk` (v6.3.1) in a decoupled TypeScript daemon:

```typescript
import { ShelbyNodeClient } from "@shelby-protocol/sdk/node";

const client = new ShelbyNodeClient({
  network: "shelbynet",
  apiKey: process.env.SHELBY_API_KEY,
});
```

### Key Technical Capabilities:
1. **Clay Erasure Coding Stressing:**
   - Ingesting dense uncompressed JSON (~5.1 MB) and encrypted depth archives (~21 MB) stresses Clay Erasure Codes across distributed storage nodes, moving far beyond in-memory toy payloads (<50 KB).
2. **Multi-Location Geographic Routing:**
   - Upload operations specify `locationHint` / `selectedLocation` (`"shelbynet-1"`) to steer placement across storage provider clusters.
3. **Deterministic Retention:**
   - Snapshots declare a 90-day retention horizon via `expirationMicros`:
     `expirationMicros: Date.now() * 1000 + 90 * 24 * 60 * 60 * 1_000_000`

---

## 3. Asynchronous Verification & Availability SLA Probing

To guarantee data persistence beyond optimistic upload confirmation, the uploader implements a multi-stage background verification loop:

```
[Upload Confirmed] ──▶ [Enqueue VerificationTask (20s delay)]
                                   │
                                   ▼
                      [HTTP GET Range: bytes=0-31]
                                   │
                    ┌──────────────┴──────────────┐
                    ▼                             ▼
            [HTTP 206 / 200 OK]              [Failure / Timeout]
            - Record Latency (ms)            - Exponential Backoff
            - Verify Remote Size             - Retry (up to 3x)
            - Mark verified: true            - Move to failed/ if unverified
            - Gated Cleanup of Local Disk
```

### Verification Probe Logic:
* Uses HTTP byte-range slicing (`Range: bytes=0-31`) to test storage provider chunk assembly and response latency without downloading the full multi-megabyte payload.
* Tracks latency metrics (`verifyLatencyMs`) in `data/upload_tracker.json`.
* Only verify-confirmed depth archives are pruned from local disk, ensuring zero risk of unrecoverable data loss.

---

## 4. On-Chain Attestation: Aptos Move Smart Contract

Every successful blob publication is permanently notarized to the Aptos blockchain via the `hansen::registry` module (`contract/sources/registry.move`).

### Smart Contract Structure:
```move
module hansen::registry {
    struct SnapshotRecord has store, drop, copy {
        blob_name: vector<u8>,
        merkle_root: vector<u8>,
        timestamp: u64,
        data_type: vector<u8>,
        record_count: u64,
    }

    public entry fun initialize(admin: &signer);

    public entry fun record_snapshot(
        admin: &signer,
        blob_name: vector<u8>,
        merkle_root: vector<u8>,
        timestamp: u64,
        data_type: vector<u8>,
        record_count: u64,
    );

    #[view]
    public fun is_initialized(addr: address): bool;

    #[view]
    public fun get_total_records(addr: address): u64;

    #[view]
    public fun get_snapshot_record(addr: address, record_id: u64): 
        (vector<u8>, vector<u8>, u64, vector<u8>, u64);
}
```

### Attestation Lifecycle:
1. `record_snapshot` creates a sequential record in an on-chain `Table<u64, SnapshotRecord>`.
2. Emits an on-chain `SnapshotRecordedEvent` containing the `record_id`, `blob_name`, and timestamp.
3. Cryptographically seals the 32-byte SHA-256 digest (`merkle_root`) of the blob on the ledger.

---

## 5. Downstream Consumption: Reader CLI (`shelby_reader.py`)

External consumers and AI agents query, verify, and decrypt market telemetry using the Python CLI tool:

### Commands:

1. **Inspect Metadata:**
   ```bash
   python scripts/shelby_reader.py inspect hansen_ai/market_pipeline/snapshots/snapshot_2026-09-22T08:00:00.json
   ```

2. **Byte-Range Query (Slice Ingestion):**
   ```bash
   python scripts/shelby_reader.py range hansen_ai/market_pipeline/snapshots/snapshot_2026-09-22T08:00:00.json --start 0 --end 1024
   ```

3. **Stream Download:**
   ```bash
   python scripts/shelby_reader.py download hansen_ai/market_pipeline/snapshots/snapshot_2026-09-22T08:00:00.json
   ```

4. **SHA-256 Integrity Verification:**
   ```bash
   python scripts/shelby_reader.py verify hansen_ai/market_pipeline/snapshots/snapshot_2026-09-22T08:00:00.json --expected <hash>
   ```

5. **Client-Side Decryption (AES-256-GCM):**
   ```bash
   python scripts/shelby_reader.py decrypt depth_2026-09-22.parquet.enc --key <32_byte_hex_key>
   ```

6. **On-Chain Attestation Verification:**
   ```bash
   # Query record from Aptos Move contract
   python scripts/shelby_reader.py onchain 1

   # Query and cross-verify with Shelby blob in one step
   python scripts/shelby_reader.py onchain 1 --verify-blob
   ```
