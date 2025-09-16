#!/bin/bash

# Run the hogs upload script in a detached screen session
# Usage: ./run-hogs-detached.sh [additional arguments]
# Example: ./run-hogs-detached.sh --resume-from 3500 --max-retries 10 --skip-cdn-check

echo "Starting hogs upload in detached screen session..."
echo "To reconnect to the session later, run: screen -r hogs-upload"

# Activate virtual environment
source /home/hamsa/cdenv/bin/activate

# Check for Bunny credentials
if [ -z "$BUNNY_STORAGE_ZONE" ] || [ -z "$BUNNY_ACCESS_KEY" ]; then
    echo "⚠️  Warning: Bunny credentials not found in environment variables"
    echo "   Make sure to set BUNNY_STORAGE_ZONE and BUNNY_ACCESS_KEY"
    echo "   Or pass them as arguments: --storage-zone ZONE --access-key KEY"
    echo ""
fi

# Default arguments (can be overridden by command line)
DEFAULT_ARGS="--resume-from 3273 --max-retries 5 --retry-delay 10 --download-timeout 300 --log-file ipfs-to-cdn-hogs-detached.log"

# Use provided arguments or defaults
ARGS="${@:-$DEFAULT_ARGS}"

echo "Using arguments: $ARGS"
echo ""

# Start the script in a named screen session
screen -dmS hogs-upload bash -c "
    cd /home/hamsa/cdn && \
    source /home/hamsa/cdenv/bin/activate && \
    export BUNNY_STORAGE_ZONE='$BUNNY_STORAGE_ZONE' && \
    export BUNNY_ACCESS_KEY='$BUNNY_ACCESS_KEY' && \
    export BUNNY_REGION_HOST='$BUNNY_REGION_HOST' && \
    python3 ipfs-to-cdn-hogs.py $ARGS; \
    echo 'Script completed. Press any key to close this window.'; \
    read -n 1
"

echo "Hogs upload started in screen session 'hogs-upload'"
echo ""
echo "Useful commands:"
echo "  screen -r hogs-upload    # Reconnect to the session"
echo "  screen -ls               # List all screen sessions"
echo "  screen -S hogs-upload -X quit  # Kill the session"
echo ""
echo "Example usage:"
echo "  ./run-hogs-detached.sh                                    # Use defaults"
echo "  ./run-hogs-detached.sh --resume-from 3500                 # Resume from 3500"
echo "  ./run-hogs-detached.sh --skip-cdn-check --max-retries 10  # Skip CDN check, more retries"