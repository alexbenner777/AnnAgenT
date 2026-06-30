#!/bin/bash
set -e
echo "=== LOS Mini App ==="

# ── 1. Python deps ───────────────────────────────────────────────────
if ! python3 -c "import fastapi, aiogram, anthropic" 2>/dev/null; then
  echo "Installing Python packages..."
  pip install -r requirements.txt --break-system-packages -q
fi

# ── 2. Node deps ─────────────────────────────────────────────────────
if [ ! -d "frontend/node_modules" ]; then
  echo "Installing Node packages..."
  cd frontend && npm install --silent && cd ..
fi

# ── 3. Build frontend (only if source changed or dist missing) ───────
DIST="frontend/dist/index.html"
SRC_CHANGED=false
if [ ! -f "$DIST" ]; then
  SRC_CHANGED=true
elif [ "$(find frontend/src -newer "$DIST" 2>/dev/null | head -1)" != "" ]; then
  SRC_CHANGED=true
fi

if $SRC_CHANGED; then
  echo "Building frontend..."
  cd frontend && npm run build 2>&1 | tail -3 && cd ..
fi

echo "Copying frontend build to public/..."
cp -r frontend/dist/* public/

# ── 4. Start servers ─────────────────────────────────────────────────
echo "Starting FastAPI backend on port 8001..."
python miniapp_api.py &

echo "Starting frontend server on port 5000..."
exec python los_server.py
