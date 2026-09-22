import dotenv from "dotenv";
import type { UploaderConfig } from "./types.js";
import { log } from "./logger.js";

export function loadConfig(): UploaderConfig {
  const envPath = "/home/hansen/AI/hansen_engine/.env";
  dotenv.config({ path: envPath });
  return {
    envPath,
    keyFile: "/home/hansen/AI/shelby_uploader/.aptos_key",
    watchDir: "/home/hansen/AI/hansen_engine/dataset/pending",
    uploadedDir: "/home/hansen/AI/hansen_engine/dataset/uploaded",
    failedDir: "/home/hansen/AI/hansen_engine/dataset/failed",
    trackerFile: "/home/hansen/AI/hansen_engine/data/upload_tracker.json",
    maxRetries: 3,
    maxPending: 20,
    scanIntervalMs: 60_000,
    rpcUrl: process.env.SHELBY_RPC_URL || "https://shelby.shelbynet.shelby.xyz/shelby",
    streamThresholdBytes: Number(process.env.SHELBY_STREAM_THRESHOLD_BYTES) || 20 * 1024 * 1024,
    verifyInitialDelayMs: Number(process.env.SHELBY_VERIFY_DELAY_MS) || 20_000,
    verifyMaxRetries: 3,
    maxUploadedDepthKeep: 2,
    maxUploadedSnapshotsKeep: 30,
    contractAddress: process.env.HANSEN_REGISTRY_ADDRESS || "0x797570358c2208ce0e225f07fe727174c9cc4500072967dd963e645c95c2a07d",
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
