#!/usr/bin/env python3
"""
Single-pass IPFS -> Bunny pipeline for files named N.json (no padding).
For each n in [start, end]:
  - GET n.json from the gateway
  - If 200, save to temp, immediately PUT to Bunny, then delete local (optional)
  - If 404/timeout, count as "missing"
Stop after --max-missing consecutive misses.
"""

import argparse
import os
import sys
import tempfile
import shutil
from pathlib import Path
from urllib.parse import quote

import requests
from requests.adapters import HTTPAdapter, Retry

# -------------------- Defaults --------------------
DEFAULT_CID = "bafybeifi6awhcvqrzgsh37ribjk62ozzsrekql7p7rqnobuggu5jjl2d2i"
DEFAULT_GATEWAY = "https://ipfs.io"
DEFAULT_START_NUMBER = 1
DEFAULT_END_NUMBER   = 10000
DEFAULT_MAX_MISSING  = 75
DEFAULT_DOWNLOAD_TIMEOUT = 180
DEFAULT_DEST_PATH    = "ape_jsons/"
DEFAULT_DELETE_LOCAL = True

# Bunny via env by default
DEFAULT_STORAGE_ZONE = os.getenv("BUNNY_STORAGE_ZONE", "")
DEFAULT_ACCESS_KEY   = os.getenv("BUNNY_ACCESS_KEY", "")
DEFAULT_REGION_HOST  = os.getenv("BUNNY_REGION_HOST", None)  # e.g. "la.storage.bunnycdn.com"

def make_session():
    s = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=0.6,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "PUT"]
    )
    adapter = HTTPAdapter(max_retries=retries, pool_connections=20, pool_maxsize=20)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    return s

def download_json(session: requests.Session, gateway: str, cid: str, n: int, out_file: Path, timeout: int):
    url = f"{gateway.rstrip('/')}/ipfs/{cid}/{n}.json"
    with session.get(url, stream=True, timeout=timeout) as r:
        if r.status_code != 200:
            return False, r.status_code
        out_file.parent.mkdir(parents=True, exist_ok=True)
        with open(out_file, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024*256):
                if chunk:
                    f.write(chunk)
    return True, 200

def bunny_put(session, storage_zone, access_key, region_host, dest_key, file_path: Path):
    base = region_host.strip() if region_host else "storage.bunnycdn.com"
    url = f"https://{base}/{quote(storage_zone.strip())}/{dest_key}"
    headers = {
        "AccessKey": access_key.strip(),
        "Content-Type": "application/octet-stream"
    }
    with open(file_path, "rb") as f:
        resp = session.put(url, headers=headers, data=f, timeout=180)
    return resp.status_code in (200, 201), resp.status_code, resp.text[:200]

def main():
    ap = argparse.ArgumentParser(description="Single-pass IPFS (N.json) -> Bunny uploader.")
    ap.add_argument("--cid", default=DEFAULT_CID)
    ap.add_argument("--gateway", default=DEFAULT_GATEWAY)
    ap.add_argument("--start-number", type=int, default=DEFAULT_START_NUMBER)
    ap.add_argument("--end-number", type=int, default=DEFAULT_END_NUMBER)
    ap.add_argument("--max-missing", type=int, default=DEFAULT_MAX_MISSING)
    ap.add_argument("--download-timeout", type=int, default=DEFAULT_DOWNLOAD_TIMEOUT)
    ap.add_argument("--dest-path", default=DEFAULT_DEST_PATH)
    ap.add_argument("--delete-local", action="store_true", default=DEFAULT_DELETE_LOCAL)
    # Bunny
    ap.add_argument("--storage-zone", default=DEFAULT_STORAGE_ZONE)
    ap.add_argument("--access-key", default=DEFAULT_ACCESS_KEY)
    ap.add_argument("--region-host", default=DEFAULT_REGION_HOST)

    args = ap.parse_args()

    if not args.storage_zone or not args.access_key:
        print("ERROR: Bunny credentials missing. Set --storage-zone/--access-key or env vars BUNNY_STORAGE_ZONE/BUNNY_ACCESS_KEY.", file=sys.stderr)
        sys.exit(1)

    dest_prefix = args.dest_path.strip()
    if dest_prefix and not dest_prefix.endswith("/"):
        dest_prefix += "/"

    session = make_session()
    tempdir = tempfile.mkdtemp(prefix="ipfs_dl_")
    tempdir_path = Path(tempdir)

    total = args.end_number - args.start_number + 1
    print(f"Single-pass: scanning & uploading {total} candidates: {args.gateway}/ipfs/{args.cid}/N.json")
    print(f"Stopping after {args.max_missing} consecutive misses.")

    consecutive_missing = 0
    found_count = 0
    uploaded_count = 0
    errors_upload = 0

    try:
        for n in range(args.start_number, args.end_number + 1):
            filename = f"{n}.json"
            local_path = tempdir_path / filename

            ok, code = download_json(session, args.gateway, args.cid, n, local_path, args.download_timeout)
            if not ok:
                consecutive_missing += 1
                if n % 25 == 0:
                    print(f"[{n}] missing (HTTP {code}); miss streak={consecutive_missing}")
                if consecutive_missing >= args.max_missing:
                    print(f"Stopping at n={n}: reached {consecutive_missing} consecutive misses.")
                    break
                continue

            # got it
            consecutive_missing = 0
            found_count += 1
            dest_key = f"{dest_prefix}{filename}"
            up_ok, up_code, up_text = bunny_put(session, args.storage_zone, args.access_key, args.region_host, dest_key, local_path)
            if up_ok:
                uploaded_count += 1
                print(f"[{n}] uploaded -> {dest_key}")
                if args.delete_local:
                    try:
                        local_path.unlink(missing_ok=True)
                    except Exception:
                        pass
            else:
                errors_upload += 1
                print(f"[{n}] upload FAILED (HTTP {up_code}): {up_text}", file=sys.stderr)
                # keep local copy for inspection

        print(f"Done. Found: {found_count}, Uploaded: {uploaded_count}, Upload errors: {errors_upload}")
        if errors_upload == 0 and args.delete_local:
            shutil.rmtree(tempdir, ignore_errors=True)
            print("Local temp files deleted.")
        else:
            print(f"Local files kept at: {tempdir}")
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        print(f"Local files kept at: {tempdir}")

if __name__ == "__main__":
    main()