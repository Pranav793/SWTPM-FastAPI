#!/bin/bash
# Script to start TPM2 REST API in the background

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if virtual environment exists and activate it
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Get port from command line argument or environment variable, default to 8000
PORT=${1:-${TPM2_API_PORT:-8000}}

# Check if port is already in use
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "Port $PORT is already in use. Kill the process or use a different port."
    echo "To kill: kill -9 \$(lsof -t -i:$PORT)"
    exit 1
fi

# Start the API in background
echo "Starting TPM2 REST API on port $PORT in the background..."
nohup python3 tpm2_rest_api.py $PORT > tpm2_api.log 2>&1 &

# Get the PID
PID=$!

# Wait a moment to see if it starts successfully
sleep 2

# Check if process is still running
if ps -p $PID > /dev/null 2>&1; then
    echo "✓ TPM2 REST API started successfully!"
    echo "  PID: $PID"
    echo "  Port: $PORT"
    echo "  Log file: $SCRIPT_DIR/tpm2_api.log"
    echo "  API URL: http://localhost:$PORT"
    echo "  Health check: http://localhost:$PORT/health"
    echo ""
    echo "To view logs: tail -f $SCRIPT_DIR/tpm2_api.log"
    echo "To stop: kill $PID"
    echo "To check status: ps aux | grep tpm2_rest_api"
else
    echo "✗ Failed to start TPM2 REST API"
    echo "Check the log file: $SCRIPT_DIR/tpm2_api.log"
    exit 1
fi

