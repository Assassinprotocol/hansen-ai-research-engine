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
}

export interface TrackerEntry {
  file: string;
  time: string;
  detail?: string;
}

export interface TrackerData {
  uploads: TrackerEntry[];
  failed: TrackerEntry[];
}
