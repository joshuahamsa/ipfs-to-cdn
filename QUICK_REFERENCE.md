# IPFS Upload Scripts - Quick Reference

## 🚀 **Yes, all scripts support full argument customization!**

### **Available Arguments:**
- `--resume-from N` - Resume from image number N
- `--start-number N` - Start from image number N  
- `--end-number N` - End at image number N
- `--skip-cdn-check` - Skip checking CDN for existing files
- `--max-retries N` - Max retries per file (default: 3)
- `--retry-delay N` - Base delay between retries in seconds (default: 5)
- `--download-timeout N` - Download timeout in seconds (default: 180)
- `--max-missing N` - Stop after N consecutive misses (default: 75)
- `--log-file FILE` - Custom log file name

## 📋 **Script Options:**

### **1. Comprehensive Script (Recommended)**
```bash
# Show help
./run-upload.sh help

# Run with custom arguments
./run-upload.sh apes --resume-from 2500 --skip-cdn-check --max-retries 10
./run-upload.sh hogs --resume-from 3500 --retry-delay 15
```

### **2. Individual Scripts**
```bash
# Apes with custom args
./run-apes-detached.sh --resume-from 2500 --skip-cdn-check

# Hogs with custom args  
./run-hogs-detached.sh --max-retries 10 --retry-delay 15
```

### **3. Direct Python (for testing)**
```bash
python3 ipfs-to-cdn.py --resume-from 2500 --skip-cdn-check --max-retries 10
python3 ipfs-to-cdn-hogs.py --resume-from 3500 --retry-delay 15
```

## 🔧 **Screen Session Management:**
```bash
# Reconnect to sessions
screen -r apes-upload
screen -r hogs-upload

# List all sessions
screen -ls

# Kill a session
screen -S apes-upload -X quit
screen -S hogs-upload -X quit

# Check status
./check-status.sh
```

## 💡 **Common Use Cases:**

### **Resume after failure:**
```bash
./run-upload.sh apes --resume-from 2500
```

### **Skip CDN check (faster):**
```bash
./run-upload.sh apes --skip-cdn-check --resume-from 2500
```

### **More aggressive retries:**
```bash
./run-upload.sh apes --max-retries 10 --retry-delay 15
```

### **Custom range:**
```bash
./run-upload.sh apes --start-number 3000 --end-number 4000
```

### **Both uploads simultaneously:**
```bash
./run-upload.sh apes --resume-from 2500 --skip-cdn-check
./run-upload.sh hogs --resume-from 3500 --skip-cdn-check
```

## 🎯 **Key Benefits:**
- ✅ **Survives SSH disconnections** (uses screen sessions)
- ✅ **Full argument support** (all Python script arguments work)
- ✅ **Easy monitoring** (check-status.sh script)
- ✅ **Flexible configuration** (custom retries, timeouts, etc.)
- ✅ **Multiple gateway support** (automatic fallback)
- ✅ **Resume capability** (continue from any point)

