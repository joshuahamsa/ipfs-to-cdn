#!/bin/bash

# Comprehensive IPFS upload script with full argument support
# Usage: ./run-upload.sh [script] [arguments]
# Examples:
#   ./run-upload.sh apes --resume-from 2500 --skip-cdn-check
#   ./run-upload.sh hogs --max-retries 10 --retry-delay 15
#   ./run-upload.sh apes --start-number 3000 --end-number 4000

SCRIPT_TYPE="${1:-help}"

if [ "$SCRIPT_TYPE" = "help" ] || [ "$SCRIPT_TYPE" = "-h" ] || [ "$SCRIPT_TYPE" = "--help" ]; then
    echo "=== IPFS Upload Script Runner ==="
    echo ""
    echo "Usage: ./run-upload.sh [script] [arguments]"
    echo ""
    echo "Scripts:"
    echo "  apes  - Upload ape images (CID: QmdYwvVtjNFKRqHEWPChdkfM24Z1i34FmmC4uAjDdnJ7NF)"
    echo "  hogs  - Upload hog images (CID: bafybeiac27xcgv3oer2j3p6xvuh4vr2pxlp6hdpywucqkiraw6y3h35cke)"
    echo ""
    echo "Common Arguments:"
    echo "  --resume-from N        Resume from image number N"
    echo "  --start-number N       Start from image number N"
    echo "  --end-number N         End at image number N"
    echo "  --skip-cdn-check       Skip checking CDN for existing files"
    echo "  --max-retries N        Max retries per file (default: 3)"
    echo "  --retry-delay N        Base delay between retries in seconds (default: 5)"
    echo "  --download-timeout N   Download timeout in seconds (default: 180)"
    echo "  --max-missing N        Stop after N consecutive misses (default: 75)"
    echo "  --log-file FILE        Log file name"
    echo ""
    echo "Examples:"
    echo "  ./run-upload.sh apes --resume-from 2500 --skip-cdn-check"
    echo "  ./run-upload.sh hogs --max-retries 10 --retry-delay 15"
    echo "  ./run-upload.sh apes --start-number 3000 --end-number 4000"
    echo "  ./run-upload.sh hogs --resume-from 3500 --max-missing 100"
    echo ""
    echo "Screen Commands:"
    echo "  screen -r apes-upload  # Reconnect to apes session"
    echo "  screen -r hogs-upload  # Reconnect to hogs session"
    echo "  screen -ls            # List all sessions"
    echo "  ./check-status.sh     # Check upload status"
    exit 0
fi

# Shift to remove the script type from arguments
shift
ARGS="$@"

# Activate virtual environment
source /home/hamsa/cdenv/bin/activate

# Check for Bunny credentials
if [ -z "$BUNNY_STORAGE_ZONE" ] || [ -z "$BUNNY_ACCESS_KEY" ]; then
    echo "⚠️  Warning: Bunny credentials not found in environment variables"
    echo "   Make sure to set BUNNY_STORAGE_ZONE and BUNNY_ACCESS_KEY"
    echo "   Or pass them as arguments: --storage-zone ZONE --access-key KEY"
    echo ""
fi

case "$SCRIPT_TYPE" in
    "apes")
        echo "Starting apes upload in detached screen session..."
        echo "Arguments: $ARGS"
        echo "To reconnect: screen -r apes-upload"
        
        screen -dmS apes-upload bash -c "
            cd /home/hamsa/cdn && \
            source /home/hamsa/cdenv/bin/activate && \
            export BUNNY_STORAGE_ZONE='$BUNNY_STORAGE_ZONE' && \
            export BUNNY_ACCESS_KEY='$BUNNY_ACCESS_KEY' && \
            export BUNNY_REGION_HOST='$BUNNY_REGION_HOST' && \
            python3 ipfs-to-cdn.py $ARGS; \
            echo 'Apes upload completed. Press any key to close.'; \
            read -n 1
        "
        echo "Apes upload started in screen session 'apes-upload'"
        ;;
        
    "hogs")
        echo "Starting hogs upload in detached screen session..."
        echo "Arguments: $ARGS"
        echo "To reconnect: screen -r hogs-upload"
        
        screen -dmS hogs-upload bash -c "
            cd /home/hamsa/cdn && \
            source /home/hamsa/cdenv/bin/activate && \
            export BUNNY_STORAGE_ZONE='$BUNNY_STORAGE_ZONE' && \
            export BUNNY_ACCESS_KEY='$BUNNY_ACCESS_KEY' && \
            export BUNNY_REGION_HOST='$BUNNY_REGION_HOST' && \
            python3 ipfs-to-cdn-hogs.py $ARGS; \
            echo 'Hogs upload completed. Press any key to close.'; \
            read -n 1
        "
        echo "Hogs upload started in screen session 'hogs-upload'"
        ;;
        
    *)
        echo "Error: Unknown script type '$SCRIPT_TYPE'"
        echo "Use 'apes' or 'hogs', or run without arguments for help"
        exit 1
        ;;
esac

echo ""
echo "Useful commands:"
echo "  screen -r ${SCRIPT_TYPE}-upload  # Reconnect to session"
echo "  screen -ls                       # List all sessions"
echo "  ./check-status.sh                # Check status"
