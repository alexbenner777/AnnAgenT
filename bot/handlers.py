"""Telegram-хендлеры: команды, меню, пошаговый ввод состояния, действия по
препаратам, голос и свободный текст (→ оркестратор)."""
import logging
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery

from database import crud
from bot.keyboards import main_menu, scale_kb, yesno_kb, esoteric_kb

log = logging.getLogger("los.handlers")

WELCOME = (
    "👋 Это <b>LOS</b> — твой цифровой штаб.\n"
    "Свожу состояние, расписание, приём препаратов, анализы, напоминания, людей и "
    "«качество дня» в один чат и подсказываю, что делать.\n\n"
    "Команды: /briefing /status /meds /health /reminders /calendar /contacts /day /state /help\n"
    "Или просто пиши текстом / голосом 🎙, шли фото бланка анализов и жми кнопки ниже."
)

HELP = (
    "📋 /briefing — утренний брифинг сейчас\n"
    "🔋 /status — состояние и готовность\n"
    "💊 /meds — препараты на сегодня\n"
    "⏰ /reminders — мои напоминания\n"
    "📅 /calendar — подключить/показать календарь\n"
    "👥 /contacts — мои контакты\n"
    "❤️ /health — анализы и динамика · /visits — визиты к врачам\n"
    "🔮 /day — качество дня · /why — расшифровка · /birth — данные\n"
    "📝 /state — ввести самочувствие\n\n"
    "<b>Свободные команды</b> (текст или голос):\n"
    "• «Напомни завтра в 9 позвонить юристу»\n"
    "• «Напомни каждый день в 8 выпить воду»\n"
    "• «Добавь финебут по субботам в 21:00»\n"
    "• «Запомни: Иван Петров любит встречи до 11 утра»\n\n"
    "<b>❤️ Здоровье:</b>\n"
    "• Пришли фото или PDF бланка анализов — разберу и буду вести динамику\n"
    "• «Динамика витамина D» — тренд по показателю\n"
    "• «Расскажи про магний, как сочетается с моими препаратами»\n"
    "• «Запиши визит к кардиологу 30 июня, плановый осмотр»"
)

CALENDAR_HELP = (
    "📅 <b>Подключить Google Календарь</b> (30 секунд, без программирования):\n\n"
    "1. Открой Google Календарь на компьютере.\n"
    "2. Слева наведи на нужный календарь → ⋮ → «Настройки и общий доступ».\n"
    "3. Прокрути вниз до «Интеграция календаря».\n"
    "4. Скопируй «<b>Секретный адрес в формате iCal</b>» (ссылка на .ics).\n"
    "5. Пришли мне: <code>/calendar ВСТАВЬ_ССЫЛКУ</code>\n\n"
    "Потом переключить на основной — просто пришли другую ссылку той же командой.\n"
    "Отключить — <code>/calendar off</code>.\n"
    "⚠️ Это секретная ссылка (по ней видно твой календарь) — никому не пересылай."
)

STATE_ORDER = ["energy", "focus", "mood", "workout", "massage", "alcohol"]
STATE_PROMPT = {
    "energy": "Оцени ЭНЕРГИЮ (1–10):",
    "focus": "ФОКУС (1–10):",
    "mood": "НАСТРОЕНИЕ (1–10):",
    "workout": "Тренировка была?",
    "massage": "Массаж был?",
    "alcohol": "Алкоголь был?",
}
SCALE_FIELDS = {"energy", "focus", "mood"}


def build_router(services) -> Router:
    router = Router()
    cfg = services.config
    db = services.db
    pending: dict[int, dict] = {}  # chat_id -> частично заполненное состояние

    async def ask_state(target: Message, field: str):
        kb = scale_kb(field) if field in SCALE_FIELDS else yesno_kb(field)
        await target.answer(STATE_PROMPT[field], reply_markup=kb)

    async def do_briefing(target: Message):
        from agents import decision_support
        await target.answer("Собираю брифинг…")
        await target.answer(await decision_support.run(services, mode="morning"))

    async def do_status(target: Message):
        from agents import neuro_bio
        await target.answer(await neuro_bio.run(services))

    async def do_meds(target: Message):
        from agents import medication
        await target.answer(await medication.schedule_text(services))

    async def do_reminders(target: Message):
        from agents import reminders
        await target.answer(await reminders.list_text(services))

    async def do_calendar(target: Message):
        from integrations import calendar
        await target.answer(await calendar.schedule_text(services))

    async def do_contacts(target: Message):
        from agents import network
        await target.answer(await network.list_text(services))

    async def do_health(target: Message):
        from agents import health
        await target.answer(await health.overview_text(services))

    # ---------- команды ----------
    @router.message(CommandStart())
    async def _start(m: Message):
        await crud.upsert_user(db, m.from_user.id, m.chat.id, m.from_user.full_name)
        await m.answer(WELCOME, reply_markup=main_menu())

    @router.message(Command("help"))
    async def _help(m: Message):
        await m.answer(HELP, reply_markup=main_menu())

    @router.message(Command("briefing"))
    async def _brief(m: Message):
        await do_briefing(m)

    @router.message(Command("status"))
    async def _status(m: Message):
        await do_status(m)

    @router.message(Command("meds"))
    async def _meds(m: Message):
        await do_meds(m)

    @router.message(Command("reminders"))
    async def _reminders(m: Message):
        await do_reminders(m)

    @router.message(Command("calendar"))
    async def _calendar(m: Message):
        from integrations import calendar
        arg = (m.text or "").partition(" ")[2].strip()
        if not arg:
            if await calendar.get_url(services):
                await m.answer(await calendar.schedule_text(services))
            else:
                await m.answer(CALENDAR_HELP)
            return
        if arg.lower() in ("off", "выкл", "отключить", "stop"):
            await crud.set_setting(db, "gcal_ics_url", "")
            await m.answer("📅 Календарь отключён.")
            return
        n = await calendar.probe(arg, cfg.tz)
        if n is None:
            await m.answer("⚠️ Не смог прочитать календарь по ссылке. Нужен "
                           "«Секретный адрес в формате iCal» (оканчивается на .ics).")
            return
        await crud.set_setting(db, "gcal_ics_url", calendar.normalize(arg))
        await m.answer(f"✅ Календарь подключён. Событий сегодня: {n}.\n\n"
                       + await calendar.schedule_text(services))

    @router.message(Command("contacts"))
    async def _contacts(m: Message):
        await do_contacts(m)

    @router.message(Command("health"))
    async def _health(m: Message):
        await do_health(m)

    @router.message(Command("visits"))
    async def _visits(m: Message):
        from agents import health
        await m.answer(await health.visits_text(services))

    @router.message(Command("birth"))
    async def _birth(m: Message):
        from integrations import geocode
        from agents import esoteric
        from orchestrator.tools import parse_date, parse_time
        arg = (m.text or "").partition(" ")[2].strip()
        if not arg:
            b = await crud.get_birth(db)
            await m.answer("🔮 Данные рождения: " + esoteric.birth_summary(b)
                           + "\nЗадать: /birth 14.03.1985 09:20 Москва")
            return
        parts = arg.split()
        iso = parse_date(parts[0])
        if not iso:
            await m.answer("Не понял дату. Пример: /birth 14.03.1985 09:20 Москва")
            return
        rest = parts[1:]
        tm = None
        if rest and parse_time(rest[0]):
            tm = parse_time(rest[0]); rest = rest[1:]
        city = " ".join(rest) if rest else None
        birth = {"date": iso, "time": tm, "city": city}
        if city:
            g = await geocode.geocode(city)
            if g:
                birth.update({"lat": g["lat"], "lon": g["lon"], "tz": g["tz"], "city": g["city"]})
        await crud.set_birth(db, birth)
        await m.answer("✅ Записал: " + esoteric.birth_summary(birth) + "\nПопробуй /day.")

    @router.message(Command("day"))
    async def _day(m: Message):
        from agents import esoteric
        await m.answer("🔮 Считаю качество дня…")
        await m.answer(await esoteric.day_quality(services), reply_markup=esoteric_kb())

    @router.message(Command("why"))
    async def _why(m: Message):
        from agents import esoteric
        await m.answer(await esoteric.facts_text(services))

    @router.callback_query(F.data == "eso:facts")
    async def _eso_facts(cb: CallbackQuery):
        from agents import esoteric
        await cb.message.answer(await esoteric.facts_text(services))
        await cb.answer()

    @router.message(Command("state"))
    async def _state(m: Message):
        pending[m.chat.id] = {}
        await ask_state(m, "energy")

    # ---------- меню (callbacks) ----------
    @router.callback_query(F.data.startswith("menu:"))
    async def _menu(cb: CallbackQuery):
        action = cb.data.split(":", 1)[1]
        if action == "briefing":
            await do_briefing(cb.message)
        elif action == "status":
            await do_status(cb.message)
        elif action == "meds":
            await do_meds(cb.message)
        elif action == "reminders":
            await do_reminders(cb.message)
        elif action == "calendar":
            await do_calendar(cb.message)
        elif action == "contacts":
            await do_contacts(cb.message)
        elif action == "health":
            await do_health(cb.message)
        elif action == "help":
            await cb.message.answer(HELP)
        elif action == "state":
            pending[cb.message.chat.id] = {}
            await ask_state(cb.message, "energy")
        await cb.answer()

    # ---------- пошаговый ввод состояния ----------
    @router.callback_query(F.data.startswith("st:"))
    async def _state_cb(cb: CallbackQuery):
        _, field, value = cb.data.split(":")
        chat = cb.message.chat.id
        st = pending.setdefault(chat, {})
        st[field] = int(value) if field in SCALE_FIELDS else (value == "yes")

        idx = STATE_ORDER.index(field)
        if idx + 1 < len(STATE_ORDER):
            await cb.answer()
            await ask_state(cb.message, STATE_ORDER[idx + 1])
            return

        pending.pop(chat, None)
        day = datetime.now(cfg.tz).date()
        await crud.upsert_daily_health(
            db, day,
            energy_subjective=st.get("energy"), focus_subjective=st.get("focus"),
            mood_subjective=st.get("mood"), workout_done=st.get("workout"),
            massage_done=st.get("massage"), alcohol=st.get("alcohol"))
        await cb.answer("Сохранено ✅")
        await cb.message.answer(
            "📝 Состояние записано:\n"
            f"Энергия {st.get('energy')}/10 · Фокус {st.get('focus')}/10 · "
            f"Настроение {st.get('mood')}/10\n"
            f"Тренировка: {'да' if st.get('workout') else 'нет'} · "
            f"Массаж: {'да' if st.get('massage') else 'нет'} · "
            f"Алкоголь: {'да' if st.get('alcohol') else 'нет'}")

    # ---------- действия по препаратам ----------
    @router.callback_query(F.data.startswith("med:"))
    async def _med_cb(cb: CallbackQuery):
        _, action, mid, ts = cb.data.split(":")
        med_id = int(mid)
        scheduled = datetime.strptime(ts, "%Y%m%d%H%M")
        if action == "taken":
            await crud.set_intake_status(db, med_id, scheduled, "taken")
            note = "✅ Принято"
        elif action == "skip":
            await crud.set_intake_status(db, med_id, scheduled, "skipped")
            note = "⏭ Пропущено"
        else:  # snooze
            await crud.set_intake_status(db, med_id, scheduled, "snoozed")
            note = f"💤 Напомню через {cfg.medication_repeat_minutes} мин"
            await _schedule_snooze(med_id, cb.message.chat.id)
        try:
            await cb.message.edit_text(f"{cb.message.text}\n\n{note}")
        except Exception:
            pass
        await cb.answer(note)

    async def _schedule_snooze(med_id: int, chat_id: int):
        from scheduler.jobs import send_single_reminder
        if not services.scheduler:
            return
        meds = await crud.list_active_medications(db)
        med = next((m for m in meds if m["id"] == med_id), None)
        if not med:
            return
        run_at = datetime.now(cfg.tz) + timedelta(minutes=cfg.medication_repeat_minutes)
        new_sched = run_at.replace(tzinfo=None)
        services.scheduler.add_job(
            send_single_reminder, "date", run_date=run_at,
            args=[services, chat_id, med, new_sched])

    # ---------- действия по напоминаниям ----------
    @router.callback_query(F.data.startswith("rem:"))
    async def _rem_cb(cb: CallbackQuery):
        _, action, rid, ts = cb.data.split(":")
        rem_id = int(rid)
        scheduled = datetime.strptime(ts, "%Y%m%d%H%M")
        if action == "taken":
            await crud.set_reminder_status(db, rem_id, scheduled, "taken")
            note = "✅ Готово"
        elif action == "skip":
            await crud.set_reminder_status(db, rem_id, scheduled, "skipped")
            note = "⏭ Пропущено"
        else:  # snooze
            await crud.set_reminder_status(db, rem_id, scheduled, "snoozed")
            note = f"💤 Напомню через {cfg.medication_repeat_minutes} мин"
            await _schedule_snooze_rem(rem_id, cb.message.chat.id)
        if action in ("taken", "skip"):
            rem = await crud.get_reminder(db, rem_id)
            if rem and rem.get("due_at"):   # разовое — закрыть совсем
                await crud.deactivate_reminder(db, rem_id)
        try:
            await cb.message.edit_text(f"{cb.message.text}\n\n{note}")
        except Exception:
            pass
        await cb.answer(note)

    async def _schedule_snooze_rem(rem_id: int, chat_id: int):
        from scheduler.jobs import send_single_reminder_rem
        if not services.scheduler:
            return
        rem = await crud.get_reminder(db, rem_id)
        if not rem:
            return
        run_at = datetime.now(cfg.tz) + timedelta(minutes=cfg.medication_repeat_minutes)
        services.scheduler.add_job(
            send_single_reminder_rem, "date", run_date=run_at,
            args=[services, chat_id, rem, run_at.replace(tzinfo=None)])

    # ---------- анализы: фото и документы (PDF/изображения) ----------
    @router.message(F.photo)
    async def _photo(m: Message):
        from bot.upload import download_bytes
        from agents import health
        await m.answer("🧪 Похоже на анализы — разбираю…")
        data = await download_bytes(services, m.photo[-1].file_id)
        if not data:
            await m.answer("Не смог скачать фото. Попробуй ещё раз.")
            return
        await m.answer(await health.ingest_file(services, data, "image/jpeg", "photo"))

    @router.message(F.document)
    async def _document(m: Message):
        from bot.upload import download_bytes
        from agents import health
        doc = m.document
        mime = (doc.mime_type or "").lower()
        name = (doc.file_name or "").lower()
        is_pdf = mime == "application/pdf" or name.endswith(".pdf")
        is_img = mime.startswith("image/") or name.endswith((".jpg", ".jpeg", ".png", ".webp"))
        if not (is_pdf or is_img):
            await m.answer("Пришли бланк анализов фото или PDF — разберу и буду вести динамику.")
            return
        await m.answer("🧪 Разбираю анализы…")
        data = await download_bytes(services, doc.file_id)
        if not data:
            await m.answer("Не смог скачать файл. Попробуй ещё раз.")
            return
        media_type = "application/pdf" if is_pdf else (mime if mime.startswith("image/") else "image/jpeg")
        await m.answer(await health.ingest_file(services, data, media_type, "pdf" if is_pdf else "photo"))

    # ---------- голос и свободный текст ----------
    @router.message(F.voice)
    async def _voice(m: Message):
        from bot.voice import handle_voice
        text = await handle_voice(services, m)
        if not text:
            await m.answer("Не удалось распознать голос (нужен OPENAI_API_KEY для Whisper).")
            return
        await m.answer(f"🎙 Распознал: <i>{text}</i>")
        await m.answer(await services.orchestrator.handle(text, m.chat.id))

    @router.message(F.text)
    async def _text(m: Message):
        await m.answer(await services.orchestrator.handle(m.text, m.chat.id))

    return router
