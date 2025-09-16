#!/usr/bin/env python3
"""
Single-pass IPFS -> Bunny pipeline for files named N.png (no padding).
For each n in [start, end]:
  - Check if file already exists on CDN
  - If not, GET n.png from the gateway
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
DEFAULT_CID = "bafybeiac27xcgv3oer2j3p6xvuh4vr2pxlp6hdpywucqkiraw6y3h35cke"
DEFAULT_GATEWAY = "https://ipfs.io"
DEFAULT_GATEWAYS = [
    "https://ipfs.io",
    "https://gateway.pinata.cloud",
    "https://dweb.link"
]
DEFAULT_START_NUMBER = 2951
DEFAULT_END_NUMBER   = 8888
DEFAULT_MAX_MISSING  = 75
DEFAULT_DOWNLOAD_TIMEOUT = 180
DEFAULT_DEST_PATH    = "hog_images/"
DEFAULT_DELETE_LOCAL = True
DEFAULT_LOG_FILE     = "ipfs-to-cdn-hogs.log"
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 5

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
        total=3,  # Reduced total retries since we'll handle retries manually
        backoff_factor=1.0,  # Increased backoff factor
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "PUT", "HEAD"]
    )
    adapter = HTTPAdapter(max_retries=retries, pool_connections=20, pool_maxsize=20)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    return s

def check_file_exists_on_cdn(session, storage_zone, access_key, region_host, dest_key):
    """Check if a file already exists on Bunny CDN using public URL."""
    # Use the public CDN URL format instead of storage API
    # Note: The actual CDN URL uses 'baysed' not 'baysedlabs'
    public_url = f"https://baysed.b-cdn.net/{dest_key}"
    try:
        resp = session.head(public_url, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        logging.warning(f"Error checking CDN for {dest_key}: {e}")
        return False

def get_existing_files_on_cdn(session, storage_zone, access_key, region_host, dest_prefix, start_num, end_num):
    """Get list of files that already exist on CDN in the given range."""
    existing_files = set()
    base = region_host.strip() if region_host else "storage.bunnycdn.com"
    
    total_files = end_num - start_num + 1
    logging.info(f"Checking {total_files} files for existence on CDN...")
    
    # Check files in batches to avoid overwhelming the CDN
    batch_size = 100
    checked_count = 0
    
    for batch_start in range(start_num, end_num + 1, batch_size):
        batch_end = min(batch_start + batch_size - 1, end_num)
        batch_size_actual = batch_end - batch_start + 1
        
        logging.info(f"Checking batch {batch_start}-{batch_end} ({batch_size_actual} files)...")
        
        # Check each file in the batch
        for n in range(batch_start, batch_end + 1):
            filename = f"{n}.png"
            dest_key = f"{dest_prefix}{filename}"
            
            if check_file_exists_on_cdn(session, storage_zone, access_key, region_host, dest_key):
                existing_files.add(n)
                logging.info(f"✓ File {n}.png already exists on CDN")
            
            checked_count += 1
            
            # Progress update every 50 files
            if checked_count % 50 == 0:
                progress_pct = (checked_count / total_files) * 100
                logging.info(f"Progress: {checked_count}/{total_files} files checked ({progress_pct:.1f}%) - Found {len(existing_files)} existing files")
        
        # Small delay between batches to be nice to the CDN
        time.sleep(0.1)
    
    logging.info(f"CDN check complete: {len(existing_files)} files already exist out of {total_files} checked")
    return existing_files

def download_png(session: requests.Session, gateways: list, cid: str, n: int, out_file: Path, timeout: int, max_retries: int = 3, retry_delay: int = 5):
    """Download PNG from IPFS using multiple gateways with retry logic."""
    filename = f"{n}.png"
    
    for attempt in range(max_retries):
        for gateway_idx, gateway in enumerate(gateways):
            try:
                url = f"{gateway.rstrip('/')}/ipfs/{cid}/{filename}"
                logging.debug(f"Attempt {attempt + 1}/{max_retries}: Trying {gateway} for {filename}")
                
                with session.get(url, stream=True, timeout=timeout) as r:
                    if r.status_code == 200:
                        out_file.parent.mkdir(parents=True, exist_ok=True)
                        with open(out_file, "wb") as f:
                            for chunk in r.iter_content(chunk_size=1024*256):
                                if chunk:
                                    f.write(chunk)
                        logging.debug(f"Successfully downloaded {filename} from {gateway}")
                        return True, 200
                    elif r.status_code == 404:
                        logging.debug(f"File {filename} not found on {gateway} (404)")
                        return False, 404
                    else:
                        logging.warning(f"Gateway {gateway} returned {r.status_code} for {filename}")
                        
            except requests.exceptions.Timeout:
                logging.warning(f"Timeout downloading {filename} from {gateway}")
            except requests.exceptions.ConnectionError as e:
                logging.warning(f"Connection error downloading {filename} from {gateway}: {e}")
            except requests.exceptions.RequestException as e:
                logging.warning(f"Request error downloading {filename} from {gateway}: {e}")
            except Exception as e:
                logging.error(f"Unexpected error downloading {filename} from {gateway}: {e}")
        
        # If we've tried all gateways and this isn't the last attempt, wait before retrying
        if attempt < max_retries - 1:
            wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
            logging.info(f"All gateways failed for {filename}, waiting {wait_time}s before retry {attempt + 2}/{max_retries}")
            time.sleep(wait_time)
    
    logging.error(f"Failed to download {filename} after {max_retries} attempts across all gateways")
    return False, 504  # Return 504 to indicate gateway timeout

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
    ap = argparse.ArgumentParser(description="Single-pass IPFS (N.png) -> Bunny uploader with CDN checking.")
    ap.add_argument("--cid", default=DEFAULT_CID)
    ap.add_argument("--gateway", default=DEFAULT_GATEWAY, help="Primary IPFS gateway (will use multiple gateways automatically)")
    ap.add_argument("--gateways", nargs="+", default=DEFAULT_GATEWAYS, help="List of IPFS gateways to try")
    ap.add_argument("--start-number", type=int, default=DEFAULT_START_NUMBER)
    ap.add_argument("--end-number", type=int, default=DEFAULT_END_NUMBER)
    ap.add_argument("--max-missing", type=int, default=DEFAULT_MAX_MISSING)
    ap.add_argument("--download-timeout", type=int, default=DEFAULT_DOWNLOAD_TIMEOUT)
    ap.add_argument("--max-retries", type=int, default=DEFAULT_MAX_RETRIES, help="Max retries per file across all gateways")
    ap.add_argument("--retry-delay", type=int, default=DEFAULT_RETRY_DELAY, help="Base delay between retries (seconds)")
    ap.add_argument("--dest-path", default=DEFAULT_DEST_PATH)
    ap.add_argument("--delete-local", action="store_true", default=DEFAULT_DELETE_LOCAL)
    ap.add_argument("--log-file", default=DEFAULT_LOG_FILE)
    ap.add_argument("--skip-cdn-check", action="store_true", help="Skip checking CDN for existing files")
    ap.add_argument("--resume-from", type=int, help="Resume from this number (useful after failures)")
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
    
    # Handle resume functionality
    start_number = args.resume_from if args.resume_from else args.start_number
    if args.resume_from:
        logger.info(f"Resuming from number {start_number} (original range was {args.start_number} to {args.end_number})")
    
    logger.info(f"Range: {start_number} to {args.end_number}")
    logger.info(f"Gateways: {', '.join(args.gateways)}")
    logger.info(f"CID: {args.cid}")
    logger.info(f"Max retries per file: {args.max_retries}")
    logger.info(f"Retry delay: {args.retry_delay}s")

    dest_prefix = args.dest_path.strip()
    if dest_prefix and not dest_prefix.endswith("/"):
        dest_prefix += "/"

    session = make_session()
    tempdir = tempfile.mkdtemp(prefix="ipfs_dl_")
    tempdir_path = Path(tempdir)

    total = args.end_number - start_number + 1
    logger.info(f"Single-pass: scanning & uploading {total} candidates: {args.gateways[0]}/ipfs/{args.cid}/N.png")
    logger.info(f"Stopping after {args.max_missing} consecutive misses.")

    # Check for existing files on CDN
    existing_files = set()
    if not args.skip_cdn_check:
        logger.info("Checking CDN for existing files...")
        existing_files = get_existing_files_on_cdn(session, args.storage_zone, args.access_key, args.region_host, dest_prefix, start_number, args.end_number)
        logger.info(f"Found {len(existing_files)} existing files on CDN")

    consecutive_missing = 0
    found_count = 0
    uploaded_count = 0
    skipped_count = 0
    errors_upload = 0

    try:
        for n in range(start_number, args.end_number + 1):
            filename = f"{n}.png"
            local_path = tempdir_path / filename
            dest_key = f"{dest_prefix}{filename}"

            # Skip if file already exists on CDN
            if n in existing_files:
                skipped_count += 1
                if n % 100 == 0:
                    logger.info(f"[{n}] skipped (already exists on CDN)")
                continue

            ok, code = download_png(session, args.gateways, args.cid, n, local_path, args.download_timeout, args.max_retries, args.retry_delay)
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