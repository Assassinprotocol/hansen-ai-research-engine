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
import { encryptDepthPayload } from "./crypto.js";
import type { SnapshotFile, TrackerData, TrackerEntry } from "./types.js";

const cfg = loadConfig();

const SHELBY_API_KEY = requireEnv("SHELBY_API_KEY");
const SHELBY_LOCATION_HINT = process.env.SHELBY_LOCATION_HINT || "shelbynet-1";

function loadOrCreateSigner(): Account {
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

for (const dir of [cfg.uploadedDir, cfg.failedDir]) {
  fs.mkdirSync(dir, { recursive: true });
}

const retryCount = new Map<string, number>();
const processing = new Set<string>();

function recordUpload(
  filename: string,
  success: boolean,
  dataType?: "snapshot" | "depth",
  blobName?: string,
  encryptionKey?: string,
  detail = ""
): void {
  try {
    let tracker: TrackerData = { uploads: [], failed: [] };
    if (fs.existsSync(cfg.trackerFile)) {
      tracker = JSON.parse(fs.readFileSync(cfg.trackerFile, "utf8")) as TrackerData;
    }
    tracker.uploads ??= [];
    tracker.failed ??= [];

    const entry: TrackerEntry = {
      file: filename,
      time: new Date().toISOString(),
      ...(dataType ? { dataType } : {}),
      ...(blobName ? { blobName } : {}),
      ...(encryptionKey ? { encryptionKey } : {}),
      ...(detail ? { detail } : {}),
    };
    if (success) tracker.uploads.push(entry);
    else tracker.failed.push(entry);

    fs.writeFileSync(cfg.trackerFile, JSON.stringify(tracker, null, 2));
  } catch (err) {
    log("ERROR", "Tracker write failed", { error: (err as Error).message });
  }
}

function withTimeout<T>(promise: Promise<T>, ms: number, label: string): Promise<T> {
  return Promise.race([
    promise,
    new Promise<T>((_, reject) =>
      setTimeout(() => reject(new Error(`${label} timeout after ${ms}ms`)), ms)
    ),
  ]);
}

async function checkSignerBalance(): Promise<void> {
  try {
    const rawBalance = await withTimeout(
      client.aptos.getAccountAPTAmount({ accountAddress: signer.accountAddress }),
      10_000,
      "getAccountAPTAmount"
    );
    const apt = Number(rawBalance) / 100_000_000;
    log("INFO", "Signer balance checked", {
      address: signer.accountAddress.toString(),
      aptBalance: `${apt.toFixed(4)} APT`,
    });
  } catch (err) {
    log("WARN", "Signer balance check skipped", { error: (err as Error).message });
  }
}

async function fundSignerOnce(): Promise<void> {
  if (process.env.SHELBY_AUTO_FAUCET !== "true") {
    log("INFO", "Auto-faucet disabled (production/credits mode)");
    return;
  }
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

async function uploadFile(filePath: string): Promise<void> {
  const filename = path.basename(filePath);

  if (processing.has(filename)) return;
  processing.add(filename);

  const attempts = (retryCount.get(filename) ?? 0) + 1;
  retryCount.set(filename, attempts);

  const isDepth = filename.startsWith("depth_");
  const prefix = isDepth
    ? "hansen_ai/market_pipeline/depth"
    : "hansen_ai/market_pipeline/snapshots";
  const targetBlobFilename = isDepth && !filename.endsWith(".enc") ? `${filename}.enc` : filename;
  const blobName = `${prefix}/${targetBlobFilename}`;

  log("INFO", `Upload attempt ${attempts}/${cfg.maxRetries}`, { file: filename, blobName });

  let encryptionKeyHex: string | undefined = undefined;

  try {
    let content: any = fs.readFileSync(filePath);

    if (isDepth) {
      const encrypted = encryptDepthPayload(content);
      content = encrypted.encryptedPayload;
      encryptionKeyHex = encrypted.keyHex;
      log("INFO", "Encrypted depth payload (AES-256-GCM)", {
        file: filename,
        origSize: fs.statSync(filePath).size,
        encSize: content.length,
      });
    }

    if (client && 'initializeAccount' in client) {
      await (client as any).initializeAccount({ signer });
    }

    const location = attempts > 1 ? undefined : SHELBY_LOCATION_HINT;
    const uploadOptions = location
      ? ({ selectedLocation: location, locationHint: location } as any)
      : undefined;

    await client.upload({
      blobData: content,
      signer,
      blobName,
      expirationMicros: Date.now() * 1000 + 90 * 24 * 60 * 60 * 1_000_000,
      options: uploadOptions,
    } as any);

    log("INFO", "Upload success", { file: filename, blobName, encrypted: isDepth });

    if (!isDepth) {
      fs.copyFileSync(filePath, path.join(cfg.uploadedDir, filename));
    }
    fs.unlinkSync(filePath);
    retryCount.delete(filename);
    recordUpload(filename, true, isDepth ? "depth" : "snapshot", blobName, encryptionKeyHex);
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
      recordUpload(filename, false, isDepth ? "depth" : "snapshot", blobName, encryptionKeyHex, detail);
    }
  } finally {
    processing.delete(filename);
  }
}

const WATCH_REGEX = /^(snapshot_.*|depth_.*)\.(json|parquet|tar\.gz)$/;

function getPendingSnapshots(): SnapshotFile[] {
  try {
    const files = fs
      .readdirSync(cfg.watchDir)
      .filter((f) => WATCH_REGEX.test(f) && f !== "snapshot_state.json");

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
          recordUpload(s.name, false, undefined, undefined, undefined, "exceeded max pending limit");
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

async function scan(): Promise<void> {
  const snapshots = getPendingSnapshots();
  if (snapshots.length === 0) return;

  log("INFO", `Scan found ${snapshots.length} pending snapshot(s)`);
  for (const snap of snapshots) {
    await uploadFile(snap.path);
  }
}

const watcher = chokidar.watch(cfg.watchDir, {
  persistent: true,
  ignoreInitial: true,
  depth: 0,
  awaitWriteFinish: { stabilityThreshold: 2000, pollInterval: 500 },
});

watcher.on("add", async (filePath: string) => {
  const filename = path.basename(filePath);
  if (!WATCH_REGEX.test(filename) || filename === "snapshot_state.json") return;
  log("INFO", "New snapshot detected", { file: filename });
  await uploadFile(filePath);
});

watcher.on("error", (err: unknown) => {
  log("ERROR", "Watcher error", { error: (err as Error).message });
});

function reclaimFailedUploads(): void {
  try {
    if (!fs.existsSync(cfg.failedDir)) return;
    const failedFiles = fs
      .readdirSync(cfg.failedDir)
      .filter((f) => WATCH_REGEX.test(f) && f !== "snapshot_state.json");

    if (failedFiles.length === 0) return;

    log("INFO", `Auto-Recovery: Found ${failedFiles.length} file(s) in failed/, reclaiming back to pending/`);
    for (const f of failedFiles) {
      const src = path.join(cfg.failedDir, f);
      const dst = path.join(cfg.watchDir, f);
      try {
        fs.renameSync(src, dst);
        retryCount.delete(f);
        log("INFO", "Auto-Recovery: Reclaimed file to pending/", { file: f });
      } catch (err) {
        log("ERROR", "Auto-Recovery move failed", { file: f, error: (err as Error).message });
      }
    }
  } catch (err) {
    log("ERROR", "Failed to scan failed/ dir for recovery", { error: (err as Error).message });
  }
}

log("INFO", "Shelby uploader started", {
  watchDir: cfg.watchDir,
  uploadedDir: cfg.uploadedDir,
  failedDir: cfg.failedDir,
  maxRetries: cfg.maxRetries,
  maxPending: cfg.maxPending,
  scanInterval: `${cfg.scanIntervalMs / 1000}s`,
  autoRecoveryInterval: "1h",
});

(async () => {
  await checkSignerBalance();
  await fundSignerOnce();
  reclaimFailedUploads();
  await scan();
})();

setInterval(scan, cfg.scanIntervalMs);
setInterval(reclaimFailedUploads, 3600_000);
