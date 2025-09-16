#!/usr/bin/env python3
"""
Convert CSV HOG NFT data to JSON metadata files and upload to Bunny CDN.
Recreates metadata JSON files from cached CSV data and streams them to CDN.

Based on ipfs-to-cdn.py for CDN upload functionality.
"""

import argparse
import csv
import json
import os
import sys
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests  # type: ignore
from requests.adapters import HTTPAdapter, Retry  # type: ignore
from tqdm import tqdm  # type: ignore

# -------------------- Defaults (override via CLI) --------------------
DEFAULT_CSV_FILE = "Hogs.csv"
DEFAULT_DEST_PATH = "hog_jsons/"
DEFAULT_CONCURRENCY = 8
DEFAULT_TIMEOUT = 180

# Bunny CDN settings
DEFAULT_STORAGE_ZONE = os.getenv("BUNNY_STORAGE_ZONE", "")
DEFAULT_ACCESS_KEY = os.getenv("BUNNY_ACCESS_KEY", "")
DEFAULT_REGION_HOST = os.getenv("BUNNY_REGION_HOST", None)


def make_session():
    """Create a requests session with retry logic."""
    s = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=0.6,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "PUT"]
    )
    adapter = HTTPAdapter(
        max_retries=retries, pool_connections=50, pool_maxsize=50
    )
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    return s


def extract_attributes_from_row(row):
    """Extract attributes from CSV row data for HOGs."""
    attributes = []

    # Map CSV columns to trait types for HOGs
    attribute_mapping = {
        "Attribute Background": "Background",
        "Attribute Body": "Body",
        "Attribute Headwear": "Headwear",
        "Attribute Eyes": "Eyes",
        "Attribute Clothing": "Clothing",
        "Attribute Mouth": "Mouth",
        "Attribute Tusks": "Tusks"
    }

    for csv_col, trait_type in attribute_mapping.items():
        if csv_col in row and row[csv_col] and row[csv_col].strip():
            attributes.append({
                "trait_type": trait_type,
                "value": row[csv_col].strip()
            })

    return attributes


def create_metadata_json(row):
    """Create JSON metadata from CSV row data for HOGs."""
    # Extract edition number from Name field
    # (e.g., "HOG #3642" -> 3642)
    name = row.get("Name", "")
    edition = ""
    if "#" in name:
        edition_str = name.split("#")[-1].strip()
        try:
            edition = int(edition_str)
        except ValueError:
            edition = edition_str
    else:
        edition = "unknown"

    # Create the metadata JSON structure for HOGs
    metadata = {
        "name": name,
        "description": row.get(
            "Description",
            "The HOGs are a collection of 8888 unique HOG NFTs living on "
            "the XRP ledger."
        ),
        "image": row.get("Image", ""),
        "dna": row.get("Dna", ""),
        "edition": edition,
        "date": 1674756786096,  # Default date for HOGs
        "creator": row.get("Creator", "Bored Apes XRP Club"),
        "artist": row.get("Artist", "Bored Apes XRP Club"),
        "attributes": extract_attributes_from_row(row)
    }

    return metadata


def bunny_put_json(session, storage_zone, access_key, region_host,
                   dest_key, json_data):
    """Upload JSON data directly to Bunny CDN without local file storage."""
    base = region_host.strip() if region_host else "storage.bunnycdn.com"
    url = f"https://{base}/{quote(storage_zone.strip())}/{dest_key}"

    headers = {
        "AccessKey": access_key.strip(),
        "Content-Type": "application/json"
    }

    # Convert JSON to bytes
    json_bytes = json.dumps(json_data, indent=2).encode('utf-8')

    # Upload directly from memory
    resp = session.put(url, headers=headers, data=json_bytes, timeout=180)

    if resp.status_code not in (200, 201):
        raise RuntimeError(
            f"Bunny upload failed ({resp.status_code}): {resp.text[:200]}"
        )

    return True


def process_nft_row(session, row, storage_zone, access_key, region_host,
                    dest_prefix):
    """Process a single NFT row: create JSON and upload to CDN."""
    try:
        # Create metadata JSON
        metadata = create_metadata_json(row)

        # Extract edition number for filename
        edition = metadata.get("edition", "unknown")
        if isinstance(edition, int):
            edition_str = str(edition)
        else:
            edition_str = str(edition)
            if not edition_str or edition_str == "unknown":
                # Fallback: try to extract from Name field
                name = row.get("Name", "")
                if "#" in name:
                    edition_str = name.split("#")[-1].strip()
                else:
                    edition_str = "unknown"

        # Create destination path
        dest_key = f"{dest_prefix}{edition_str}.json"

        # Upload to CDN
        bunny_put_json(session, storage_zone, access_key, region_host,
                       dest_key, metadata)

        return True, edition_str, None

    except Exception as e:
        return False, row.get("Name", "unknown"), str(e)


def main():
    ap = argparse.ArgumentParser(
        description="Convert CSV HOG NFT data to JSON metadata and upload to "
                    "Bunny CDN."
    )
    ap.add_argument("--csv-file", default=DEFAULT_CSV_FILE,
                    help="Path to CSV file containing HOG NFT data")
    ap.add_argument("--dest-path", default=DEFAULT_DEST_PATH,
                    help="Destination path prefix in CDN")
    ap.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY,
                    help="Number of concurrent uploads")
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                    help="Upload timeout in seconds")

    # Bunny CDN settings
    ap.add_argument("--storage-zone", default=DEFAULT_STORAGE_ZONE,
                    help="Bunny storage zone name")
    ap.add_argument("--access-key", default=DEFAULT_ACCESS_KEY,
                    help="Bunny access key")
    ap.add_argument("--region-host", default=DEFAULT_REGION_HOST,
                    help="Bunny region host (optional)")

    # Processing options
    ap.add_argument("--start-row", type=int, default=0,
                    help="Start processing from this row (0-based)")
    ap.add_argument("--max-rows", type=int,
                    help="Maximum number of rows to process")
    ap.add_argument("--dry-run", action="store_true",
                    help="Show what would be processed without uploading")

    args = ap.parse_args()

    # Validate required arguments
    if not args.storage_zone or not args.access_key:
        print("ERROR: Bunny credentials missing. Set --storage-zone/"
              "--access-key or env vars BUNNY_STORAGE_ZONE/"
              "BUNNY_ACCESS_KEY.", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(args.csv_file):
        print(f"ERROR: CSV file not found: {args.csv_file}", file=sys.stderr)
        sys.exit(1)

    # Normalize destination path
    dest_prefix = args.dest_path.strip()
    if dest_prefix and not dest_prefix.endswith("/"):
        dest_prefix += "/"

    print(f"Processing CSV file: {args.csv_file}")
    print(f"Destination CDN path: {dest_prefix}")
    print(f"Concurrency: {args.concurrency}")

    if args.dry_run:
        print("DRY RUN MODE - No files will be uploaded")

    # Read CSV file
    try:
        with open(args.csv_file, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)
    except Exception as e:
        print(f"ERROR: Failed to read CSV file: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(rows)} rows in CSV file")

    # Apply row filtering
    start_idx = args.start_row
    end_idx = len(rows)
    if args.max_rows:
        end_idx = min(start_idx + args.max_rows, len(rows))

    rows_to_process = rows[start_idx:end_idx]
    print(f"Processing rows {start_idx} to {end_idx-1} "
          f"({len(rows_to_process)} rows)")

    if not rows_to_process:
        print("No rows to process.")
        return

    if args.dry_run:
        # Show sample of what would be processed
        print("\nSample of first 3 rows that would be processed:")
        for i, row in enumerate(rows_to_process[:3]):
            metadata = create_metadata_json(row)
            edition = metadata.get("edition", "unknown")
            print(f"Row {start_idx + i}: {row.get('Name', 'Unknown')} "
                  f"-> {edition}.json")
        return

    # Create session and process rows
    session = make_session()

    success_count = 0
    error_count = 0
    errors = []

    print(f"\nStarting upload of {len(rows_to_process)} JSON files...")

    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        pbar = tqdm(total=len(rows_to_process), desc="Uploading", unit="file")
        futures = []

        for row in rows_to_process:
            future = pool.submit(
                process_nft_row,
                session,
                row,
                args.storage_zone,
                args.access_key,
                args.region_host,
                dest_prefix
            )
            futures.append(future)

        for future in as_completed(futures):
            try:
                success, identifier, error = future.result()
                if success:
                    success_count += 1
                else:
                    error_count += 1
                    errors.append(f"{identifier}: {error}")
            except Exception as e:
                error_count += 1
                errors.append(f"Unknown: {str(e)}")

            pbar.update(1)

        pbar.close()

    # Print results
    print("\nProcessing complete!")
    print(f"Successfully uploaded: {success_count}")
    print(f"Errors: {error_count}")

    if errors:
        print("\nFirst 10 errors:")
        for error in errors[:10]:
            print(f"  - {error}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more errors")


if __name__ == "__main__":
    main()
