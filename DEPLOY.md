# Деплой LOS на Render (постоянный хостинг 24/7)

Бот — это **Background Worker** (long-polling Telegram, без веб-порта). Хранилище —
файл SQLite `los_data.db`, поэтому нужен **постоянный Disk**, иначе данные обнулятся
при каждом обновлении.

⚠️ Тарифы Render: у воркера нет бесплатного плана, Disk доступен только на платном
инстансе. Итог ≈ **$7/мес** (worker `starter`) + ~$0.25 за 1 ГБ диска.

## Что уже готово в репозитории
- `render.yaml` — Render сам создаст воркер + диск + переменные (Blueprint).
- `requirements.txt` — без `mem0ai` (не используем).
- `.gitignore` — не пускает в репозиторий `.env` и `los_data.db` (секреты/данные не утекают).
- (`Procfile`/`.python-version` — для Railway, на Render не мешают; версия Python тут задаётся в render.yaml.)

## Способ 1 — Blueprint (рекомендую, меньше кликов)
1. render.com → **New → Blueprint**.
2. Подключи GitHub-репозиторий `alexbenner777/los` → Render прочитает `render.yaml`.
3. Render спросит значения секретных переменных (помечены `sync: false`) — впиши из `.env`:
   - `TELEGRAM_BOT_TOKEN`
   - `ANTHROPIC_API_KEY`
   - `OPENAI_API_KEY`  (голос/Whisper)
   - `LOS_CHAT_ID`  (необязательно — для проактивных сообщений)
   (остальные — `LOS_DB_PATH`, `LOS_TIMEZONE`, `ANTHROPIC_MODEL`, `PYTHON_VERSION` — уже в render.yaml)
4. **Apply** → Render соберёт и запустит. Диск `/data` создастся автоматически.
5. В логах ждём `✅ LOS запущен` и `Run polling for bot @agent_orcestror_bot`.

## Способ 2 — вручную (если не хочешь Blueprint)
1. **New → Background Worker** → подключи репозиторий `alexbenner777/los`.
2. Build command: `pip install -r requirements.txt` · Start command: `python -u main.py`.
3. Вкладка **Disk**: New Disk, Mount path = `/data`, размер 1 ГБ.
4. **Environment**: добавь переменные (как в Способе 1) + `LOS_DB_PATH=/data/los_data.db`,
   `LOS_TIMEZONE=Europe/Moscow`, `ANTHROPIC_MODEL=claude-opus-4-8`, `PYTHON_VERSION=3.11.9`.
5. Create → дождись деплоя, проверь логи.

## ВАЖНО: только один экземпляр
Telegram пускает только один long-poll. Когда бот заработает на Render —
**останови локальный на Маке** (иначе `TelegramConflictError`):
```
pkill -f "main.py"
```

## Данные
Облачный диск стартует пустым. Данные рождения/контакты/препараты проще ввести заново
через бота (`/birth …` и т.д.). Хочешь — помогу залить существующий `los_data.db` на диск.

## Обновления
После любых правок: `git push` → Render сам пересоберёт и перезапустит бота (autoDeploy).
