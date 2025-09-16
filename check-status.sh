#!/bin/bash

# Check the status of your IPFS uploads

echo "=== IPFS Upload Status Check ==="
echo ""

# Check for running screen sessions
echo "📺 Active Screen Sessions:"
screen -ls | grep -E "(apes-upload|hogs-upload)" || echo "  No upload sessions running"
echo ""

# Check log files for recent activity
echo "📊 Recent Upload Activity:"
echo ""

echo "🦍 Apes Upload (last 5 lines):"
if [ -f "/home/hamsa/cdn/ipfs-to-cdn-apes-detached.log" ]; then
    tail -5 /home/hamsa/cdn/ipfs-to-cdn-apes-detached.log
elif [ -f "/home/hamsa/cdn/ipfs-to-cdn-apes.log" ]; then
    tail -5 /home/hamsa/cdn/ipfs-to-cdn-apes.log
else
    echo "  No apes log file found"
fi
echo ""

echo "🐷 Hogs Upload (last 5 lines):"
if [ -f "/home/hamsa/cdn/ipfs-to-cdn-hogs-detached.log" ]; then
    tail -5 /home/hamsa/cdn/ipfs-to-cdn-hogs-detached.log
elif [ -f "/home/hamsa/cdn/ipfs-to-cdn-hogs.log" ]; then
    tail -5 /home/hamsa/cdn/ipfs-to-cdn-hogs.log
else
    echo "  No hogs log file found"
fi
echo ""

# Check for any error patterns
echo "🚨 Recent Errors:"
echo "Apes errors:"
grep -i "error\|failed\|timeout" /home/hamsa/cdn/ipfs-to-cdn-apes*.log 2>/dev/null | tail -3 || echo "  No recent errors"
echo ""
echo "Hogs errors:"
grep -i "error\|failed\|timeout" /home/hamsa/cdn/ipfs-to-cdn-hogs*.log 2>/dev/null | tail -3 || echo "  No recent errors"
echo ""

echo "💡 Useful Commands:"
echo "  screen -r apes-upload    # Connect to apes upload session"
echo "  screen -r hogs-upload    # Connect to hogs upload session"
echo "  screen -ls               # List all sessions"
echo "  ./run-apes-detached.sh   # Start apes upload"
echo "  ./run-hogs-detached.sh   # Start hogs upload"
