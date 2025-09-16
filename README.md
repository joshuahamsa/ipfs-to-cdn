# IPFS to Bunny CDN Migration Tool

A robust Python script suite for efficiently migrating NFT images from IPFS to Bunny CDN storage. This tool downloads images from IPFS gateways and uploads them to Bunny CDN with intelligent error handling, multiple gateway support, and progress tracking.

## 🚀 Features

* **Multiple Gateway Support**: Automatically tries multiple IPFS gateways for better reliability
* **Intelligent Error Handling**: Graceful handling of 504 timeouts, connection errors, and incomplete reads
* **Resume Capability**: Continue from any point after failures
* **Screen Session Support**: Survives SSH disconnections
* **Flexible Configuration**: Command-line arguments and environment variables
* **Memory Efficient**: Streams files without loading entire images into memory
* **Progress Tracking**: Real-time feedback on download and upload progress
* **CDN Skip Option**: Skip CDN existence checks for faster processing

## 📁 Project Structure

```
cdn/
├── ipfs-to-cdn.py              # Main script for ape images
├── ipfs-to-cdn-hogs.py         # Script for hog images
├── run-upload.sh               # Comprehensive upload runner
├── run-apes-detached.sh        # Apes upload with screen sessions
├── run-hogs-detached.sh        # Hogs upload with screen sessions
├── check-status.sh             # Monitor upload progress
├── setup-credentials.sh        # Credential setup helper
├── QUICK_REFERENCE.md          # Quick command reference
├── SCREEN_MANAGEMENT.md        # Screen session management guide
└── README.md                   # This file
```

## 🛠 Prerequisites

* Python 3.6+
* Bunny CDN account with storage zone access
* Network access to IPFS gateways
* `screen` or `tmux` for detached sessions (recommended)

## 📦 Installation

1. Clone this repository:
```bash
git clone https://github.com/joshuahamsa/ipfs-to-cdn.git
cd ipfs-to-cdn
```

2. Create and activate virtual environment:
```bash
python3 -m venv cdenv
source cdenv/bin/activate
```

3. Install required dependencies:
```bash
pip install requests
```

## ⚙️ Configuration

### Environment Variables (Recommended)

Set these environment variables for your Bunny CDN credentials:

```bash
export BUNNY_STORAGE_ZONE="your-storage-zone-name"
export BUNNY_ACCESS_KEY="your-access-key"
export BUNNY_REGION_HOST="la.storage.bunnycdn.com"  # Optional
```

### Quick Setup

Use the setup script to configure credentials:

```bash
./setup-credentials.sh
```

## 🎯 Usage

### Quick Start (Recommended)

```bash
# Set credentials and activate environment
export BUNNY_STORAGE_ZONE="baysedlabs"
export BUNNY_ACCESS_KEY="your-access-key"
source cdenv/bin/activate

# Start both uploads with screen sessions
./run-upload.sh apes --resume-from 2406 --skip-cdn-check
./run-upload.sh hogs --resume-from 3273 --skip-cdn-check
```

### Individual Scripts

```bash
# Apes upload
./run-apes-detached.sh --resume-from 2406 --skip-cdn-check

# Hogs upload  
./run-hogs-detached.sh --resume-from 3273 --skip-cdn-check
```

### Direct Python Execution

```bash
# For testing or debugging
python3 ipfs-to-cdn.py --resume-from 2406 --skip-cdn-check --max-retries 5
python3 ipfs-to-cdn-hogs.py --resume-from 3273 --skip-cdn-check --max-retries 5
```

## 📋 Available Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--resume-from N` | - | Resume from image number N |
| `--start-number N` | 2232 (apes), 2951 (hogs) | Starting image number |
| `--end-number N` | 10000 (apes), 8888 (hogs) | Ending image number |
| `--skip-cdn-check` | False | Skip checking CDN for existing files |
| `--max-retries N` | 3 | Max retries per file across all gateways |
| `--retry-delay N` | 5 | Base delay between retries (seconds) |
| `--download-timeout N` | 180 | Download timeout (seconds) |
| `--max-missing N` | 75 | Stop after N consecutive misses |
| `--log-file FILE` | auto-generated | Log file name |
| `--storage-zone ZONE` | From env | Bunny storage zone |
| `--access-key KEY` | From env | Bunny access key |

## 🔧 Screen Session Management

### Start Uploads
```bash
./run-upload.sh apes --resume-from 2406 --skip-cdn-check
./run-upload.sh hogs --resume-from 3273 --skip-cdn-check
```

### Monitor Progress
```bash
# Check status
./check-status.sh

# Reconnect to sessions
screen -r apes-upload
screen -r hogs-upload

# List all sessions
screen -ls
```

### Stop Sessions
```bash
# Kill specific sessions
screen -S apes-upload -X quit
screen -S hogs-upload -X quit

# Or from inside session: Ctrl+C then 'exit'
```

## 🌐 Multiple Gateway Support

The scripts automatically try multiple IPFS gateways for better reliability:

- `https://ipfs.io` (primary)
- `https://gateway.pinata.cloud`
- `https://dweb.link`

If one gateway fails, the script automatically tries the next one with exponential backoff.

## 📊 Monitoring and Logs

### Real-time Monitoring
```bash
# Check current status
./check-status.sh

# View live output
screen -r apes-upload
screen -r hogs-upload
```

### Log Files
- `ipfs-to-cdn-apes-detached.log` - Apes upload log
- `ipfs-to-cdn-hogs-detached.log` - Hogs upload log
- `ipfs-to-cdn-apes.log` - Legacy apes log
- `ipfs-to-cdn-hogs.log` - Legacy hogs log

## 🚨 Error Handling

The improved scripts handle various network issues:

- **504 Gateway Timeouts**: Automatic retry with multiple gateways
- **Connection Errors**: Graceful handling with exponential backoff
- **Incomplete Reads**: Retry logic for partial downloads
- **SSH Disconnections**: Screen sessions survive connection drops

## 💡 Common Use Cases

### Resume After Failure
```bash
./run-upload.sh apes --resume-from 2500
```

### Skip CDN Check (Faster)
```bash
./run-upload.sh apes --skip-cdn-check --resume-from 2500
```

### More Aggressive Retries
```bash
./run-upload.sh apes --max-retries 10 --retry-delay 15
```

### Custom Range
```bash
./run-upload.sh apes --start-number 3000 --end-number 4000
```

## 🔍 Troubleshooting

### Common Issues

1. **Credential Errors**: Run `./setup-credentials.sh` or set environment variables
2. **Virtual Environment**: Make sure to activate with `source cdenv/bin/activate`
3. **Screen Sessions**: Use `screen -ls` to check running sessions
4. **Network Issues**: Scripts automatically handle with multiple gateways

### Debug Mode
```bash
# Keep local files for inspection
python3 ipfs-to-cdn.py --delete-local False --resume-from 2500
```

## 📈 Performance

- **Memory Usage**: Constant regardless of file size (streaming)
- **Network Efficiency**: HTTP connection pooling and retry logic
- **Reliability**: Multiple gateway fallback and exponential backoff
- **Persistence**: Screen sessions survive SSH disconnections

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with both apes and hogs scripts
5. Submit a pull request

## 📄 License

[Add your license information here]

## 🆘 Support

For issues and questions:
- Create an issue in this repository
- Check the troubleshooting section
- Verify your Bunny CDN configuration
- Use `./check-status.sh` for diagnostics

## 📚 Additional Resources

- [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - Quick command reference
- [SCREEN_MANAGEMENT.md](SCREEN_MANAGEMENT.md) - Screen session management
- [GitHub Repository](https://github.com/joshuahamsa/ipfs-to-cdn.git)

---

**Note**: This tool is designed for NFT image migration from IPFS to Bunny CDN. It expects files to be named as `N.png` where N is a sequential number (e.g., `1.png`, `2.png`, `3.png`).
