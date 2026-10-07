type LogLevel = "INFO" | "WARN" | "ERROR" | "DEBUG";

function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  const val = (bytes / Math.pow(1024, i)).toFixed(2);
  const formattedNumber = bytes.toLocaleString("en-US");
  return i >= 2 ? `${val} ${units[i]} (${formattedNumber} bytes)` : `${val} ${units[i]}`;
}

function getLocalTime(): string {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

export function log(level: LogLevel, msg: string, meta: Record<string, unknown> = {}): void {
  const timeStr = getLocalTime();

  // Detect file type
  const filename = String(meta.file || meta.filename || meta.blobName || "");
  const isDepth = filename.includes("depth_") || filename.endsWith(".tar.gz") || filename.endsWith(".enc") || meta.encrypted === true;
  const isSnapshot = filename.includes("snapshot_") || filename.endsWith(".json");

  let tag = "SHELBY";
  if (isDepth) {
    tag = "SHELBY:DEPTH";
  } else if (isSnapshot) {
    tag = "SHELBY:SNAPSHOT";
  }

  const levelTag = level !== "INFO" ? `:${level}` : "";
  const header = `[${timeStr}] [${tag}${levelTag}]`;

  // 1. Upload Success
  if (msg === "Upload success") {
    const file = String(meta.file || "");
    const blob = String(meta.blobName || "");
    const typeLabel = isDepth ? "DEPTH (AES-256-GCM Encrypted)" : "SNAPSHOT (RAW / Unencrypted)";
    const modeLabel = isDepth ? "Ciphertext Stream" : "Plaintext";
    console.log(`${header} Upload SUCCESS`);
    console.log(`  ├─ Type        : ${typeLabel}`);
    console.log(`  ├─ Target File : ${file}`);
    console.log(`  ├─ Blob Path   : ${blob}`);
    console.log(`  └─ Mode        : ${modeLabel}`);
    return;
  }

  // 2. Verification Success
  if (msg === "RAW Verification SUCCESS") {
    const file = String(meta.file || "");
    const latency = String(meta.latencyMs || "");
    const remoteSize = typeof meta.remoteSize === "number" ? formatBytes(meta.remoteSize) : String(meta.remoteSize || "-");
    const typeLabel = isDepth ? "DEPTH (Encrypted)" : "SNAPSHOT (RAW)";
    console.log(`${header} Verification SUCCESS (HTTP ${meta.status || 206})`);
    console.log(`  ├─ Type        : ${typeLabel}`);
    console.log(`  ├─ Target File : ${file}`);
    console.log(`  ├─ Probe Time  : ${latency} latency`);
    console.log(`  ├─ Remote Size : ${remoteSize}`);
    console.log(`  └─ Durability  : Confirmed on Shelbynet`);
    return;
  }

  // 3. Upload Attempt
  if (msg.startsWith("Upload attempt")) {
    const file = String(meta.file || "");
    const blob = String(meta.blobName || "");
    console.log(`${header} ${msg}`);
    console.log(`  ├─ Target File : ${file}`);
    console.log(`  └─ Blob Path   : ${blob}`);
    return;
  }

  // 4. Enqueued for Verification
  if (msg === "Enqueued RAW verification task") {
    const file = String(meta.file || "");
    const delaySec = typeof meta.delayMs === "number" ? `${Math.round(meta.delayMs / 1000)}s` : String(meta.delayMs || "");
    console.log(`${header} Enqueued for Verification`);
    console.log(`  ├─ Target File : ${file}`);
    console.log(`  └─ Schedule    : Probe in ${delaySec}`);
    return;
  }

  // 5. Verification Probe Attempt
  if (msg.startsWith("Running RAW verification probe")) {
    const file = String(meta.file || "");
    console.log(`${header} ${msg}`);
    console.log(`  └─ Target File : ${file}`);
    return;
  }

  // 6. Stream Encryption Engaged
  if (msg === "Engaging single-buffer stream encryption") {
    const file = String(meta.file || "");
    const size = meta.sizeMb ? `${meta.sizeMb} MB` : "-";
    console.log(`${header} Stream Encryption Engaged`);
    console.log(`  ├─ Cipher      : AES-256-GCM`);
    console.log(`  ├─ Source File : ${file}`);
    console.log(`  └─ Plaintext   : ${size}`);
    return;
  }

  // 7. Encrypted Payload Summary
  if (msg === "Encrypted depth payload (AES-256-GCM)") {
    const file = String(meta.file || "");
    const orig = typeof meta.origSize === "number" ? formatBytes(meta.origSize) : String(meta.origSize || "-");
    const enc = typeof meta.encSize === "number" ? formatBytes(meta.encSize) : String(meta.encSize || "-");
    console.log(`${header} Payload Encrypted (AES-256-GCM)`);
    console.log(`  ├─ Source File : ${file}`);
    console.log(`  ├─ Original    : ${orig}`);
    console.log(`  └─ Ciphertext  : ${enc}`);
    return;
  }

  // 8. Gated Cleanup
  if (msg === "Gated Cleanup: Unlinked verified depth archive from local disk") {
    const file = String(meta.file || "");
    console.log(`${header} Gated Cleanup Complete`);
    console.log(`  ├─ Unlinked    : ${file} (Local disk freed)`);
    console.log(`  └─ Safety      : Remote blob verified and durable`);
    return;
  }

  // 9. Signer Balance Checked
  if (msg === "Signer balance checked") {
    console.log(`${header} Signer Balance Checked`);
    console.log(`  ├─ Address     : ${meta.address || "-"}`);
    console.log(`  └─ Balance     : ${meta.aptBalance || "-"} (Shelbynet)`);
    return;
  }

  // 10. Engine Started
  if (msg === "Shelby uploader started") {
    console.log(`${header} Shelby Uploader Engine Started`);
    console.log(`  ├─ Watch Dir   : ${meta.watchDir || "-"}`);
    console.log(`  ├─ Uploaded Dir: ${meta.uploadedDir || "-"}`);
    console.log(`  ├─ Failed Dir  : ${meta.failedDir || "-"}`);
    console.log(`  └─ Policy      : Max ${meta.maxPending} pending | Scan ${meta.scanInterval} | Recovery ${meta.autoRecoveryInterval}`);
    return;
  }

  // Single file shortcut (e.g. New snapshot detected)
  const keys = Object.keys(meta);
  if (keys.length === 1 && (keys[0] === "file" || keys[0] === "filename")) {
    console.log(`${header} ${msg}: ${meta[keys[0]]}`);
    return;
  }

  // Generic multi-key tree formatting
  if (keys.length > 0) {
    console.log(`${header} ${msg}`);
    keys.forEach((k, idx) => {
      const isLast = idx === keys.length - 1;
      const branch = isLast ? "  └─" : "  ├─";
      let val = meta[k];
      if (typeof val === "object" && val !== null) {
        val = JSON.stringify(val);
      }
      const label = k.padEnd(14, " ");
      console.log(`${branch} ${label} : ${val}`);
    });
    return;
  }

  // Simple message with no meta
  console.log(`${header} ${msg}`);
}
