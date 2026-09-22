#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import sys
import urllib.parse
import urllib.request
import urllib.error

DEFAULT_ACCOUNT = os.environ.get(
    "HANSEN_REGISTRY_ADDRESS",
    os.environ.get("SHELBY_ACCOUNT", "0x797570358c2208ce0e225f07fe727174c9cc4500072967dd963e645c95c2a07d"),
)
DEFAULT_RPC_URL = os.environ.get("SHELBY_RPC_URL", "https://shelby.shelbynet.shelby.xyz/shelby")
DEFAULT_APTOS_RPC = os.environ.get("APTOS_RPC_URL", "https://api.shelbynet.shelby.xyz/v1")


def get_default_api_key():
    return os.environ.get("SHELBY_API_KEY")


def build_blob_url(base_url: str, account: str, blob_name: str) -> str:
    account_clean = account.strip()
    if not account_clean.startswith("0x"):
        account_clean = "0x" + account_clean
    encoded_account = urllib.parse.quote(account_clean, safe="")
    encoded_blob_name = urllib.parse.quote(blob_name, safe="/")
    return f"{base_url.rstrip('/')}/v1/blobs/{encoded_account}/{encoded_blob_name}"


def get_headers(api_key: str = None, extra_headers: dict = None) -> dict:
    headers = {"User-Agent": "HansenShelbyReader/1.0"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    if extra_headers:
        headers.update(extra_headers)
    return headers


def cmd_inspect(args):
    url = build_blob_url(args.rpc, args.account, args.blob)
    print(f"[*] Target Endpoint: {url}")
    print(f"[*] Blob Name:       {args.blob}")
    print(f"[*] Account:         {args.account}")

    headers = get_headers(args.api_key, {"Range": "bytes=0-0"})
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=args.timeout) as resp:
            content_range = resp.headers.get("Content-Range", "")
            content_length = resp.headers.get("Content-Length", "")
            status = resp.status
            total_size = content_range.split("/")[-1] if "/" in content_range else "unknown"
            print(f"[+] Status:         HTTP {status} (OK)")
            print(f"[+] Content-Range:  {content_range}")
            print(f"[+] Total Size:     {total_size} bytes")
            print(f"[+] Content-Type:   {resp.headers.get('Content-Type', 'unknown')}")
            for k, v in resp.headers.items():
                if k.lower().startswith("x-shelby"):
                    print(f"[+] {k}: {v}")
    except urllib.error.HTTPError as e:
        print(f"[-] HTTP Error {e.code}: {e.reason}")
        sys.exit(1)
    except Exception as e:
        print(f"[-] Connection Error: {e}")
        sys.exit(1)


def cmd_range(args):
    url = build_blob_url(args.rpc, args.account, args.blob)
    range_header = f"bytes={args.start}-{args.end}"
    print(f"[*] Fetching byte range [{range_header}] from: {url}")

    headers = get_headers(args.api_key, {"Range": range_header})
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=args.timeout) as resp:
            data = resp.read()
            print(f"[+] Received {len(data)} bytes (HTTP {resp.status})")
            if args.out:
                with open(args.out, "wb") as f:
                    f.write(data)
                print(f"[+] Saved slice to: {args.out}")
            else:
                preview = data[:64].hex()
                print(f"[+] First {min(len(data), 64)} bytes (hex): {preview}")
                try:
                    text_preview = data[:128].decode("utf-8", errors="replace")
                    print(f"[+] Text preview:\n{text_preview}")
                except Exception:
                    pass
    except urllib.error.HTTPError as e:
        print(f"[-] HTTP Error {e.code}: {e.reason}")
        sys.exit(1)
    except Exception as e:
        print(f"[-] Error: {e}")
        sys.exit(1)


def cmd_download(args):
    url = build_blob_url(args.rpc, args.account, args.blob)
    dest_path = args.out or os.path.basename(args.blob)
    print(f"[*] Streaming download from: {url}")
    print(f"[*] Destination: {dest_path}")

    headers = get_headers(args.api_key)
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=args.timeout) as resp:
            total_size = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            hasher = hashlib.sha256()

            with open(dest_path, "wb") as f:
                while True:
                    chunk = resp.read(64 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
                    hasher.update(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        pct = (downloaded / total_size) * 100
                        print(f"\r[*] Progress: {downloaded}/{total_size} bytes ({pct:.1f}%)", end="", flush=True)

            print(f"\n[+] Download completed successfully!")
            print(f"[+] File Size:  {downloaded} bytes")
            print(f"[+] SHA-256:    {hasher.hexdigest()}")
    except urllib.error.HTTPError as e:
        print(f"\n[-] HTTP Error {e.code}: {e.reason}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[-] Download Failed: {e}")
        sys.exit(1)


def cmd_verify(args):
    url = build_blob_url(args.rpc, args.account, args.blob)
    print(f"[*] Verifying blob integrity: {url}")

    headers = get_headers(args.api_key)
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=args.timeout) as resp:
            hasher = hashlib.sha256()
            total_bytes = 0
            while True:
                chunk = resp.read(64 * 1024)
                if not chunk:
                    break
                hasher.update(chunk)
                total_bytes += len(chunk)

            calculated_hash = hasher.hexdigest()
            print(f"[+] Blob Size: {total_bytes} bytes")
            print(f"[+] SHA-256:   {calculated_hash}")

            if args.expected:
                if calculated_hash.lower() == args.expected.lower():
                    print("[+] INTEGRITY CHECK PASSED: Hash matches expected value.")
                else:
                    print(f"[-] INTEGRITY CHECK FAILED!")
                    print(f"    Expected:   {args.expected}")
                    print(f"    Calculated: {calculated_hash}")
                    sys.exit(2)
    except urllib.error.HTTPError as e:
        print(f"[-] HTTP Error {e.code}: {e.reason}")
        sys.exit(1)
    except Exception as e:
        print(f"[-] Verification Error: {e}")
        sys.exit(1)


def cmd_decrypt(args):
    key_hex = args.key.strip()
    if len(key_hex) != 64:
        print("[-] Error: Key must be a 64-character hex string (32 bytes / 256 bits).")
        sys.exit(1)
    try:
        key = bytes.fromhex(key_hex)
    except ValueError as e:
        print(f"[-] Invalid key hex: {e}")
        sys.exit(1)

    if os.path.exists(args.source):
        print(f"[*] Reading encrypted blob from local file: {args.source}")
        with open(args.source, "rb") as f:
            packed = f.read()
    else:
        url = build_blob_url(args.rpc, args.account, args.source)
        print(f"[*] Fetching encrypted blob from Shelby: {url}")
        headers = get_headers(args.api_key)
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=args.timeout) as resp:
                packed = resp.read()
        except urllib.error.HTTPError as e:
            print(f"[-] HTTP Error {e.code}: {e.reason}")
            sys.exit(1)
        except Exception as e:
            print(f"[-] Download Failed: {e}")
            sys.exit(1)

    if len(packed) < 28:
        print(f"[-] Error: Payload too short ({len(packed)} bytes) to contain IV (12) + Tag (16).")
        sys.exit(1)

    iv = packed[:12]
    tag = packed[12:28]
    ciphertext = packed[28:]

    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    try:
        aesgcm = AESGCM(key)
        decrypted = aesgcm.decrypt(iv, ciphertext + tag, b"hansen_depth_v1")
        print(f"[+] Decryption successful! ({len(decrypted)} bytes)")
    except Exception as e:
        print(f"[-] Decryption failed (Authentication tag mismatch or invalid key): {e}")
        sys.exit(2)

    dest_path = args.out
    if not dest_path:
        base = os.path.basename(args.source)
        if base.endswith(".enc"):
            dest_path = base[:-4]
        else:
            dest_path = base + ".decrypted"

    with open(dest_path, "wb") as f:
        f.write(decrypted)
    print(f"[+] Saved plaintext to: {dest_path}")


def cmd_onchain(args):
    aptos_rpc = args.aptos_rpc.rstrip("/")
    account = args.account.strip()
    if not account.startswith("0x"):
        account = "0x" + account
    contract_addr = args.contract.strip() if args.contract else account
    if not contract_addr.startswith("0x"):
        contract_addr = "0x" + contract_addr

    print("=" * 68)
    print("  HANSEN ENGINE - ON-CHAIN ATTESTATION VERIFIER (APTOS MOVE)")
    print("=" * 68)
    print(f"[*] Aptos RPC Endpoint: {aptos_rpc}")
    print(f"[*] Move Module:        {contract_addr}::registry")
    print(f"[*] Registry Admin:     {account}")
    print(f"[*] Record ID:          #{args.record_id}")
    print("-" * 68)

    view_url = f"{aptos_rpc}/view"
    headers = {"Content-Type": "application/json", "User-Agent": "HansenShelbyReader/1.0"}

    view_payload = {
        "function": f"{contract_addr}::registry::get_snapshot_record",
        "type_arguments": [],
        "arguments": [account, str(args.record_id)],
    }

    try:
        req_data = json.dumps(view_payload).encode("utf-8")
        req = urllib.request.Request(view_url, data=req_data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=args.timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"[-] Aptos RPC HTTP Error {e.code}: {e.reason}")
        print(f"    Details: {body}")
        sys.exit(1)
    except Exception as e:
        print(f"[-] Connection Error to Aptos Node: {e}")
        sys.exit(1)

    if not data or len(data) < 5:
        print(f"[-] Unexpected view response structure: {data}")
        sys.exit(1)

    raw_blob_name, raw_merkle_root, raw_ts, raw_data_type, raw_count = data[0], data[1], data[2], data[3], data[4]

    def decode_vec_u8(val):
        if isinstance(val, str) and val.startswith("0x"):
            return bytes.fromhex(val[2:])
        elif isinstance(val, list):
            return bytes(val)
        return str(val).encode("utf-8")

    blob_name = decode_vec_u8(raw_blob_name).decode("utf-8", errors="replace")
    merkle_bytes = decode_vec_u8(raw_merkle_root)
    merkle_root_hex = merkle_bytes.hex()
    timestamp = int(raw_ts)
    data_type = decode_vec_u8(raw_data_type).decode("utf-8", errors="replace")
    record_count = int(raw_count)

    from datetime import datetime, timezone
    dt_str = datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()

    print("[+] ON-CHAIN ATTESTATION CONFIRMED ON LEDGER:")
    print(f"    Record ID:     #{args.record_id}")
    print(f"    Blob Name:     {blob_name}")
    print(f"    Data Type:     {data_type}")
    print(f"    Record Count:  {record_count:,} records")
    print(f"    Timestamp:     {timestamp} ({dt_str})")
    print(f"    Merkle Root:   {merkle_root_hex}")
    print("-" * 68)

    if args.verify_blob:
        print(f"[*] Cross-verifying against Shelby blob: {blob_name}...")
        url = build_blob_url(args.rpc, account, blob_name)
        h_req = get_headers(args.api_key)
        req = urllib.request.Request(url, headers=h_req)
        try:
            with urllib.request.urlopen(req, timeout=args.timeout) as b_resp:
                hasher = hashlib.sha256()
                while True:
                    chunk = b_resp.read(64 * 1024)
                    if not chunk:
                        break
                    hasher.update(chunk)
                blob_hash = hasher.hexdigest()
                print(f"    Calculated Blob SHA-256: {blob_hash}")
                if blob_hash.lower() == merkle_root_hex.lower():
                    print("[+] INTEGRITY CHECK PASSED: On-chain attestation matches Shelby blob digest exactly!")
                else:
                    print("[-] MISMATCH: On-chain hash does NOT match blob hash!")
                    sys.exit(2)
        except Exception as err:
            print(f"[-] Failed to fetch Shelby blob for cross-verification: {err}")


def main():
    default_key = get_default_api_key()
    parser = argparse.ArgumentParser(description="Hansen Engine Shelby Reader & Downstream Query CLI")
    parser.add_argument("--rpc", default=DEFAULT_RPC_URL, help=f"Shelby RPC Base URL (default: {DEFAULT_RPC_URL})")
    parser.add_argument("--account", default=DEFAULT_ACCOUNT, help=f"Aptos Account Address (default: {DEFAULT_ACCOUNT})")
    parser.add_argument("--api-key", default=default_key, help="Shelby API Key (defaults to SHELBY_API_KEY from env)")
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout in seconds (default: 30)")

    subparsers = parser.add_subparsers(dest="command", required=True)

    p_inspect = subparsers.add_parser("inspect", help="Inspect blob HTTP headers and metadata")
    p_inspect.add_argument("blob", help="Blob name in Shelby")

    p_range = subparsers.add_parser("range", help="Fetch byte range slice")
    p_range.add_argument("blob", help="Blob name in Shelby")
    p_range.add_argument("--start", type=int, default=0, help="Start byte offset (default: 0)")
    p_range.add_argument("--end", type=int, default=1024, help="End byte offset (default: 1024)")
    p_range.add_argument("--out", help="Optional output file to save slice")

    p_dl = subparsers.add_parser("download", help="Stream download full blob to disk")
    p_dl.add_argument("blob", help="Blob name in Shelby")
    p_dl.add_argument("--out", help="Output path (defaults to blob filename)")

    p_verify = subparsers.add_parser("verify", help="Stream blob and verify SHA-256 integrity")
    p_verify.add_argument("blob", help="Blob name in Shelby")
    p_verify.add_argument("--expected", help="Expected SHA-256 hash to compare")

    p_dec = subparsers.add_parser("decrypt", help="Decrypt an AES-256-GCM encrypted blob")
    p_dec.add_argument("source", help="Blob name on Shelby or local .enc file path")
    p_dec.add_argument("--key", required=True, help="32-byte hex decryption key")
    p_dec.add_argument("--out", help="Output path for decrypted file")

    p_onchain = subparsers.add_parser("onchain", help="Query on-chain attestation record from Aptos Move contract")
    p_onchain.add_argument("record_id", type=int, help="Record ID in the registry table (1-indexed)")
    p_onchain.add_argument("--contract", default=None, help=f"Contract module address (defaults to --account: {DEFAULT_ACCOUNT})")
    p_onchain.add_argument("--aptos-rpc", default=DEFAULT_APTOS_RPC, help=f"Aptos RPC REST URL (default: {DEFAULT_APTOS_RPC})")
    p_onchain.add_argument("--verify-blob", action="store_true", help="Fetch blob from Shelby and verify on-chain hash matches")

    args = parser.parse_args()
    if args.command == "inspect":
        cmd_inspect(args)
    elif args.command == "range":
        cmd_range(args)
    elif args.command == "download":
        cmd_download(args)
    elif args.command == "verify":
        cmd_verify(args)
    elif args.command == "decrypt":
        cmd_decrypt(args)
    elif args.command == "onchain":
        cmd_onchain(args)


if __name__ == "__main__":
    main()
