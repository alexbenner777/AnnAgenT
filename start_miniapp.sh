#!/bin/bash
echo "=== LOS Mini App ==="

# Build and copy React frontend to public/
echo "Building frontend..."
cd frontend && npm run build 2>&1 | tail -3
cd ..
echo "Copying frontend build to public/..."
cp -r frontend/dist/* public/

echo "Starting FastAPI backend on port 8001..."
python miniapp_api.py &

echo "Starting frontend server on port 5000..."
exec python los_server.py
