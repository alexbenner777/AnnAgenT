# Деплой LOS на Railway (постоянный хостинг 24/7)

Бот — это «воркер» (long-polling Telegram, без веб-порта). Хранилище — файл SQLite
`los_data.db`, поэтому нужен **постоянный диск (Volume)**, иначе данные обнулятся при
каждом обновлении.

## Что уже готово в репозитории
- `Procfile` → `worker: python -u main.py` (Railway так запускает бота)
- `.python-version` → `3.11`
- `requirements.txt` → без `mem0ai` (не используем)
- `.gitignore` → не пускает в репозиторий `.env` и `los_data.db` (секреты/данные не утекают)

## Шаги в Railway (один раз)
1. Зайти на railway.app → **New Project → Deploy from GitHub repo** → выбрать `alexbenner777/los`.
2. Дождаться первой сборки (она упадёт без переменных — это нормально, добавим ниже).
3. **Variables** (Settings → Variables) — добавить (значения взять из локального `.env`):
   - `TELEGRAM_BOT_TOKEN`
   - `ANTHROPIC_API_KEY`
   - `ANTHROPIC_MODEL` = `claude-opus-4-8`
   - `OPENAI_API_KEY`  (голос/Whisper)
   - `LOS_TIMEZONE` = `Europe/Moscow`
   - `LOS_CHAT_ID`  (необязательно — для проактивных сообщений)
   - `LOS_DB_PATH` = `/data/los_data.db`   ← важно, путь на диск
4. **Volume**: сервис → вкладка Volumes → New Volume, **Mount path** = `/data`.
5. Redeploy. В логах должно быть `✅ LOS запущен` и `Run polling for bot @agent_orcestror_bot`.

## ВАЖНО: только один экземпляр
Telegram пускает только один long-poll. Когда бот заработает на Railway —
**останови локальный на Маке** (иначе `TelegramConflictError`):
```
pkill -f "main.py"   # или kill по PID
```
И наоборот: чтобы временно вернуть на Мак — поставь Railway-сервис на паузу.

## Данные
Облачный диск стартует пустым. Данные рождения/контакты/препараты проще ввести заново
через бота (`/birth …`, и т.д.). При желании можно залить существующий `los_data.db`
на Volume — спроси, помогу.

## Обновления
После любых правок: `git push` → Railway сам пересоберёт и перезапустит бота.
