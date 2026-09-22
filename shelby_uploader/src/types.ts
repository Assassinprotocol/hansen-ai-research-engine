export interface SnapshotFile {
  name: string;
  path: string;
  mtime: number;
}

export interface UploadResult {
  success: boolean;
  file: string;
  detail?: string;
}

export interface UploaderConfig {
  envPath: string;
  keyFile: string;
  watchDir: string;
  uploadedDir: string;
  failedDir: string;
  trackerFile: string;
  maxRetries: number;
  maxPending: number;
  scanIntervalMs: number;
  rpcUrl: string;
  streamThresholdBytes: number;
  verifyInitialDelayMs: number;
  verifyMaxRetries: number;
  maxUploadedDepthKeep: number;
  maxUploadedSnapshotsKeep: number;
  contractAddress: string;
}

export interface TrackerEntry {
  file: string;
  time: string;
  dataType?: "snapshot" | "depth";
  blobName?: string;
  encryptionKey?: string;
  detail?: string;
  verified?: boolean;
  verifiedAt?: string;
  verifyLatencyMs?: number;
  verifyStatus?: number | string;
  verifyError?: string;
  sizeBytes?: number;
  remoteSizeBytes?: number;
  merkleRootHex?: string;
  onchainTxHash?: string;
  onchainStatus?: "confirmed" | "failed" | "skipped";
}

export interface VerificationTask {
  filename: string;
  blobName: string;
  isDepth: boolean;
  localSize: number;
  attempts: number;
  nextAttemptAt: number;
}

export interface TrackerData {
  uploads: TrackerEntry[];
  failed: TrackerEntry[];
}

