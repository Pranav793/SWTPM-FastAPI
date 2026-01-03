#!/bin/bash
# Script to stop TPM2 REST API

# Get port from command line argument or environment variable, default to 8000
PORT=${1:-${TPM2_API_PORT:-8000}}

echo "Stopping TPM2 REST API on port $PORT..."

# Find and kill the process
PID=$(lsof -t -i:$PORT 2>/dev/null)

if [ -z "$PID" ]; then
    echo "No process found running on port $PORT"
    exit 0
fi

# Kill the process
kill $PID 2>/dev/null

# Wait a moment
sleep 1

# Force kill if still running
if ps -p $PID > /dev/null 2>&1; then
    echo "Force killing process $PID..."
    kill -9 $PID 2>/dev/null
fi

# Verify it's stopped
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "✗ Failed to stop process on port $PORT"
    exit 1
else
    echo "✓ TPM2 REST API stopped successfully"
    exit 0
fi

