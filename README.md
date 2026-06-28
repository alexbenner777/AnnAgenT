# LOS — Life Operating System (Phase 1 MVP)

Персональный мультиагентный ассистент в Telegram. Единый интерфейс — чат (Аня),
язык — русский. Реализована **Фаза 1** ТЗ v2.0 + новый агент напоминаний о препаратах.

## Что уже работает (MVP)

| Компонент | Статус |
|---|---|
| 🧭 Master Orchestrator (ReAct, function calling) | ✅ |
| 🔋 Neuro & Bio Agent (Oura + субъективный ввод) | ✅ |
| 🎯 Decision Support (брифинг 07:00 / дайджест 22:00 / ad-hoc анализ) | ✅ |
| 💊 Medication Reminder Agent (график + напоминания + журнал) | ✅ |
| 🧠 Постоянная память: SQLite (переживает перезапуск, без сервера) | ✅ |
| 🧠 Семантическая память (Mem0/pgvector) + ночная рефлексия | ⏳ план |
| 🎙 Голос → текст (Whisper) | ✅ |
| ⏰ Планировщик (APScheduler) | ✅ |
| 🔮 Esoteric / ❤️ Health / 🤝 Network / Comm Intel | ⏳ заглушки (Фаза 2) |

**Грациозная деградация:** бот стартует даже без БД/Oura/Mem0. Минимум для запуска —
`TELEGRAM_BOT_TOKEN`; для понимания свободного текста и голоса добавь `OPENAI_API_KEY`.

## Быстрый старт (локально, macOS)

```bash
cd los
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # впиши TELEGRAM_BOT_TOKEN и ANTHROPIC_API_KEY
python main.py
```

В Telegram: напиши боту `/start`.

### Минимальный .env для первого теста
```
TELEGRAM_BOT_TOKEN=123:ABC
ANTHROPIC_API_KEY=sk-ant-...   # «мозги» (Claude)
# OPENAI_API_KEY=sk-...        # опционально — только для голосовых (Whisper)
```
Данные сохраняются в локальный файл **SQLite** (`los_data.db`) — переживают перезапуск,
никакой настройки не нужно. «Мозги» — Claude (Opus 4.8); голосовые распознаёт Whisper
(OpenAI), поэтому для голоса нужен ещё `OPENAI_API_KEY`.

## Команды и примеры

- `/briefing` — утренний брифинг сейчас
- `/status` — состояние и Readiness
- `/meds` — препараты на сегодня
- `/state` — пошаговый ввод самочувствия (кнопки 1–10)
- Свободный текст / 🎙 голос:
  - «Стоит ли проводить стратегическую встречу сегодня?»
  - «Добавь витамин D 2000 МЕ в 09:00 с едой»
  - «Запомни: Иван Петров любит встречи до 11 утра»

## Как работают напоминания о таблетках

1. Добавляешь препарат (через свободную команду → `add_medication`).
2. Планировщик раз в минуту проверяет график (`medication.compute_due`).
3. В нужное время приходит сообщение с кнопками **[✅ Принял] [⏭ Пропустить] [💤 +15м]**.
4. Если не подтверждено — повтор через 15 мин (до 3 раз). «+15м» откладывает разово.
5. Статусы пишутся в `medication_intake_log` (журнал приёма).

## Деплой на Replit

1. Загрузи папку `los/` в новый Repl (Python).
2. Внеси секреты в **Tools → Secrets** (те же, что в `.env`).
3. Подключи **Replit PostgreSQL** (Add-on) → `DATABASE_URL` появится автоматически.
   - для семантической таблицы нужен pgvector; без него MVP тоже работает (Mem0 опц.).
4. Включи **Always-on** / Reserved VM, чтобы планировщик жил круглосуточно.
5. `.replit` и `replit.nix` уже в комплекте (`run = python main.py`, есть ffmpeg).

## Структура

```
los/
├── main.py                 # запуск бота + планировщика
├── config.py               # настройки из env
├── services.py             # контейнер зависимостей (DB/OpenAI/Oura/Mem0/bot)
├── bot/                    # handlers, keyboards, voice
├── orchestrator/           # master (ReAct), router, tools (function calling)
├── agents/                 # neuro_bio, decision_support, medication (+ Фаза 2 заглушки)
├── memory/                 # mem0_client, episodic
├── integrations/           # oura, whisper, calendar
├── database/               # db, crud, migrations/*.sql
└── scheduler/              # jobs (07:00 / 22:00 / тик препаратов)
```

## Отклонения от исходного ТЗ (осознанные)

- «Мозги» (оркестратор + агенты) — **Claude (Opus 4.8)** через Anthropic tool use.
  Голос остаётся на **Whisper (OpenAI)** — у Claude нет своего STT.
- Хранилище — **SQLite** (файл, без сервера): постоянное по умолчанию, ноль настройки.
  Postgres + pgvector — задел на будущее (для смыслового поиска), пока не подключён.
- Маршрутизация агентов — через **tool use** в оркестраторе
  (эвристический роутер оставлен как fallback без LLM).
- Google Calendar — задел (`integrations/calendar.py` читает таблицу `calendar_events`);
  полноценный OAuth — отдельный шаг.
- `semantic_memories` (pgvector) вынесена в отдельную необязательную миграцию.
```
