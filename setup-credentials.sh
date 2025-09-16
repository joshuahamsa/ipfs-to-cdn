#!/bin/bash

# Setup script for Bunny CDN credentials
# This script helps you set up the credentials for the IPFS upload scripts

echo "=== Bunny CDN Credentials Setup ==="
echo ""

# Check if credentials are already set
if [ -n "$BUNNY_STORAGE_ZONE" ] && [ -n "$BUNNY_ACCESS_KEY" ]; then
    echo "✅ Bunny credentials are already set:"
    echo "   Storage Zone: $BUNNY_STORAGE_ZONE"
    echo "   Access Key: ${BUNNY_ACCESS_KEY:0:8}..."
    echo "   Region Host: ${BUNNY_REGION_HOST:-'default'}"
    echo ""
    echo "You can now run the upload scripts!"
    exit 0
fi

echo "⚠️  Bunny credentials not found in environment variables"
echo ""
echo "You have several options to provide credentials:"
echo ""
echo "1. Set environment variables (recommended):"
echo "   export BUNNY_STORAGE_ZONE='your-storage-zone'"
echo "   export BUNNY_ACCESS_KEY='your-access-key'"
echo "   export BUNNY_REGION_HOST='your-region-host'  # optional"
echo ""
echo "2. Pass as arguments to the scripts:"
echo "   ./run-upload.sh apes --storage-zone ZONE --access-key KEY"
echo ""
echo "3. Create a .env file (we can set this up)"
echo ""

read -p "Would you like to set up environment variables now? (y/n): " setup_env

if [ "$setup_env" = "y" ] || [ "$setup_env" = "Y" ]; then
    echo ""
    read -p "Enter your Bunny Storage Zone: " storage_zone
    read -p "Enter your Bunny Access Key: " access_key
    read -p "Enter your Bunny Region Host (optional, press Enter to skip): " region_host
    
    echo ""
    echo "Setting environment variables..."
    export BUNNY_STORAGE_ZONE="$storage_zone"
    export BUNNY_ACCESS_KEY="$access_key"
    if [ -n "$region_host" ]; then
        export BUNNY_REGION_HOST="$region_host"
    fi
    
    echo "✅ Credentials set for this session!"
    echo ""
    echo "To make them permanent, add these lines to your ~/.bashrc:"
    echo "export BUNNY_STORAGE_ZONE='$storage_zone'"
    echo "export BUNNY_ACCESS_KEY='$access_key'"
    if [ -n "$region_host" ]; then
        echo "export BUNNY_REGION_HOST='$region_host'"
    fi
    echo ""
    echo "You can now run the upload scripts!"
else
    echo ""
    echo "You can run the scripts with credentials as arguments:"
    echo "./run-upload.sh apes --storage-zone YOUR_ZONE --access-key YOUR_KEY"
fi

