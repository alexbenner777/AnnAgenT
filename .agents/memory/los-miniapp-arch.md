---
name: LOS Mini App architecture
description: Architecture decisions for the LOS Telegram Mini App
---

**Stack:** React + Vite (port 5000) + TypeScript + Tailwind + Framer Motion + Recharts + Lucide React. FastAPI (port 8001). SQLite (los_miniapp.db — separate from bot's los.db).

**Startup:** `start_miniapp.sh` — starts `python miniapp_api.py &` (background) then `cd frontend && npm install && exec npm run dev`. Configured as "Start application" workflow in .replit.

**Role-based access:** UserContext in App.tsx. `role: 'anya'` sees all 12 pages. `role: 'den'` redirected away from /health. Toggled in SettingsPage.

**Design tokens:** #F4F6F9 background, rgba(255,255,255,0.55) glass cards, #5B9DB8 accent. All in frontend/src/index.css via @layer components (.glass-card, .glass-tab-bar, .accent-button, etc.).

**API structure:** All endpoints under /api prefix. Vite proxy forwards /api → http://localhost:8001. CORS allows all origins in development.

**miniapp_api.py:** 859 lines, auto-installs fastapi+uvicorn on first import. Seeds demo data into los_miniapp.db on startup via lifespan. All endpoints: /api/health/*, /api/calendar/*, /api/finances/*, /api/state/*, /api/briefing/*, /api/contacts/*, /api/meetings/*, /api/reminders/*, /api/settings, /api/dashboard.
