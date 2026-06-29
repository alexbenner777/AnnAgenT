#!/bin/bash
echo "=== LOS Mini App ==="

# Start FastAPI backend in background (auto-installs fastapi/uvicorn on first run)
python miniapp_api.py &

# Install and start frontend
cd frontend
npm install
exec npm run dev
