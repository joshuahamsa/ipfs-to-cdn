# IPFS to Bunny CDN Migration Tool

A Python script for efficiently migrating NFT images from IPFS to Bunny CDN storage. This tool downloads images from IPFS gateways and uploads them to Bunny CDN in a single pass, with intelligent error handling and progress tracking.

## Features

- **Single-pass processing**: Downloads and uploads images in one operation
- **Intelligent stopping**: Automatically stops after consecutive missing files
- **Retry logic**: Built-in HTTP retry mechanism for network resilience
- **Progress tracking**: Real-time feedback on download and upload progress
- **Flexible configuration**: Command-line arguments and environment variables
- **Memory efficient**: Streams files without loading entire images into memory
- **Error handling**: Graceful handling of network timeouts and missing files

## Prerequisites

- Python 3.6+
- Bunny CDN account with storage zone access
- Network access to IPFS gateways

## Installation

1. Clone this repository:
```bash
git clone https://github.com/joshuahamsa/ipfs-to-cdn.git
cd ipfs-to-cdn
```

2. Install required dependencies:
```bash
pip install requests
```

## Configuration

### Environment Variables (Recommended)

Set these environment variables for your Bunny CDN credentials:

```bash
export BUNNY_STORAGE_ZONE="your-storage-zone-name"
export BUNNY_ACCESS_KEY="your-access-key"
export BUNNY_REGION_HOST="la.storage.bunnycdn.com"  # Optional, defaults to storage.bunnycdn.com
```

### Command Line Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--cid` | `QmdYwvVtjNFKRqHEWPChdkfM24Z1i34FmmC4uAjDdnJ7NF` | IPFS Content Identifier |
| `--gateway` | `https://ipfs.io` | IPFS gateway URL |
| `--start-number` | `1` | Starting image number |
| `--end-number` | `10000` | Ending image number |
| `--max-missing` | `75` | Stop after this many consecutive missing files |
| `--download-timeout` | `180` | Download timeout in seconds |
| `--dest-path` | `ape_images/` | Destination path in Bunny CDN |
| `--delete-local` | `True` | Delete local temp files after upload |
| `--storage-zone` | From env | Bunny storage zone name |
| `--access-key` | From env | Bunny access key |
| `--region-host` | From env | Bunny region host |

## Usage

### Basic Usage

```bash
python3 ipfs-to-bunny.py
```

This will use default settings and environment variables for Bunny credentials.

### Advanced Usage

```bash
python3 ipfs-to-bunny.py \
  --cid "QmYourCustomCID" \
  --start-number 1 \
  --end-number 5000 \
  --max-missing 100 \
  --dest-path "my_nft_collection/" \
  --gateway "https://gateway.pinata.cloud"
```

### With Custom Bunny Settings

```bash
python3 ipfs-to-bunny.py \
  --storage-zone "my-storage-zone" \
  --access-key "my-access-key" \
  --region-host "ny.storage.bunnycdn.com" \
  --dest-path "nft_images/"
```

## How It Works

1. **Sequential Processing**: The script processes images sequentially from `start-number` to `end-number`
2. **Download**: Attempts to download each image from the IPFS gateway
3. **Upload**: If download succeeds, immediately uploads to Bunny CDN
4. **Cleanup**: Optionally deletes local temporary files after successful upload
5. **Smart Stopping**: Stops processing after encountering `max-missing` consecutive missing files

## File Naming Convention

The script expects files to be named as `N.png` where N is the sequential number (e.g., `1.png`, `2.png`, `3.png`). This is common for NFT collections.

## Error Handling

- **Network Timeouts**: Configurable timeout with retry logic
- **Missing Files**: Tracks consecutive missing files and stops gracefully
- **Upload Failures**: Reports upload errors while continuing processing
- **Interruption**: Handles Ctrl+C gracefully, preserving local files for inspection

## Output

The script provides real-time feedback:

```
Single-pass: scanning & uploading 10000 candidates: https://ipfs.io/ipfs/QmdYwvVtjNFKRqHEWPChdkfM24Z1i34FmmC4uAjDdnJ7NF/N.png
Stopping after 75 consecutive misses.
[1] uploaded -> ape_images/1.png
[2] uploaded -> ape_images/2.png
[25] missing (HTTP 404); miss streak=1
[50] missing (HTTP 404); miss streak=2
...
Stopping at n=100: reached 75 consecutive misses.
Done. Found: 25, Uploaded: 25, Upload errors: 0
Local temp files deleted.
```

## Performance Considerations

- **Memory Usage**: Files are streamed, so memory usage remains constant regardless of file size
- **Network Efficiency**: Uses HTTP connection pooling and retry logic
- **Concurrent Processing**: Currently single-threaded for simplicity and reliability
- **Storage**: Temporary files are created in system temp directory

## Troubleshooting

### Common Issues

1. **Authentication Errors**: Verify your Bunny CDN credentials
2. **Network Timeouts**: Increase `--download-timeout` for slow connections
3. **Missing Files**: Adjust `--max-missing` based on your collection's completeness
4. **Permission Errors**: Ensure write access to temp directory

### Debug Mode

For debugging, you can keep local files by setting `--delete-local` to `False`:

```bash
python3 ipfs-to-bunny.py --delete-local False
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run linting: `python3 -m flake8 cdn/ipfs-to-bunny.py`
5. Submit a pull request

## License

[Add your license information here]

## Support

For issues and questions:
- Create an issue in this repository
- Check the troubleshooting section above
- Verify your Bunny CDN configuration
