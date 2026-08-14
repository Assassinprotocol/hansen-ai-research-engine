import fs from "fs";
import path from "path";
import dotenv from "dotenv";
import chokidar from "chokidar";
import { ShelbyNodeClient } from "@shelby-protocol/sdk/node";
import { Account, Ed25519PrivateKey, Network, PrivateKey, PrivateKeyVariants } from "@aptos-labs/ts-sdk";

// ── Config ──────────────────────────────────────────────────────
const ENV_PATH         = "/home/hansen/AI/hansen_engine/.env";
const KEYFILE          = "/home/hansen/AI/shelby_uploader/.aptos_key";
const WATCH_DIR        = "/home/hansen/AI/hansen_engine/dataset/pending";
const UPLOADED_DIR     = "/home/hansen/AI/hansen_engine/dataset/uploaded";
const FAILED_DIR       = "/home/hansen/AI/hansen_engine/dataset/failed";
const TRACKER_FILE     = "/home/hansen/AI/hansen_engine/data/upload_tracker.json";

const MAX_RETRIES      = 3;
const MAX_PENDING      = 20;
const SCAN_INTERVAL_MS = 60_000;

// ── Load env ────────────────────────────────────────────────────
dotenv.config({ path: ENV_PATH });

const SHELBY_API_KEY = process.env.SHELBY_API_KEY;
if (!SHELBY_API_KEY) {
    console.error("[FATAL] SHELBY_API_KEY not found in", ENV_PATH);
    console.error("Add SHELBY_API_KEY=<your-key> to that file and restart.");
    process.exit(1);
}
const SHELBY_LOCATION_HINT = process.env.SHELBY_LOCATION_HINT || "us-east-1";

// ── Load or generate Aptos signer account ──────────────────────
// Shelby's client.upload() requires a signer: Account (Aptos Ed25519).
// The account pays gas on the Aptos chain used by Shelby testnet.
function loadOrCreateSigner() {
    let hex = process.env.APTOS_PRIVATE_KEY;

    // Fall back to persisted keyfile if env var not set
    if (!hex && fs.existsSync(KEYFILE)) {
        hex = fs.readFileSync(KEYFILE, "utf8").trim();
    }

    // Auto-generate on first run, persist to keyfile
    if (!hex) {
        const fresh = Ed25519PrivateKey.generate();
        hex = fresh.toString();
        fs.writeFileSync(KEYFILE, hex, { mode: 0o600 });
        console.log("[INIT] Generated new Aptos signer key, saved to", KEYFILE);
    }

    // Accept both AIP-80 "ed25519-priv-0x..." and raw "0x..." forms
    let privateKey;
    try {
        const formatted = PrivateKey.formatPrivateKey(hex, PrivateKeyVariants.Ed25519);
        privateKey = new Ed25519PrivateKey(formatted);
    } catch {
        privateKey = new Ed25519PrivateKey(hex);
    }

    const account = Account.fromPrivateKey({ privateKey });
    console.log("[INIT] Aptos signer address:", account.accountAddress.toString());
    return account;
}

const signer = loadOrCreateSigner();

const client = new ShelbyNodeClient({
    network: "shelbynet",
    apiKey: SHELBY_API_KEY,
});

// ── Best-effort testnet funding (non-blocking, runs once at startup) ──
function withTimeout(promise, ms, label) {
    return Promise.race([
        promise,
        new Promise((_, reject) =>
            setTimeout(() => reject(new Error(`${label} timeout after ${ms}ms`)), ms)
        ),
    ]);
}

async function fundSignerOnce() {
    try {
        await withTimeout(
            client.fundAccountWithAPT({
                address: signer.accountAddress,
                amount: 100_000_000,
            }),
            20_000,
            "fundAccountWithAPT"
        );
        log("INFO", "Funded signer with testnet APT");
    } catch (err) {
        log("WARN", "APT funding skipped", { error: err.message });
    }
    try {
        await withTimeout(
            client.fundAccountWithShelbyUSD({
                address: signer.accountAddress,
                amount: 100_000_000,
            }),
            20_000,
            "fundAccountWithShelbyUSD"
        );
        log("INFO", "Funded signer with ShelbyUSD");
    } catch (err) {
        log("WARN", "ShelbyUSD funding skipped", { error: err.message });
    }
}

// ── Ensure directories ─────────────────────────────────────────
for (const dir of [UPLOADED_DIR, FAILED_DIR]) {
    fs.mkdirSync(dir, { recursive: true });
}

// ── State ───────────────────────────────────────────────────────
const retryCount = new Map();   // filename -> attempt count
const processing = new Set();   // filenames currently being uploaded

// ── Logging ─────────────────────────────────────────────────────
function log(level, msg, meta = {}) {
    const ts = new Date().toISOString();
    const extras = Object.keys(meta).length
        ? " " + JSON.stringify(meta)
        : "";
    console.log(`[${ts}] [${level}] ${msg}${extras}`);
}

// ── Tracker persistence ─────────────────────────────────────────
function recordUpload(filename, success, detail = "") {
    try {
        let tracker = { uploads: [], failed: [] };
        if (fs.existsSync(TRACKER_FILE)) {
            tracker = JSON.parse(fs.readFileSync(TRACKER_FILE, "utf8"));
        }
        tracker.uploads ??= [];
        tracker.failed  ??= [];

        const entry = {
            file: filename,
            time: new Date().toISOString(),
            ...(detail ? { detail } : {}),
        };

        if (success) {
            tracker.uploads.push(entry);
        } else {
            tracker.failed.push(entry);
        }

        fs.writeFileSync(TRACKER_FILE, JSON.stringify(tracker, null, 2));
    } catch (err) {
        log("ERROR", "Tracker write failed", { error: err.message });
    }
}

// ── Upload a single file via Shelby testnet API ─────────────────
async function uploadFile(filePath) {
    const filename = path.basename(filePath);

    if (processing.has(filename)) return;
    processing.add(filename);

    const attempts = (retryCount.get(filename) ?? 0) + 1;
    retryCount.set(filename, attempts);

    log("INFO", `Upload attempt ${attempts}/${MAX_RETRIES}`, { file: filename });

    try {
        const content = fs.readFileSync(filePath);

        if (client && 'initializeAccount' in client) {
            await client.initializeAccount({ signer });
        }

        await client.upload({
            blobData: content,
            signer,
            blobName: `hansen_ai/market_pipeline/snapshots/${filename}`,
            expirationMicros: Date.now() * 1000 + 86400000000,
            options: {
                selectedLocation: SHELBY_LOCATION_HINT,
                locationHint: SHELBY_LOCATION_HINT,
            }
        });

        log("INFO", "Upload success", {
            file: filename,
        });

        // Archive then delete original
        fs.copyFileSync(filePath, path.join(UPLOADED_DIR, filename));
        fs.unlinkSync(filePath);
        retryCount.delete(filename);
        recordUpload(filename, true);
    } catch (err) {
        const detail = err.response
            ? `HTTP ${err.response.status}: ${JSON.stringify(err.response.data)}`
            : err.message;

        log("WARN", `Upload failed (attempt ${attempts})`, {
            file: filename,
            error: detail,
        });

        if (attempts >= MAX_RETRIES) {
            log("ERROR", "Max retries reached, moving to failed/", { file: filename });
            try {
                fs.renameSync(filePath, path.join(FAILED_DIR, filename));
            } catch (mvErr) {
                log("ERROR", "Move to failed/ failed", { error: mvErr.message });
            }
            retryCount.delete(filename);
            recordUpload(filename, false, detail);
        }
        // Otherwise: keep file, retry on next scan cycle
    } finally {
        processing.delete(filename);
    }
}

// ── Collect pending snapshot files, sorted newest-first ─────────
function getPendingSnapshots() {
    try {
        const files = fs.readdirSync(WATCH_DIR)
            .filter(f => /^snapshot_.*\.json$/.test(f) && f !== "snapshot_state.json");

        // Sort by mtime descending (newest first)
        const withStats = files.map(f => {
            const full = path.join(WATCH_DIR, f);
            try {
                return { name: f, path: full, mtime: fs.statSync(full).mtimeMs };
            } catch {
                return null;
            }
        }).filter(Boolean);

        withStats.sort((a, b) => b.mtime - a.mtime);

        // Enforce max pending limit — skip oldest
        if (withStats.length > MAX_PENDING) {
            const skipped = withStats.splice(MAX_PENDING);
            for (const s of skipped) {
                log("WARN", "Exceeds max pending, skipping oldest", { file: s.name });
                try {
                    fs.renameSync(s.path, path.join(FAILED_DIR, s.name));
                    recordUpload(s.name, false, "exceeded max pending limit");
                } catch (e) {
                    log("ERROR", "Failed to move excess file", { error: e.message });
                }
            }
        }

        return withStats;
    } catch (err) {
        log("ERROR", "Failed to read watch dir", { error: err.message });
        return [];
    }
}

// ── Scan cycle ──────────────────────────────────────────────────
async function scan() {
    const snapshots = getPendingSnapshots();

    if (snapshots.length === 0) return;

    log("INFO", `Scan found ${snapshots.length} pending snapshot(s)`);

    for (const snap of snapshots) {
        await uploadFile(snap.path);
    }
}

// ── File watcher (triggers immediate upload on new files) ───────
const watcher = chokidar.watch(WATCH_DIR, {
    persistent: true,
    ignoreInitial: true,
    depth: 0,
    awaitWriteFinish: { stabilityThreshold: 2000, pollInterval: 500 },
});

watcher.on("add", async (filePath) => {
    const filename = path.basename(filePath);
    if (!/^snapshot_.*\.json$/.test(filename)) return;
    if (filename === "snapshot_state.json") return;

    log("INFO", "New snapshot detected", { file: filename });
    await uploadFile(filePath);
});

watcher.on("error", (err) => {
    log("ERROR", "Watcher error", { error: err.message });
});

// ── Start ───────────────────────────────────────────────────────
log("INFO", "Shelby uploader started", {
    watchDir: WATCH_DIR,
    uploadedDir: UPLOADED_DIR,
    failedDir: FAILED_DIR,
    maxRetries: MAX_RETRIES,
    maxPending: MAX_PENDING,
    scanInterval: `${SCAN_INTERVAL_MS / 1000}s`,
});

// Fund signer once (non-blocking; uploads can start immediately).
// The scan runs after funding attempt so the first upload has gas if funding succeeded.
(async () => {
    await fundSignerOnce();
    scan();
})();
setInterval(scan, SCAN_INTERVAL_MS);
