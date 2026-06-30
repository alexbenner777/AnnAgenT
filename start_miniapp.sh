#!/bin/bash
set -e
echo "=== LOS Mini App ==="

# ── 1. Python deps ───────────────────────────────────────────────────
if ! python3 -c "import fastapi, aiogram, anthropic" 2>/dev/null; then
  echo "Installing Python packages..."
  pip install -r requirements.txt -q
fi

# ── 2. Node deps ─────────────────────────────────────────────────────
if [ ! -d "frontend/node_modules" ]; then
  echo "Installing Node packages..."
  cd frontend && npm install --silent && cd ..
fi

# ── 3. Start FastAPI backend ─────────────────────────────────────────
echo "Starting FastAPI backend on port 8001..."
python miniapp_api.py &

# ── 4. Start Vite dev server on port 5000 ────────────────────────────
echo "Starting frontend dev server on port 5000..."
cd frontend && exec npm run dev
