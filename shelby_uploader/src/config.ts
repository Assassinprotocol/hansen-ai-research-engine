import path from "path";
import dotenv from "dotenv";
import type { UploaderConfig } from "./types.js";
import { log } from "./logger.js";
import { resolveNetworkConfig } from "./network.js";

export function loadConfig(): UploaderConfig {
  const baseDir = process.env.HANSEN_BASE_DIR || path.resolve(process.cwd(), "..");
  const envPath = process.env.SHELBY_ENV_PATH || path.resolve(process.cwd(), ".env");
  dotenv.config({ path: envPath });
  const net = resolveNetworkConfig();

  return {
    envPath,
    keyFile: process.env.SHELBY_KEY_FILE || path.resolve(process.cwd(), ".aptos_key"),
    watchDir: process.env.SHELBY_WATCH_DIR || path.join(baseDir, "dataset/pending"),
    uploadedDir: process.env.SHELBY_UPLOADED_DIR || path.join(baseDir, "dataset/uploaded"),
    failedDir: process.env.SHELBY_FAILED_DIR || path.join(baseDir, "dataset/failed"),
    trackerFile: process.env.SHELBY_TRACKER_FILE || path.join(baseDir, "data/upload_tracker.json"),
    maxRetries: 3,
    maxPending: 20,
    scanIntervalMs: 60_000,
    rpcUrl: net.rpcUrl,
    aptosRpcUrl: net.aptosRpcUrl,
    networkName: net.name,
    networkType: net.networkType,
    locationHint: net.locationHint,
    streamThresholdBytes: Number(process.env.SHELBY_STREAM_THRESHOLD_BYTES) || 20 * 1024 * 1024,
    verifyInitialDelayMs: Number(process.env.SHELBY_VERIFY_DELAY_MS) || 20_000,
    verifyMaxRetries: 3,
    maxUploadedDepthKeep: 2,
    maxUploadedSnapshotsKeep: 30,
    contractAddress: net.contractAddress,
    minSignerBalanceApt: Number(process.env.SHELBY_MIN_GAS_APT) || 2.1,
    balanceCacheTtlMs: Number(process.env.SHELBY_BALANCE_CACHE_TTL_MS) || 300_000,
    faucetCooldownMs: Number(process.env.SHELBY_FAUCET_COOLDOWN_MS) || 3600_000,
    maxAttestationGasAmount: Number(process.env.SHELBY_MAX_ATTESTATION_GAS) || 5_000,
  };
}

export function requireEnv(key: string, fallbackKey?: string): string {
  const val = process.env[key] ?? (fallbackKey ? process.env[fallbackKey] : undefined);
  if (!val) {
    const keys = fallbackKey ? `${key} or ${fallbackKey}` : key;
    log("ERROR", `Required env var missing: ${keys}`);
    process.exit(1);
  }
  return val;
}
