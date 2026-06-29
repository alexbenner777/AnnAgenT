#!/bin/bash
echo "=== LOS Mini App ==="
echo "Starting FastAPI backend on port 8001..."
python miniapp_api.py &

echo "Starting frontend server on port 5000..."
exec python los_server.py
