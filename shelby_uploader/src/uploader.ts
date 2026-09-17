import fs from "fs";
import path from "path";
import axios from "axios";
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
import { encryptDepthPayload, encryptDepthPayloadOptimized } from "./crypto.js";
import type { SnapshotFile, TrackerData, TrackerEntry, VerificationTask } from "./types.js";

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

let trackerPromise = Promise.resolve();

function mutateTracker(mutator: (tracker: TrackerData) => void): Promise<void> {
  trackerPromise = trackerPromise.then(async () => {
    try {
      let tracker: TrackerData = { uploads: [], failed: [] };
      if (fs.existsSync(cfg.trackerFile)) {
        try {
          tracker = JSON.parse(fs.readFileSync(cfg.trackerFile, "utf8")) as TrackerData;
        } catch {
          tracker = { uploads: [], failed: [] };
        }
      }
      tracker.uploads ??= [];
      tracker.failed ??= [];

      mutator(tracker);

      const tmpFile = `${cfg.trackerFile}.${Date.now()}.${Math.random().toString(36).substring(2, 6)}.tmp`;
      fs.writeFileSync(tmpFile, JSON.stringify(tracker, null, 2));
      fs.renameSync(tmpFile, cfg.trackerFile);
    } catch (err) {
      log("ERROR", "Tracker atomic mutation failed", { error: (err as Error).message });
    }
  });
  return trackerPromise;
}

async function recordUpload(
  filename: string,
  success: boolean,
  dataType?: "snapshot" | "depth",
  blobName?: string,
  encryptionKey?: string,
  detail = "",
  sizeBytes?: number
): Promise<void> {
  await mutateTracker((tracker) => {
    const entry: TrackerEntry = {
      file: filename,
      time: new Date().toISOString(),
      ...(dataType ? { dataType } : {}),
      ...(blobName ? { blobName } : {}),
      ...(encryptionKey ? { encryptionKey } : {}),
      ...(detail ? { detail } : {}),
      ...(sizeBytes !== undefined ? { sizeBytes } : {}),
      ...(success ? { verified: false, verifyStatus: "pending" } : {}),
    };
    if (success) tracker.uploads.push(entry);
    else tracker.failed.push(entry);
  });
}

async function probeBlobAvailability(task: VerificationTask): Promise<{
  success: boolean;
  status?: number;
  latencyMs?: number;
  remoteSize?: number;
  error?: string;
}> {
  const encodedAccount = encodeURIComponent(signer.accountAddress.toString());
  const encodedBlob = encodeURI(task.blobName);
  const url = `${cfg.rpcUrl}/v1/blobs/${encodedAccount}/${encodedBlob}`;
  const start = Date.now();

  try {
    const resp = await axios.get(url, {
      headers: {
        Authorization: `Bearer ${SHELBY_API_KEY}`,
        Range: "bytes=0-31",
        "User-Agent": "HansenShelbyUploader/3.1",
      },
      timeout: 10_000,
      validateStatus: (status) => status >= 200 && status < 300,
    });

    const latencyMs = Date.now() - start;
    const contentRange = resp.headers["content-range"] || "";
    let remoteSize = task.localSize;

    if (contentRange && typeof contentRange === "string" && contentRange.includes("/")) {
      const parsed = parseInt(contentRange.split("/")[1], 10);
      if (!isNaN(parsed)) remoteSize = parsed;
    }

    const sizeMatches = task.localSize === 0 || remoteSize === task.localSize;
    if (!sizeMatches) {
      return {
        success: false,
        status: resp.status,
        latencyMs,
        remoteSize,
        error: `Size mismatch: local ${task.localSize} vs remote ${remoteSize}`,
      };
    }

    return { success: true, status: resp.status, latencyMs, remoteSize };
  } catch (err: any) {
    const latencyMs = Date.now() - start;
    const status = err.response?.status;
    const errorMsg = status ? `HTTP ${status}` : err.message;
    return { success: false, status, latencyMs, error: errorMsg };
  }
}

const verificationQueue: VerificationTask[] = [];

function enqueueVerification(task: VerificationTask): void {
  verificationQueue.push(task);
  log("INFO", "Enqueued RAW verification task", { file: task.filename, delayMs: task.nextAttemptAt - Date.now() });
}

async function processVerificationQueue(): Promise<void> {
  const now = Date.now();
  const readyIndices: number[] = [];

  for (let i = 0; i < verificationQueue.length; i++) {
    if (now >= verificationQueue[i].nextAttemptAt) readyIndices.push(i);
  }

  if (readyIndices.length === 0) return;

  for (const idx of readyIndices.reverse()) {
    const task = verificationQueue.splice(idx, 1)[0];
    task.attempts += 1;

    log("INFO", `Running RAW verification probe (attempt ${task.attempts}/${cfg.verifyMaxRetries})`, {
      file: task.filename,
    });

    const res = await probeBlobAvailability(task);

    if (res.success) {
      log("INFO", "RAW Verification SUCCESS", {
        file: task.filename,
        status: res.status,
        latencyMs: `${res.latencyMs}ms`,
        remoteSize: res.remoteSize,
      });

      await mutateTracker((tracker) => {
        const entry = tracker.uploads.find((u) => u.file === task.filename);
        if (entry) {
          entry.verified = true;
          entry.verifiedAt = new Date().toISOString();
          entry.verifyLatencyMs = res.latencyMs;
          entry.verifyStatus = res.status;
          entry.remoteSizeBytes = res.remoteSize;
        }
      });

      const localUploadedPath = path.join(cfg.uploadedDir, task.filename);
      if (task.isDepth && fs.existsSync(localUploadedPath)) {
        fs.unlinkSync(localUploadedPath);
        log("INFO", "Gated Cleanup: Unlinked verified depth archive from local disk", { file: task.filename });
      }
    } else {
      if (task.attempts < cfg.verifyMaxRetries) {
        const backoffMs = task.attempts === 1 ? 40_000 : 120_000;
        task.nextAttemptAt = Date.now() + backoffMs;
        verificationQueue.push(task);
        log("WARN", `RAW probe unconfirmed, rescheduled in ${backoffMs / 1000}s`, {
          file: task.filename,
          error: res.error,
        });
      } else {
        log("ERROR", "RAW verification FAILED after max retries", {
          file: task.filename,
          error: res.error,
        });

        await mutateTracker((tracker) => {
          const entry = tracker.uploads.find((u) => u.file === task.filename);
          if (entry) {
            entry.verified = false;
            entry.verifyStatus = res.status || "unconfirmed";
            entry.verifyError = res.error;
          }
        });

        const localUploadedPath = path.join(cfg.uploadedDir, task.filename);
        const localFailedPath = path.join(cfg.failedDir, task.filename);
        if (fs.existsSync(localUploadedPath)) {
          fs.renameSync(localUploadedPath, localFailedPath);
          log("WARN", "Moved unverified file to failed/ for auto-reclaim", { file: task.filename });
        }
      }
    }
  }
}

function pruneUploadedDir(): void {
  try {
    if (!fs.existsSync(cfg.uploadedDir)) return;
    const files = fs.readdirSync(cfg.uploadedDir);

    const depthFiles = files
      .filter((f) => f.startsWith("depth_"))
      .map((f) => ({ name: f, path: path.join(cfg.uploadedDir, f), mtime: fs.statSync(path.join(cfg.uploadedDir, f)).mtimeMs }))
      .sort((a, b) => b.mtime - a.mtime);

    if (depthFiles.length > cfg.maxUploadedDepthKeep) {
      for (const d of depthFiles.slice(cfg.maxUploadedDepthKeep)) {
        try { fs.unlinkSync(d.path); } catch {}
      }
    }

    const snapFiles = files
      .filter((f) => f.startsWith("snapshot_"))
      .map((f) => ({ name: f, path: path.join(cfg.uploadedDir, f), mtime: fs.statSync(path.join(cfg.uploadedDir, f)).mtimeMs }))
      .sort((a, b) => b.mtime - a.mtime);

    if (snapFiles.length > cfg.maxUploadedSnapshotsKeep) {
      for (const s of snapFiles.slice(cfg.maxUploadedSnapshotsKeep)) {
        try { fs.unlinkSync(s.path); } catch {}
      }
    }
  } catch (err) {
    log("ERROR", "pruneUploadedDir error", { error: (err as Error).message });
  }
}

function rehydrateVerificationQueue(): void {
  try {
    if (!fs.existsSync(cfg.trackerFile)) return;
    const tracker = JSON.parse(fs.readFileSync(cfg.trackerFile, "utf8")) as TrackerData;
    if (!tracker.uploads || tracker.uploads.length === 0) return;

    const oneDayAgo = Date.now() - 24 * 60 * 60 * 1000;
    const unverified = tracker.uploads.filter((u) => {
      if (u.verified === true) return false;
      const t = new Date(u.time).getTime();
      return !isNaN(t) && t >= oneDayAgo && u.blobName;
    });

    if (unverified.length === 0) return;

    log("INFO", `Auto-Recovery: Rehydrating ${unverified.length} unverified upload(s) into queue`);
    for (const u of unverified) {
      enqueueVerification({
        filename: u.file,
        blobName: u.blobName!,
        isDepth: u.file.startsWith("depth_"),
        localSize: u.sizeBytes || 0,
        attempts: 0,
        nextAttemptAt: Date.now() + 5000,
      });
    }
  } catch (err) {
    log("ERROR", "Failed to rehydrate verification queue", { error: (err as Error).message });
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
  let payloadSize = 0;

  try {
    const stat = fs.statSync(filePath);
    let content: any;

    if (isDepth) {
      if (stat.size >= cfg.streamThresholdBytes) {
        log("INFO", "Engaging single-buffer stream encryption", {
          file: filename,
          sizeMb: (stat.size / (1024 * 1024)).toFixed(2),
        });
        const opt = await encryptDepthPayloadOptimized(filePath);
        content = opt.encryptedPayload;
        encryptionKeyHex = opt.keyHex;
        payloadSize = content.length;
      } else {
        const raw = fs.readFileSync(filePath);
        const encrypted = encryptDepthPayload(raw);
        content = encrypted.encryptedPayload;
        encryptionKeyHex = encrypted.keyHex;
        payloadSize = content.length;
      }
      log("INFO", "Encrypted depth payload (AES-256-GCM)", {
        file: filename,
        origSize: stat.size,
        encSize: payloadSize,
      });
    } else {
      content = fs.readFileSync(filePath);
      payloadSize = content.length;
    }

    if (client && "initializeAccount" in client) {
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

    content = null;

    log("INFO", "Upload success", { file: filename, blobName, encrypted: isDepth });

    const destUploadedPath = path.join(cfg.uploadedDir, filename);
    fs.renameSync(filePath, destUploadedPath);
    retryCount.delete(filename);

    await recordUpload(filename, true, isDepth ? "depth" : "snapshot", blobName, encryptionKeyHex, "", payloadSize);

    enqueueVerification({
      filename,
      blobName,
      isDepth,
      localSize: payloadSize,
      attempts: 0,
      nextAttemptAt: Date.now() + cfg.verifyInitialDelayMs,
    });

    pruneUploadedDir();
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
      await recordUpload(filename, false, isDepth ? "depth" : "snapshot", blobName, encryptionKeyHex, detail);
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
  rehydrateVerificationQueue();
  pruneUploadedDir();
  await scan();
})();

setInterval(scan, cfg.scanIntervalMs);
setInterval(reclaimFailedUploads, 3600_000);
setInterval(processVerificationQueue, 5_000);
setInterval(pruneUploadedDir, 600_000);
