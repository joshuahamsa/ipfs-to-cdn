# Screen Session Management

## 🛑 **How to Stop Screen Sessions:**

### **Method 1: Kill from outside (Recommended)**
```bash
# List all sessions
screen -ls

# Kill specific sessions
screen -S apes-upload -X quit
screen -S hogs-upload -X quit
```

### **Method 2: From inside the session**
```bash
# Reconnect to session
screen -r apes-upload

# Press Ctrl+C to stop the script
# Type 'exit' to close the screen session
```

### **Method 3: Force kill if needed**
```bash
# Find the process
ps aux | grep python3 | grep ipfs

# Kill the process
kill -9 [PID]
```

## 🔄 **How to Restart with Different Arguments:**

1. **Stop the current session:**
   ```bash
   screen -S apes-upload -X quit
   ```

2. **Restart with new arguments:**
   ```bash
   ./run-upload.sh apes --resume-from 2500 --skip-cdn-check --max-retries 10
   ```

## 📊 **Monitor Progress:**
```bash
# Check status
./check-status.sh

# Reconnect to see live output
screen -r apes-upload
screen -r hogs-upload

# List all sessions
screen -ls
```

## 💡 **Pro Tips:**
- Use `--skip-cdn-check` for much faster uploads
- Sessions survive SSH disconnections
- You can close VS Code and the uploads keep running
- Use `screen -r` to reconnect and see progress anytime

