#!/usr/bin/env python3
"""
Single-pass IPFS -> Bunny pipeline for files named N.json (no padding).
For each n in [start, end]:
  - Check if file already exists on CDN
  - If not, GET n.json from the gateway
  - If 200, save to temp, immediately PUT to Bunny, then delete local (optional)
  - If 404/timeout, count as "missing"
Stop after --max-missing consecutive misses.
"""

import argparse
import os
import sys
import tempfile
import shutil
import logging
import time
from pathlib import Path
from urllib.parse import quote

import requests
from requests.adapters import HTTPAdapter, Retry

# -------------------- Defaults --------------------
DEFAULT_CID = "bafybeifi6awhcvqrzgsh37ribjk62ozzsrekql7p7rqnobuggu5jjl2d2i"
DEFAULT_GATEWAY = "https://ipfs.io"
DEFAULT_START_NUMBER = 1
DEFAULT_END_NUMBER   = 8888
DEFAULT_MAX_MISSING  = 75
DEFAULT_DOWNLOAD_TIMEOUT = 180
DEFAULT_DEST_PATH    = "hog_jsons/"
DEFAULT_DELETE_LOCAL = True
DEFAULT_LOG_FILE     = "ipfs-to-cdn-hogs.log"

# Bunny via env by default
DEFAULT_STORAGE_ZONE = os.getenv("BUNNY_STORAGE_ZONE", "")
DEFAULT_ACCESS_KEY   = os.getenv("BUNNY_ACCESS_KEY", "")
DEFAULT_REGION_HOST  = os.getenv("BUNNY_REGION_HOST", None)  # e.g. "la.storage.bunnycdn.com"

def setup_logging(log_file):
    """Setup logging to both file and console."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

def make_session():
    s = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=0.6,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "PUT", "HEAD"]
    )
    adapter = HTTPAdapter(max_retries=retries, pool_connections=20, pool_maxsize=20)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    return s

def check_file_exists_on_cdn(session, storage_zone, access_key, region_host, dest_key):
    """Check if a file already exists on Bunny CDN."""
    base = region_host.strip() if region_host else "storage.bunnycdn.com"
    url = f"https://{base}/{quote(storage_zone.strip())}/{dest_key}"
    headers = {
        "AccessKey": access_key.strip(),
    }
    try:
        resp = session.head(url, headers=headers, timeout=30)
        return resp.status_code == 200
    except Exception as e:
        logging.warning(f"Error checking CDN for {dest_key}: {e}")
        return False

def get_existing_files_on_cdn(session, storage_zone, access_key, region_host, dest_prefix, start_num, end_num):
    """Get list of files that already exist on CDN in the given range."""
    existing_files = set()
    base = region_host.strip() if region_host else "storage.bunnycdn.com"
    
    # Check files in batches to avoid overwhelming the CDN
    batch_size = 100
    for batch_start in range(start_num, end_num + 1, batch_size):
        batch_end = min(batch_start + batch_size - 1, end_num)
        
        # Check each file in the batch
        for n in range(batch_start, batch_end + 1):
            filename = f"{n}.json"
            dest_key = f"{dest_prefix}{filename}"
            
            if check_file_exists_on_cdn(session, storage_zone, access_key, region_host, dest_key):
                existing_files.add(n)
                logging.info(f"File {n}.json already exists on CDN")
        
        # Small delay between batches to be nice to the CDN
        time.sleep(0.1)
    
    return existing_files

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
    ap = argparse.ArgumentParser(description="Single-pass IPFS (N.json) -> Bunny uploader with CDN checking.")
    ap.add_argument("--cid", default=DEFAULT_CID)
    ap.add_argument("--gateway", default=DEFAULT_GATEWAY)
    ap.add_argument("--start-number", type=int, default=DEFAULT_START_NUMBER)
    ap.add_argument("--end-number", type=int, default=DEFAULT_END_NUMBER)
    ap.add_argument("--max-missing", type=int, default=DEFAULT_MAX_MISSING)
    ap.add_argument("--download-timeout", type=int, default=DEFAULT_DOWNLOAD_TIMEOUT)
    ap.add_argument("--dest-path", default=DEFAULT_DEST_PATH)
    ap.add_argument("--delete-local", action="store_true", default=DEFAULT_DELETE_LOCAL)
    ap.add_argument("--log-file", default=DEFAULT_LOG_FILE)
    ap.add_argument("--skip-cdn-check", action="store_true", help="Skip checking CDN for existing files")
    # Bunny
    ap.add_argument("--storage-zone", default=DEFAULT_STORAGE_ZONE)
    ap.add_argument("--access-key", default=DEFAULT_ACCESS_KEY)
    ap.add_argument("--region-host", default=DEFAULT_REGION_HOST)

    args = ap.parse_args()

    if not args.storage_zone or not args.access_key:
        print("ERROR: Bunny credentials missing. Set --storage-zone/--access-key or env vars BUNNY_STORAGE_ZONE/BUNNY_ACCESS_KEY.", file=sys.stderr)
        sys.exit(1)

    # Setup logging
    logger = setup_logging(args.log_file)
    logger.info(f"Starting IPFS to CDN upload process")
    logger.info(f"Range: {args.start_number} to {args.end_number}")
    logger.info(f"Gateway: {args.gateway}")
    logger.info(f"CID: {args.cid}")

    dest_prefix = args.dest_path.strip()
    if dest_prefix and not dest_prefix.endswith("/"):
        dest_prefix += "/"

    session = make_session()
    tempdir = tempfile.mkdtemp(prefix="ipfs_dl_")
    tempdir_path = Path(tempdir)

    total = args.end_number - args.start_number + 1
    logger.info(f"Single-pass: scanning & uploading {total} candidates: {args.gateway}/ipfs/{args.cid}/N.json")
    logger.info(f"Stopping after {args.max_missing} consecutive misses.")

    # Check for existing files on CDN
    existing_files = set()
    if not args.skip_cdn_check:
        logger.info("Checking CDN for existing files...")
        existing_files = get_existing_files_on_cdn(session, args.storage_zone, args.access_key, args.region_host, dest_prefix, args.start_number, args.end_number)
        logger.info(f"Found {len(existing_files)} existing files on CDN")

    consecutive_missing = 0
    found_count = 0
    uploaded_count = 0
    skipped_count = 0
    errors_upload = 0

    try:
        for n in range(args.start_number, args.end_number + 1):
            filename = f"{n}.json"
            local_path = tempdir_path / filename
            dest_key = f"{dest_prefix}{filename}"

            # Skip if file already exists on CDN
            if n in existing_files:
                skipped_count += 1
                if n % 100 == 0:
                    logger.info(f"[{n}] skipped (already exists on CDN)")
                continue

            ok, code = download_json(session, args.gateway, args.cid, n, local_path, args.download_timeout)
            if not ok:
                consecutive_missing += 1
                if n % 25 == 0:
                    logger.info(f"[{n}] missing (HTTP {code}); miss streak={consecutive_missing}")
                if consecutive_missing >= args.max_missing:
                    logger.warning(f"Stopping at n={n}: reached {consecutive_missing} consecutive misses.")
                    break
                continue

            # got it
            consecutive_missing = 0
            found_count += 1
            up_ok, up_code, up_text = bunny_put(session, args.storage_zone, args.access_key, args.region_host, dest_key, local_path)
            if up_ok:
                uploaded_count += 1
                logger.info(f"[{n}] uploaded -> {dest_key}")
                if args.delete_local:
                    try:
                        local_path.unlink(missing_ok=True)
                    except Exception:
                        pass
            else:
                errors_upload += 1
                logger.error(f"[{n}] upload FAILED (HTTP {up_code}): {up_text}")
                # keep local copy for inspection

        logger.info(f"Done. Found: {found_count}, Uploaded: {uploaded_count}, Skipped: {skipped_count}, Upload errors: {errors_upload}")
        if errors_upload == 0 and args.delete_local:
            shutil.rmtree(tempdir, ignore_errors=True)
            logger.info("Local temp files deleted.")
        else:
            logger.info(f"Local files kept at: {tempdir}")
    except KeyboardInterrupt:
        logger.warning("Interrupted by user.")
        logger.info(f"Local files kept at: {tempdir}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise

if __name__ == "__main__":
    main()