# LOS — Life Operating System

Personal AI assistant: Telegram bot + Mini App.  
Agents for health, calendar, finances, contacts, meetings, astrology — powered by Claude.

## Stack

| Layer | Tech |
|-------|------|
| Bot | Python · aiogram 3 · APScheduler |
| AI brain | Anthropic Claude (claude-opus-4-8) |
| Voice | OpenAI Whisper |
| Mini App API | FastAPI · port 8001 |
| Mini App UI | React 18 · Vite · Tailwind · port 5000 |
| DB | SQLite (los_miniapp.db) |

## First-time setup on a new Replit

1. **Add Secrets** (Replit → Secrets tab):
   - `TELEGRAM_BOT_TOKEN` — from [@BotFather](https://t.me/BotFather)
   - `ANTHROPIC_API_KEY` — from [console.anthropic.com](https://console.anthropic.com)
   - `OPENAI_API_KEY` — for voice transcription (optional but recommended)

2. **Click Run** — `start_miniapp.sh` auto-installs all deps, builds the frontend, starts both servers.

3. **Preview** opens on port 5000 (the Mini App UI).

That's it — no manual pip install, no npm install needed.

## Optional secrets

| Secret | Purpose |
|--------|---------|
| `OURA_ACCESS_TOKEN` | Oura Ring health data |
| `GOOGLE_CALENDAR_ICS_URL` | Calendar sync (or set via /calendar bot command) |
| `LOS_OWNER_IDS` | Comma-separated Telegram user IDs allowed to use the bot |
| `LOS_CHAT_ID` | Chat ID for proactive messages (briefings, reminders) |
| `LOS_TIMEZONE` | Default: `Europe/Moscow` |
| `ELEVENLABS_API_KEY` | Better Russian voice transcription |

## Architecture

```
start_miniapp.sh
├── python miniapp_api.py   → FastAPI REST API   :8001
└── python los_server.py    → Static files + proxy :5000
                               └── /api/* → proxied to :8001
                               └── /*    → frontend/dist (React SPA)

python main.py              → Telegram bot (run separately or add to start_miniapp.sh)
```

## Running the Telegram bot

The Mini App and the bot are separate processes. To run the bot alongside the Mini App, add this line to `start_miniapp.sh` before the last `exec`:

```bash
python main.py &
```

Or run it in a second workflow named **Start bot**.

## User preferences

- Language: Russian (code comments and bot responses in Russian)
- Timezone: Europe/Moscow
