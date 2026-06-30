---
name: LOS Mini App architecture
description: Architecture decisions for the LOS Telegram Mini App
---

**Stack:** React + Vite (port 5000) + TypeScript + Tailwind + Framer Motion + Recharts + Lucide React. FastAPI (port 8001). SQLite (los_miniapp.db — separate from bot's los.db).

**Startup:** `start_miniapp.sh` — starts `python miniapp_api.py &` (background) then `cd frontend && exec npm run dev`. Configured as "Start application" workflow in .replit with `outputType = "webview"` and `waitForPort = 5000`.

**Vite config requirement:** `allowedHosts: true` in `frontend/vite.config.ts` is required for Replit's mTLS proxy to work. Without it, Replit proxy blocks requests.

**Role-based access:** UserContext in App.tsx. `role: 'anya'` sees all 12 pages. `role: 'den'` redirected away from /health. Toggled in SettingsPage.

**Design tokens:** #F4F6F9 background, rgba(255,255,255,0.55) glass cards, #5B9DB8 accent. All in frontend/src/index.css via @layer components (.glass-card, .glass-tab-bar, .accent-button, etc.).

**API structure:** All endpoints under /api prefix. Vite proxy forwards /api → http://localhost:8001. CORS allows all origins in development.

**miniapp_api.py:** 859 lines, auto-installs fastapi+uvicorn on first import. Seeds demo data into los_miniapp.db on startup via lifespan. All endpoints: /api/health/*, /api/calendar/*, /api/finances/*, /api/state/*, /api/briefing/*, /api/contacts/*, /api/meetings/*, /api/reminders/*, /api/settings, /api/dashboard.

## ⚠️ Replit Canvas limitation — DO NOT try to fix in code

The Replit Canvas board CANNOT embed the running app. The artifact iframe in the canvas always shows blank white. This is a platform-level mTLS/security restriction — not a code bug. Spent many turns trying to fix it with no success.

**Why:** Canvas board iframes can't load Replit-proxied app URLs (*.picard.replit.dev) when nested inside the canvas board context.

**What to tell users:** "Click the ↗ icon in the preview address bar to open the app in a new browser tab" — OR — "Click the blue Canvas button in the preview sub-header to toggle off canvas mode."
