#!/usr/bin/env bash
# ShareBox 1-Click Startup Script for Linux / macOS

set -e

echo "========================================================"
echo "  ⚡ Starting ShareBox Local Wi-Fi File Sharing Hub..."
echo "========================================================"
echo ""

# Check for python3
if command -v python3 &>/dev/null; then
    PYTHON_CMD=python3
elif command -v python &>/dev/null; then
    PYTHON_CMD=python
else
    echo "[ERROR] Python 3 is not installed!"
    exit 1
fi

exec $PYTHON_CMD sharebox.py "$@"
