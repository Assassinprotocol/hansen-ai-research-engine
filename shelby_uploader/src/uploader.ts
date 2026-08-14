import fs from "fs";
import path from "path";
import chokidar from "chokidar";
import { ShelbyNodeClient } from "@shelby-protocol/sdk/node";
import {
  Account,
  Ed25519PrivateKey,
  Network,
  PrivateKey,
  PrivateKeyVariants,
} from "@aptos-labs/ts-sdk";

import { loadConfig, requireEnv } from "./config.js";
import { log } from "./logger.js";
import type { SnapshotFile, TrackerData } from "./types.js";

// ── Bootstrap ────────────────────────────────────────────────────
const cfg = loadConfig();

const SHELBY_API_KEY = requireEnv("SHELBY_API_KEY");
const SHELBY_LOCATION_HINT = process.env.SHELBY_LOCATION_HINT || "shelbynet-1";



// ── Signer ───────────────────────────────────────────────────────
function loadOrCreateSigner(): Account {
  // Accepts SHELBY_PRIVATE_KEY or APTOS_PRIVATE_KEY as aliases.
  let hex =
    process.env.SHELBY_PRIVATE_KEY ??
    process.env.APTOS_PRIVATE_KEY ??
    (fs.existsSync(cfg.keyFile) ? fs.readFileSync(cfg.keyFile, "utf8").trim() : undefined);

  if (!hex) {
    const fresh = new Ed25519PrivateKey(
      (Account.generate().privateKey as Ed25519PrivateKey).toString()
    );
    hex = fresh.toString();
    fs.writeFileSync(cfg.keyFile, hex, { mode: 0o600 });
    log("INFO", "Generated new Aptos signer key", { keyFile: cfg.keyFile });
  }

  let privateKey: Ed25519PrivateKey;
  try {
    const formatted = PrivateKey.formatPrivateKey(hex, PrivateKeyVariants.Ed25519);
    privateKey = new Ed25519PrivateKey(formatted);
  } catch {
    privateKey = new Ed25519PrivateKey(hex);
  }

  const account = Account.fromPrivateKey({ privateKey });
  log("INFO", "Aptos signer ready", { address: account.accountAddress.toString() });
  return account;
}

const signer = loadOrCreateSigner();

const client = new ShelbyNodeClient({
  network: "shelbynet" as any,
  apiKey: SHELBY_API_KEY,
});

// ── Ensure dirs ──────────────────────────────────────────────────
for (const dir of [cfg.uploadedDir, cfg.failedDir]) {
  fs.mkdirSync(dir, { recursive: true });
}

// ── State ────────────────────────────────────────────────────────
const retryCount = new Map<string, number>();
const processing = new Set<string>();

// ── Tracker ──────────────────────────────────────────────────────
function recordUpload(filename: string, success: boolean, detail = ""): void {
  try {
    let tracker: TrackerData = { uploads: [], failed: [] };
    if (fs.existsSync(cfg.trackerFile)) {
      tracker = JSON.parse(fs.readFileSync(cfg.trackerFile, "utf8")) as TrackerData;
    }
    tracker.uploads ??= [];
    tracker.failed ??= [];

    const entry = { file: filename, time: new Date().toISOString(), ...(detail ? { detail } : {}) };
    if (success) tracker.uploads.push(entry);
    else tracker.failed.push(entry);

    fs.writeFileSync(cfg.trackerFile, JSON.stringify(tracker, null, 2));
  } catch (err) {
    log("ERROR", "Tracker write failed", { error: (err as Error).message });
  }
}

// ── Funding (non-blocking) ───────────────────────────────────────
function withTimeout<T>(promise: Promise<T>, ms: number, label: string): Promise<T> {
  return Promise.race([
    promise,
    new Promise<T>((_, reject) =>
      setTimeout(() => reject(new Error(`${label} timeout after ${ms}ms`)), ms)
    ),
  ]);
}

async function fundSignerOnce(): Promise<void> {
  try {
    await withTimeout(
      client.fundAccountWithAPT({ address: signer.accountAddress, amount: 100_000_000 }),
      20_000,
      "fundAccountWithAPT"
    );
    log("INFO", "Funded signer with testnet APT");
  } catch (err) {
    log("WARN", "APT funding skipped", { error: (err as Error).message });
  }
  try {
    await withTimeout(
      client.fundAccountWithShelbyUSD({ address: signer.accountAddress, amount: 100_000_000 }),
      20_000,
      "fundAccountWithShelbyUSD"
    );
    log("INFO", "Funded signer with ShelbyUSD");
  } catch (err) {
    log("WARN", "ShelbyUSD funding skipped", { error: (err as Error).message });
  }
}

// ── Upload ───────────────────────────────────────────────────────
async function uploadFile(filePath: string): Promise<void> {
  const filename = path.basename(filePath);

  if (processing.has(filename)) return;
  processing.add(filename);

  const attempts = (retryCount.get(filename) ?? 0) + 1;
  retryCount.set(filename, attempts);

  log("INFO", `Upload attempt ${attempts}/${cfg.maxRetries}`, { file: filename });

  try {
    const content = fs.readFileSync(filePath);

    if (client && 'initializeAccount' in client) {
      await (client as any).initializeAccount({ signer });
    }

    await client.upload({
      blobData: content,
      signer,
      blobName: `hansen_ai/market_pipeline/snapshots/${filename}`,
      expirationMicros: Date.now() * 1000 + 90 * 24 * 60 * 60 * 1_000_000, // 90 days (3 months)
      options: {
        selectedLocation: SHELBY_LOCATION_HINT,
        locationHint: SHELBY_LOCATION_HINT,
      } as any,
    });

    log("INFO", "Upload success", { file: filename });

    fs.copyFileSync(filePath, path.join(cfg.uploadedDir, filename));
    fs.unlinkSync(filePath);
    retryCount.delete(filename);
    recordUpload(filename, true);
  } catch (err) {
    const e = err as { response?: { status: number; data: unknown }; message: string };
    const detail = e.response
      ? `HTTP ${e.response.status}: ${JSON.stringify(e.response.data)}`
      : e.message;

    log("WARN", `Upload failed (attempt ${attempts})`, { file: filename, error: detail });

    if (attempts >= cfg.maxRetries) {
      log("ERROR", "Max retries reached, moving to failed/", { file: filename });
      try {
        fs.renameSync(filePath, path.join(cfg.failedDir, filename));
      } catch (mvErr) {
        log("ERROR", "Move to failed/ failed", { error: (mvErr as Error).message });
      }
      retryCount.delete(filename);
      recordUpload(filename, false, detail);
    }
  } finally {
    processing.delete(filename);
  }
}

// ── Pending list ─────────────────────────────────────────────────
function getPendingSnapshots(): SnapshotFile[] {
  try {
    const files = fs
      .readdirSync(cfg.watchDir)
      .filter((f) => /^snapshot_.*\.json$/.test(f) && f !== "snapshot_state.json");

    const withStats: SnapshotFile[] = files
      .map((f) => {
        const full = path.join(cfg.watchDir, f);
        try {
          return { name: f, path: full, mtime: fs.statSync(full).mtimeMs };
        } catch {
          return null;
        }
      })
      .filter((x): x is SnapshotFile => x !== null);

    withStats.sort((a, b) => b.mtime - a.mtime);

    if (withStats.length > cfg.maxPending) {
      const skipped = withStats.splice(cfg.maxPending);
      for (const s of skipped) {
        log("WARN", "Exceeds max pending, moving oldest to failed/", { file: s.name });
        try {
          fs.renameSync(s.path, path.join(cfg.failedDir, s.name));
          recordUpload(s.name, false, "exceeded max pending limit");
        } catch (e) {
          log("ERROR", "Failed to move excess file", { error: (e as Error).message });
        }
      }
    }

    return withStats;
  } catch (err) {
    log("ERROR", "Failed to read watch dir", { error: (err as Error).message });
    return [];
  }
}

// ── Scan cycle ───────────────────────────────────────────────────
async function scan(): Promise<void> {
  const snapshots = getPendingSnapshots();
  if (snapshots.length === 0) return;

  log("INFO", `Scan found ${snapshots.length} pending snapshot(s)`);
  for (const snap of snapshots) {
    await uploadFile(snap.path);
  }
}

// ── Watcher ──────────────────────────────────────────────────────
const watcher = chokidar.watch(cfg.watchDir, {
  persistent: true,
  ignoreInitial: true,
  depth: 0,
  awaitWriteFinish: { stabilityThreshold: 2000, pollInterval: 500 },
});

watcher.on("add", async (filePath: string) => {
  const filename = path.basename(filePath);
  if (!/^snapshot_.*\.json$/.test(filename) || filename === "snapshot_state.json") return;
  log("INFO", "New snapshot detected", { file: filename });
  await uploadFile(filePath);
});

watcher.on("error", (err: unknown) => {
  log("ERROR", "Watcher error", { error: (err as Error).message });
});

// ── Start ────────────────────────────────────────────────────────
log("INFO", "Shelby uploader started", {
  watchDir: cfg.watchDir,
  uploadedDir: cfg.uploadedDir,
  failedDir: cfg.failedDir,
  maxRetries: cfg.maxRetries,
  maxPending: cfg.maxPending,
  scanInterval: `${cfg.scanIntervalMs / 1000}s`,
});

(async () => {
  await fundSignerOnce();
  await scan();
})();

setInterval(scan, cfg.scanIntervalMs);
