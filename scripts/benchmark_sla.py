#!/usr/bin/env python3
"""
Hansen AI Research Engine — Shelby Hot Storage Empirical SLA Benchmark
Probes distributed storage nodes for availability and byte-range slice latency.
"""

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
import urllib.error

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "modules"))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from modules.network_config import get_network_config
except ImportError:
    try:
        from network_config import get_network_config
    except ImportError:
        def get_network_config(target=None):
            return {
                "name": "shelbynet",
                "network_type": "shelbynet",
                "rpc_url": os.environ.get("SHELBY_RPC_URL", "https://shelby.shelbynet.shelby.xyz/shelby"),
                "aptos_rpc_url": os.environ.get("APTOS_RPC_URL", "https://api.shelbynet.shelby.xyz/v1"),
                "contract_address": os.environ.get("HANSEN_REGISTRY_ADDRESS", os.environ.get("SHELBY_ACCOUNT", "0x797570358c2208ce0e225f07fe727174c9cc4500072967dd963e645c95c2a07d")),
            }

_NET = get_network_config()
DEFAULT_ACCOUNT = _NET.get("contract_address", "0x797570358c2208ce0e225f07fe727174c9cc4500072967dd963e645c95c2a07d")
DEFAULT_RPC_URL = _NET.get("rpc_url", "https://shelby.shelbynet.shelby.xyz/shelby")
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_TRACKER_FILE = os.path.join(BASE_DIR, "data", "upload_tracker.json")
DEFAULT_REPORT_FILE = os.path.join(BASE_DIR, "data", "sla_benchmark_latest.json")

# Verified active sample blobs on Shelbynet
VERIFIED_PUBLIC_SAMPLE_BLOBS = [
    "hansen_ai/market_pipeline/snapshots/snapshot_20261009_165655_meta.json",
    "hansen_ai/market_pipeline/snapshots/snapshot_20261009_093401_meta.json",
    "hansen_ai/market_pipeline/snapshots/snapshot_20261009_012815_meta.json",
]


def build_blob_url(base_url: str, account: str, blob_name: str) -> str:
    account_clean = account.strip()
    if not account_clean.startswith("0x"):
        account_clean = "0x" + account_clean
    encoded_account = urllib.parse.quote(account_clean, safe="")
    encoded_blob_name = urllib.parse.quote(blob_name, safe="/")
    return f"{base_url.rstrip('/')}/v1/blobs/{encoded_account}/{encoded_blob_name}"


def get_headers(api_key: str = None, extra_headers: dict = None) -> dict:
    headers = {"User-Agent": "HansenSLABenchmark/1.0"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    if extra_headers:
        headers.update(extra_headers)
    return headers


def load_tracker_blob_names(tracker_path: str, count: int) -> list:
    """
    Safely extracts ONLY blob names from tracker without exposing or copying
    any internal operational metadata, keys, or file paths.
    """
    if not tracker_path or not os.path.exists(tracker_path):
        return []
    try:
        with open(tracker_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        uploads = data.get("uploads", [])
        verified_names = []
        for u in uploads:
            if u.get("verified") is True and u.get("blobName"):
                name = str(u["blobName"]).strip()
                if name:
                    verified_names.append(name)
        return verified_names[-count:]
    except Exception:
        return []


def probe_blob(url: str, api_key: str = None, timeout: int = 15) -> dict:
    result = {
        "ttfb_ms": None,
        "throughput_mb_s": None,
        "status_code": None,
        "verified_206": False,
        "remote_size": None,
        "error": None,
    }

    # Primary probe: 32-byte range slice (TTFB SLA verification)
    headers = get_headers(api_key, {"Range": "bytes=0-31"})
    req = urllib.request.Request(url, headers=headers)

    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            t1 = time.perf_counter()
            elapsed_ms = round((t1 - t0) * 1000, 2)
            result["ttfb_ms"] = elapsed_ms
            result["status_code"] = resp.status
            result["verified_206"] = (resp.status == 206)

            crange = resp.headers.get("Content-Range", "")
            if "/" in crange:
                try:
                    result["remote_size"] = int(crange.split("/")[-1])
                except Exception:
                    pass
    except urllib.error.HTTPError as e:
        result["status_code"] = e.code
        if e.code == 401:
            result["error"] = "HTTP 401: Unauthorized (Shelby RPC in Private Beta requires SHELBY_API_KEY environment variable or --api-key)"
        else:
            result["error"] = f"HTTP {e.code}: {e.reason}"
        return result
    except Exception as e:
        result["error"] = str(e)
        return result

    # Secondary probe: 256 KB slice for throughput benchmark
    slice_req = urllib.request.Request(url, headers=get_headers(api_key, {"Range": "bytes=0-262143"}))
    t_start = time.perf_counter()
    try:
        with urllib.request.urlopen(slice_req, timeout=timeout) as resp:
            body = resp.read()
            t_end = time.perf_counter()
            duration = max(t_end - t_start, 0.0001)
            mb = len(body) / (1024 * 1024)
            result["throughput_mb_s"] = round(mb / duration, 2)
    except Exception:
        pass

    return result


def main():
    parser = argparse.ArgumentParser(description="Hansen AI Shelby Hot Storage Empirical SLA Benchmark")
    parser.add_argument("--network", default=None, help="Target network preset (shelbynet | private_mainnet | testnet | localnet)")
    parser.add_argument("--samples", type=int, default=3, help="Number of recent blobs to sample (default: 3)")
    parser.add_argument("--blob", default=None, help="Specific blob name to benchmark directly")
    parser.add_argument("--tracker", default=DEFAULT_TRACKER_FILE, help=f"Path to local tracker file (default: {DEFAULT_TRACKER_FILE})")
    parser.add_argument("--rpc", default=None, help=f"Shelby RPC Base URL (default: {DEFAULT_RPC_URL})")
    parser.add_argument("--account", default=None, help=f"Aptos Account Address (default: {DEFAULT_ACCOUNT})")
    parser.add_argument("--api-key", default=os.environ.get("SHELBY_API_KEY"), help="Shelby API Key (optional)")
    parser.add_argument("--timeout", type=int, default=15, help="Probe timeout in seconds")
    parser.add_argument("--out", default=DEFAULT_REPORT_FILE, help=f"Output report path (default: {DEFAULT_REPORT_FILE})")
    args = parser.parse_args()

    active_net = get_network_config(args.network)
    net_name = active_net.get("name", "shelbynet")
    net_type = active_net.get("network_type", net_name)

    if not args.rpc:
        args.rpc = active_net.get("rpc_url", DEFAULT_RPC_URL)
    if not args.account:
        args.account = active_net.get("contract_address", DEFAULT_ACCOUNT)

    # Auto-load API key from local .env if present and not provided via flag/env
    if not args.api_key:
        env_file = os.path.join(BASE_DIR, ".env")
        if os.path.isfile(env_file):
            try:
                with open(env_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("SHELBY_API_KEY="):
                            args.api_key = line.split("=", 1)[1].strip("'\"\n")
                            break
            except Exception:
                pass

    print("=" * 76)
    print("   HANSEN AI RESEARCH ENGINE — SHELBY HOT STORAGE SLA BENCHMARK")
    print("=" * 76)
    print(f"[*] Network:         {net_name} ({net_type})")
    print(f"[*] Gateway RPC:     {args.rpc}")
    print(f"[*] Signer Account:  {args.account}")

    # Determine targets safely: strictly blob name strings, zero leaked metadata
    if args.blob:
        targets = [args.blob]
        print(f"[*] Target Blob:     {args.blob}")
    else:
        loaded = load_tracker_blob_names(args.tracker, args.samples)
        if loaded:
            targets = loaded
            print(f"[*] Target Source:   Local Tracker ({len(targets)} verified blobs)")
        else:
            targets = VERIFIED_PUBLIC_SAMPLE_BLOBS[:args.samples]
            print(f"[*] Target Source:   Verified Public Snapshots ({len(targets)} blobs)")
    print("-" * 76)

    probes = []
    latencies = []

    for idx, blob_name in enumerate(targets, 1):
        url = build_blob_url(args.rpc, args.account, blob_name)

        print(f"[{idx}/{len(targets)}] Probing: {blob_name}")
        metric = probe_blob(url, args.api_key, args.timeout)

        if metric["ttfb_ms"] is not None:
            latencies.append(metric["ttfb_ms"])
            status_symbol = "✅" if metric["verified_206"] else "⚠️"
            tp_str = f"{metric['throughput_mb_s']} MB/s" if metric['throughput_mb_s'] else "N/A"
            print(f"    {status_symbol} HTTP {metric['status_code']} | Latency: {metric['ttfb_ms']}ms | Throughput: {tp_str}")
        else:
            print(f"    ❌ FAILED: {metric['error']}")

        probes.append({
            "blobName": blob_name,
            "metrics": metric,
        })

    print("=" * 76)
    print("                     BENCHMARK SUMMARY REPORT")
    print("=" * 76)

    valid_count = len(latencies)
    total_count = len(targets)
    availability_pct = round((valid_count / total_count) * 100, 1)

    if latencies:
        latencies.sort()
        min_l = min(latencies)
        max_l = max(latencies)
        avg_l = round(sum(latencies) / len(latencies), 1)
        p95_idx = int(len(latencies) * 0.95)
        p95_l = latencies[p95_idx] if p95_idx < len(latencies) else max_l
        subsecond_rate = round(len([x for x in latencies if x < 1000.0]) / len(latencies) * 100, 1)

        print(f"  • Probed Blobs:             {total_count}")
        print(f"  • Availability (HTTP 206):  {availability_pct}% ({valid_count}/{total_count})")
        print(f"  • Min TTFB Latency:         {min_l} ms")
        print(f"  • Average TTFB Latency:     {avg_l} ms")
        print(f"  • P95 TTFB Latency:         {p95_l} ms")
        print(f"  • Max TTFB Latency:         {max_l} ms")
        print(f"  • Sub-Second SLA Ratio:     {subsecond_rate}% (< 1000ms)")
    else:
        print("  • Availability: 0% (All probes timed out or failed)")
        avg_l = None
        p95_l = None
        subsecond_rate = 0.0

    print("=" * 76)

    # Safe report payload: strictly metrics and public endpoints, zero tokens or keys
    report_payload = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "network": net_name,
        "networkType": net_type,
        "rpcUrl": args.rpc,
        "account": args.account,
        "summary": {
            "totalProbes": total_count,
            "successCount": valid_count,
            "availabilityPct": availability_pct,
            "avgLatencyMs": avg_l,
            "p95LatencyMs": p95_l,
            "subSecondRatio": subsecond_rate,
        },
        "probes": probes,
    }

    try:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(report_payload, f, indent=2)
        print(f"[+] Detailed report saved to: {args.out}")
    except Exception as e:
        print(f"[-] Failed to write report file: {e}")


if __name__ == "__main__":
    main()
