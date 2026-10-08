import fs from "fs";
import path from "path";
import crypto from "crypto";
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

function initShelbyClient(): ShelbyNodeClient {
  if (cfg.networkType === "custom") {
    log("INFO", "Initializing ShelbyNodeClient with custom endpoints", {
      network: cfg.networkName,
      rpcUrl: cfg.rpcUrl,
      aptosRpcUrl: cfg.aptosRpcUrl,
    });
    return new ShelbyNodeClient({
      network: Network.CUSTOM,
      apiKey: SHELBY_API_KEY,
      locationHint: cfg.locationHint,
      aptos: {
        fullnode: cfg.aptosRpcUrl,
      },
      rpc: {
        baseUrl: cfg.rpcUrl,
        apiKey: SHELBY_API_KEY,
      },
    });
  }
  return new ShelbyNodeClient({
    network: cfg.networkType as any,
    apiKey: SHELBY_API_KEY,
    locationHint: cfg.locationHint,
  });
}

const client = initShelbyClient();

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
  sizeBytes?: number,
  merkleRootHex?: string,
  onchainTxHash?: string,
  onchainStatus?: "confirmed" | "failed" | "skipped"
): Promise<void> {
  await mutateTracker((tracker) => {
    const entry: TrackerEntry = {
      file: filename,
      time: new Date().toISOString(),
      network: cfg.networkName,
      ...(dataType ? { dataType } : {}),
      ...(blobName ? { blobName } : {}),
      ...(encryptionKey ? { encryptionKey } : {}),
      ...(detail ? { detail } : {}),
      ...(sizeBytes !== undefined ? { sizeBytes } : {}),
      ...(merkleRootHex ? { merkleRootHex } : {}),
      ...(onchainTxHash ? { onchainTxHash } : {}),
      ...(onchainStatus ? { onchainStatus } : {}),
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

let isProcessingVerification = false;

async function processVerificationQueue(): Promise<void> {
  if (isProcessingVerification) return;
  isProcessingVerification = true;

  try {
    const now = Date.now();
    const readyTasks: VerificationTask[] = [];
    const remainingTasks: VerificationTask[] = [];

    for (const t of verificationQueue) {
      if (now >= t.nextAttemptAt) {
        readyTasks.push(t);
      } else {
        remainingTasks.push(t);
      }
    }

    // Atomically replace queue with remaining pending tasks
    verificationQueue.length = 0;
    verificationQueue.push(...remainingTasks);

    if (readyTasks.length === 0) return;

    for (const task of readyTasks) {
      if (!task) continue;
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
  } finally {
    isProcessingVerification = false;
  }
}

function pruneUploadedDir(): void {
  try {
    if (!fs.existsSync(cfg.uploadedDir)) return;
    const files = fs.readdirSync(cfg.uploadedDir);

    const depthFiles = files
      .filter((f) => f.startsWith("depth_") && !f.endsWith("_meta.json"))
      .map((f) => ({ name: f, path: path.join(cfg.uploadedDir, f), mtime: fs.statSync(path.join(cfg.uploadedDir, f)).mtimeMs }))
      .sort((a, b) => b.mtime - a.mtime);

    if (depthFiles.length > cfg.maxUploadedDepthKeep) {
      for (const d of depthFiles.slice(cfg.maxUploadedDepthKeep)) {
        try { fs.unlinkSync(d.path); } catch {}
        const metaPath = d.path.replace(/(\.tar\.gz|\.parquet|\.json)(\.enc)?$/, "_meta.json");
        if (fs.existsSync(metaPath)) {
          try { fs.unlinkSync(metaPath); } catch {}
        }
      }
    }

    const snapFiles = files
      .filter((f) => f.startsWith("snapshot_") && !f.endsWith("_meta.json"))
      .map((f) => ({ name: f, path: path.join(cfg.uploadedDir, f), mtime: fs.statSync(path.join(cfg.uploadedDir, f)).mtimeMs }))
      .sort((a, b) => b.mtime - a.mtime);

    if (snapFiles.length > cfg.maxUploadedSnapshotsKeep) {
      for (const s of snapFiles.slice(cfg.maxUploadedSnapshotsKeep)) {
        try { fs.unlinkSync(s.path); } catch {}
        const metaPath = s.path.replace(/\.json(\.gz)?$/, "_meta.json");
        if (fs.existsSync(metaPath)) {
          try { fs.unlinkSync(metaPath); } catch {}
        }
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

let cachedBalanceApt: number | null = null;
let balanceLastFetchedAt = 0;
let gasPauseUntil = 0;

async function getSignerBalanceApt(forceRefresh = false): Promise<number> {
  const now = Date.now();
  if (!forceRefresh && cachedBalanceApt !== null && (now - balanceLastFetchedAt < cfg.balanceCacheTtlMs)) {
    return cachedBalanceApt;
  }

  try {
    const rawBalance = await withTimeout(
      client.aptos.getAccountAPTAmount({ accountAddress: signer.accountAddress }),
      10_000,
      "getAccountAPTAmount"
    );
    cachedBalanceApt = Number(rawBalance) / 100_000_000;
    balanceLastFetchedAt = now;
    return cachedBalanceApt;
  } catch (err) {
    if (cachedBalanceApt !== null) {
      log("WARN", "Signer balance refresh failed, falling back to cached balance", {
        error: (err as Error).message,
        cachedBalanceApt,
      });
      return cachedBalanceApt;
    }
    log("WARN", "Signer balance check skipped (no cache)", { error: (err as Error).message });
    return 0;
  }
}

async function checkSignerBalance(): Promise<void> {
  try {
    const apt = await getSignerBalanceApt(true);
    log("INFO", "Signer balance checked", {
      address: signer.accountAddress.toString(),
      aptBalance: `${apt.toFixed(4)} APT`,
      minFloor: `${cfg.minSignerBalanceApt} APT`,
      network: cfg.networkName,
    });
  } catch (err) {
    log("WARN", "Signer balance check error", { error: (err as Error).message });
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

async function recordOnChainAttestation(
  blobName: string,
  merkleRootHex: string,
  dataType: string,
  recordCount: number
): Promise<{ txHash?: string; status: "confirmed" | "failed" | "skipped"; error?: string }> {
  if (process.env.SHELBY_SKIP_ONCHAIN === "true") {
    log("INFO", "On-chain attestation skipped via env", { blobName });
    return { status: "skipped" };
  }

  try {
    const timestampSecs = Math.floor(Date.now() / 1000);
    const contractAddr = cfg.contractAddress;

    const task = (async () => {
      // 1. Ensure Registry is initialized under signer account
      try {
        const isInitRes = await client.aptos.view({
          payload: {
            function: `${contractAddr}::registry::is_initialized` as any,
            typeArguments: [],
            functionArguments: [signer.accountAddress.toString()],
          },
        });
        const isInit = Boolean(isInitRes && isInitRes[0]);
        if (!isInit) {
          log("INFO", "Initializing HansenRegistry on-chain...", { address: signer.accountAddress.toString() });
          const initTx = await client.aptos.transaction.build.simple({
            sender: signer.accountAddress,
            data: {
              function: `${contractAddr}::registry::initialize` as any,
              typeArguments: [],
              functionArguments: [],
            },
          });
          const initAuth = client.aptos.transaction.sign({ signer, transaction: initTx });
          const initPending = await client.aptos.transaction.submit.simple({ transaction: initTx, senderAuthenticator: initAuth });
          await client.aptos.waitForTransaction({ transactionHash: initPending.hash });
          log("INFO", "HansenRegistry initialized on-chain", { txHash: initPending.hash });
        }
      } catch (initErr: any) {
        log("WARN", "Registry check/init skipped or errored", { error: initErr.message });
      }

      // 2. Submit record_snapshot entry function
      const tx = await client.aptos.transaction.build.simple({
        sender: signer.accountAddress,
        data: {
          function: `${contractAddr}::registry::record_snapshot` as any,
          typeArguments: [],
          functionArguments: [
            Array.from(Buffer.from(blobName, "utf8")),
            Array.from(Buffer.from(merkleRootHex, "hex")),
            timestampSecs,
            Array.from(Buffer.from(dataType, "utf8")),
            recordCount,
          ],
        },
        options: {
          maxGasAmount: cfg.maxAttestationGasAmount,
        },
      });

      const auth = client.aptos.transaction.sign({ signer, transaction: tx });
      const pending = await client.aptos.transaction.submit.simple({ transaction: tx, senderAuthenticator: auth });
      await client.aptos.waitForTransaction({ transactionHash: pending.hash });
      return pending.hash;
    })();

    const txHash = await withTimeout(task, 15_000, "recordOnChainAttestation");
    log("INFO", "On-Chain Move attestation recorded successfully", { txHash, blobName });
    return { txHash, status: "confirmed" };
  } catch (err: any) {
    log("WARN", "On-Chain Move attestation skipped / degraded gracefully", {
      error: err.message,
      blobName,
    });
    return { status: "failed", error: err.message };
  }
}

async function uploadFile(filePath: string): Promise<void> {
  const filename = path.basename(filePath);

  if (processing.has(filename)) return;
  processing.add(filename);

  if (Date.now() < gasPauseUntil) {
    log("INFO", "[GAS GUARD] Upload deferred due to gas safety cooldown", { file: filename });
    processing.delete(filename);
    return;
  }

  const currentBalance = await getSignerBalanceApt().catch(() => 0);
  if (currentBalance < cfg.minSignerBalanceApt) {
    gasPauseUntil = Date.now() + cfg.balanceCacheTtlMs;
    log("WARN", `[GAS GUARD] Signer balance (${currentBalance.toFixed(4)} APT) below safety floor (${cfg.minSignerBalanceApt} APT). Deferring upload.`, {
      file: filename,
      currentBalanceApt: currentBalance,
      minRequiredApt: cfg.minSignerBalanceApt,
      cooldownSecs: cfg.balanceCacheTtlMs / 1000,
    });
    if (process.env.SHELBY_AUTO_FAUCET === "true") {
      await fundSignerOnce();
    }
    processing.delete(filename);
    return;
  }

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

    let recordCount = 0;
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

      // 1. Resolve recordCount from companion metadata if available (for .json.gz, .parquet, .json)
      const metaCandidates = [
        filePath.replace(/\.json(\.gz)?$/, "_meta.json"),
        filePath.replace(/\.parquet$/, "_meta.json"),
        filePath.replace(/\.tar\.gz$/, "_meta.json"),
      ];
      for (const mPath of metaCandidates) {
        if (fs.existsSync(mPath)) {
          try {
            const meta = JSON.parse(fs.readFileSync(mPath, "utf8"));
            if (typeof meta.record_count === "number" && meta.record_count > 0) {
              recordCount = meta.record_count;
              break;
            }
            if (typeof meta.total_records === "number" && meta.total_records > 0) {
              recordCount = meta.total_records;
              break;
            }
          } catch {}
        }
      }

      // 2. Fallback to parsing raw JSON if not binary and recordCount still unset
      if (recordCount === 0 && !filename.endsWith(".gz") && !filename.endsWith(".parquet") && !filename.endsWith(".enc")) {
        try {
          const parsed = JSON.parse(content.toString("utf8"));
          if (Array.isArray(parsed.records)) {
            recordCount = parsed.records.length;
          }
        } catch {}
      }
    }

    const merkleRootHex = crypto.createHash("sha256").update(content).digest("hex");

    if (client && "initializeAccount" in client) {
      await (client as any).initializeAccount({ signer });
    }

    const location = SHELBY_LOCATION_HINT;
    const uploadOptions = location
      ? ({ selectedLocation: location, locationHint: location } as any)
      : undefined;

    await client.upload({
      blobData: content,
      signer,
      blobName,
      options: uploadOptions,
    } as any);

    content = null;

    log("INFO", "Upload success", { file: filename, blobName, encrypted: isDepth });

    // On-Chain Attestation via Aptos Move Smart Contract (graceful degradation)
    const attestation = await recordOnChainAttestation(
      blobName,
      merkleRootHex,
      isDepth ? "depth_archive" : "market_snapshot",
      recordCount
    );

    const destUploadedPath = path.join(cfg.uploadedDir, filename);
    fs.renameSync(filePath, destUploadedPath);
    const companionMeta = filePath.replace(/\.json(\.gz)?$/, "_meta.json");
    if (fs.existsSync(companionMeta)) {
      try {
        const metaBasename = path.basename(companionMeta);
        const metaBlobName = `${prefix}/${metaBasename}`;
        const metaContent = fs.readFileSync(companionMeta);
        await client.upload({
          blobData: metaContent,
          signer,
          blobName: metaBlobName,
          options: uploadOptions,
        } as any);
        log("INFO", "Uploaded companion metadata blob to Shelby Hot Storage", { blobName: metaBlobName });
        const metaMerkle = crypto.createHash("sha256").update(metaContent).digest("hex");
        await recordUpload(
          metaBasename,
          true,
          "snapshot",
          metaBlobName,
          undefined,
          "",
          metaContent.length,
          metaMerkle
        );
      } catch (metaErr: any) {
        log("WARN", "Companion metadata upload to Shelby Hot Storage skipped", { error: metaErr.message });
      }
      try {
        fs.renameSync(companionMeta, path.join(cfg.uploadedDir, path.basename(companionMeta)));
      } catch {}
    }
    retryCount.delete(filename);

    await recordUpload(
      filename,
      true,
      isDepth ? "depth" : "snapshot",
      blobName,
      encryptionKeyHex,
      "",
      payloadSize,
      merkleRootHex,
      attestation.txHash,
      attestation.status
    );

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
        const companionMetaFail = filePath.replace(/\.json(\.gz)?$/, "_meta.json");
        if (fs.existsSync(companionMetaFail)) {
          try {
            fs.renameSync(companionMetaFail, path.join(cfg.failedDir, path.basename(companionMetaFail)));
          } catch {}
        }
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

const WATCH_REGEX = /^(snapshot_.*|depth_.*)\.(json|json\.gz|parquet|tar\.gz)$/;

function getPendingSnapshots(): SnapshotFile[] {
  try {
    const files = fs
      .readdirSync(cfg.watchDir)
      .filter((f) => WATCH_REGEX.test(f) && f !== "snapshot_state.json" && !f.endsWith("_meta.json"));

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
          const companionMeta = s.path.replace(/\.json(\.gz)?$/, "_meta.json");
          if (fs.existsSync(companionMeta)) {
            try {
              fs.renameSync(companionMeta, path.join(cfg.failedDir, path.basename(companionMeta)));
            } catch {}
          }
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
  if (!WATCH_REGEX.test(filename) || filename === "snapshot_state.json" || filename.endsWith("_meta.json")) return;
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
      .filter((f) => WATCH_REGEX.test(f) && f !== "snapshot_state.json" && !f.endsWith("_meta.json"));

    if (failedFiles.length === 0) return;

    log("INFO", `Auto-Recovery: Found ${failedFiles.length} file(s) in failed/, reclaiming back to pending/`);
    for (const f of failedFiles) {
      const src = path.join(cfg.failedDir, f);
      const dst = path.join(cfg.watchDir, f);
      try {
        fs.renameSync(src, dst);
        const companionMeta = src.replace(/\.json(\.gz)?$/, "_meta.json");
        if (fs.existsSync(companionMeta)) {
          try {
            fs.renameSync(companionMeta, path.join(cfg.watchDir, path.basename(companionMeta)));
          } catch {}
        }
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
  network: cfg.networkName,
  networkType: cfg.networkType,
  contractAddress: cfg.contractAddress,
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
