#!/bin/bash

# Resume script for IPFS to CDN upload
# This script will resume from image 2406 (where the error occurred)

echo "Resuming IPFS to CDN upload from image 2406..."
echo "Using improved script with multiple gateways and better error handling"

# Activate your virtual environment if needed
source /home/hamsa/cdenv/bin/activate

# Run the script with resume functionality
python3 /home/hamsa/cdn/ipfs-to-cdn.py \
    --resume-from 2406 \
    --max-retries 5 \
    --retry-delay 10 \
    --download-timeout 300 \
    --log-file ipfs-to-cdn-resume.log

echo "Script completed. Check the log file for details."
