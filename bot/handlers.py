"""Telegram-хендлеры: команды, меню, пошаговый ввод состояния, действия по
препаратам, голос и свободный текст (→ оркестратор)."""
import html
import logging
import os
import re
from datetime import datetime, timedelta

from aiogram import Router, F, BaseMiddleware
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest

from database import crud
from bot.keyboards import (main_menu, main_reply_kb, MAIN_BUTTON_ACTIONS,
                           scale_kb, yesno_kb, esoteric_kb, briefing_kb, meeting_kb, health_hub_kb,
                           GROUPS, GROUP_BY_LABEL, group_kb, DIRECT_ACTIONS)
from bot.richfmt import expandable_note, md_to_tg_html

log = logging.getLogger("los.handlers")

WELCOME = (
    "👋 Это <b>LOS</b> — твой цифровой штаб.\n"
    "Свожу состояние, расписание, препараты, анализы, напоминания, людей, разбор встреч "
    "и «качество дня» в один чат и подсказываю, что делать.\n\n"
    "Команды: /briefing /status /meds /health /meeting /reminders /calendar /contacts /day /state /help\n"
    "Пиши текстом / голосом 🎙, шли фото анализов или запись встречи — и жми кнопки ниже."
)

HELP = (
    "📋 /briefing — утренний брифинг сейчас\n"
    "🔋 /status — состояние и готовность\n"
    "💊 /meds — препараты на сегодня\n"
    "⏰ /reminders — напоминания\n"
    "📅 /calendar — подключить/показать календарь\n"
    "👥 /contacts — контакты\n"
    "❤️ /health — анализы и динамика · /visits — визиты к врачам\n"
    "🎙 /meeting — разбор последней встречи\n"
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
    "• «Запиши визит к кардиологу 30 июня, плановый осмотр»\n\n"
    "<b>🎙 Встречи и переговоры:</b>\n"
    "• Пришли запись разговора (длинное голосовое, аудио или видео) — расшифрую и сделаю сводку\n"
    "• Кнопками выбери формат (протокол · переговоры · задачи), перенеси дела в напоминания\n"
    "• «Что по последней встрече», «покажи переговорную сводку», «какие там дела»"
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

STALE_BTN = "Кнопка устарела — открой заново"

# Голосовое длиннее этого — считаем записью встречи (а не голосовой командой)
VOICE_MEETING_SECONDS = 90
# Лимит скачивания обычного Bot API (без локального сервера)
MEETING_MAX_BYTES = 20 * 1024 * 1024
_AUDIO_EXT = (".mp3", ".m4a", ".wav", ".ogg", ".oga", ".opus", ".aac", ".flac", ".amr")
_VIDEO_EXT = (".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v")


class OwnerOnly(BaseMiddleware):
    """🔒 Пропускает только владельца(ев). Чужих вежливо отклоняет и НЕ запускает
    обработчик (доступа к данным нет). Если владелец не настроен (owner_ids пуст) —
    закрыто для всех (fail-closed), но подсказываем, какой id вписать в .env."""

    def __init__(self, owner_ids: set):
        self.owner_ids = set(owner_ids)

    async def __call__(self, handler, event, data):
        user = data.get("event_from_user")
        uid = getattr(user, "id", None)
        if self.owner_ids and uid in self.owner_ids:
            return await handler(event, data)
        if not self.owner_ids:
            txt = ("⚙️ Бот ещё не привязан к владельцу.\n"
                   "Чтобы доступ был только у тебя — добавь в .env строку\n"
                   f"<code>LOS_OWNER_IDS={uid}</code>\nи перезапусти бота.")
        else:
            txt = "🔒 Это личный ассистент LOS. Доступ только у владельца."
        try:
            if isinstance(event, CallbackQuery):
                await event.answer()
                if event.message:
                    await event.message.answer(txt)
            elif isinstance(event, Message):
                await event.answer(txt)
        except Exception:
            pass
        return None


def build_router(services) -> Router:
    router = Router()
    cfg = services.config
    db = services.db
    pending: dict[int, dict] = {}  # chat_id -> частично заполненное состояние
    meeting_busy: set = set()      # чаты, где сейчас идёт разбор записи (защита от наложения)

    owner_mw = OwnerOnly(cfg.owner_ids)
    router.message.middleware(owner_mw)
    router.callback_query.middleware(owner_mw)

    async def safe_send(target, text, **kw):
        """Надёжная отправка, чтобы сообщение никогда не пропало в тишину:
        (1) если длинно (>4096) — бьём на части по строкам;
        (2) если HTML-разметка сломалась ('<' '>' '&') — повторяем без разметки."""
        text = text if isinstance(text, str) else str(text)
        LIMIT = 4096
        if len(text) <= LIMIT:
            chunks = [text]
        else:
            chunks, buf = [], ""
            for line in text.split("\n"):
                while len(line) > LIMIT:               # одна строка длиннее лимита
                    chunks.append(line[:LIMIT])
                    line = line[LIMIT:]
                if buf and len(buf) + len(line) + 1 > LIMIT:
                    chunks.append(buf)
                    buf = line
                else:
                    buf = f"{buf}\n{line}" if buf else line
            if buf:
                chunks.append(buf)
        last = len(chunks) - 1
        result = None
        for i, chunk in enumerate(chunks):
            kw_i = kw if i == last else {k: v for k, v in kw.items() if k != "reply_markup"}
            try:
                result = await target.answer(chunk, **kw_i)
            except TelegramBadRequest:
                result = await target.answer(chunk, parse_mode=None, **kw_i)
        return result

    async def show_typing(target):
        """Показать «печатает…», чтобы бот не казался зависшим на долгих ответах."""
        try:
            await services.bot.send_chat_action(target.chat.id, "typing")
        except Exception:
            pass

    async def send_meeting_summary(target, body_md, header="📋 Саммари встречи"):
        """Саммари СВЁРНУТЫМ блоком. Сначала пробуем rich-<details> (Bot API 10.1),
        иначе — стандартная сворачиваемая цитата <blockquote expandable>."""
        from bot import richmsg
        try:
            content = (f"<details><summary>{html.escape(header)}</summary>"
                       f"{richmsg.md_to_html(body_md)}</details>")
            await richmsg.send_rich_html(cfg.telegram_bot_token, target.chat.id, content)
            return
        except Exception:
            pass
        card = expandable_note(header, body_md)
        await safe_send(target, card if len(card) <= 4096 else md_to_tg_html(body_md))

    async def send_meeting_note(target, label, body_md):
        """Заметка РАЗВЁРНУТО (формат/итог): rich-markdown, иначе обычный HTML."""
        from bot import richmsg
        try:
            await richmsg.send_rich_md(cfg.telegram_bot_token, target.chat.id,
                                       f"## {label}\n\n{body_md}")
            return
        except Exception:
            pass
        note = f"<b>{html.escape(label)}</b>\n{md_to_tg_html(body_md)}"
        await safe_send(target, note if len(note) <= 4096 else md_to_tg_html(body_md))

    async def rich(target, md, reply_markup=None):
        """Красивый вид (rich-markdown) с откатом на обычное сообщение, если метод недоступен.
        Маркеры «• » приводим к markdown «- », чтобы списки рисовались как списки."""
        from bot import richmsg
        md = re.sub(r"(?m)^(\s*)•[ \t]+", r"\1- ", md or "")
        await richmsg.send_rich_or_plain(services.bot, cfg.telegram_bot_token,
                                         target.chat.id, md, reply_markup=reply_markup)

    async def stream_reply(target, user_text):
        """Ответ оркестратора «печатается»: шлём заглушку и дописываем её по мере
        генерации Claude (черновик без разметки), в конце — красивый формат."""
        status = await target.answer("✍️ …")
        last = {"txt": ""}

        async def on_delta(buf):
            t = (buf or "")[:4000]
            if t == last["txt"]:
                return
            last["txt"] = t
            try:
                await status.edit_text(t, parse_mode=None)
            except TelegramBadRequest:
                pass

        text = (await services.orchestrator.handle(user_text, target.chat.id, on_delta=on_delta)) or "…"
        try:
            await status.edit_text(md_to_tg_html(text)[:4096])     # финал: parse_mode=HTML по умолчанию
        except TelegramBadRequest:
            try:
                await status.edit_text(text[:4096], parse_mode=None)
            except TelegramBadRequest:
                pass

    async def ask_state(target: Message, field: str):
        kb = scale_kb(field) if field in SCALE_FIELDS else yesno_kb(field)
        await target.answer(STATE_PROMPT[field], reply_markup=kb)

    async def do_briefing(target: Message):
        from agents import decision_support
        from bot import richmsg
        await show_typing(target)
        await target.answer("Собираю брифинг…")
        md = await decision_support.run(services, mode="morning")
        await richmsg.send_rich_or_plain(services.bot, cfg.telegram_bot_token,
                                         target.chat.id, md, reply_markup=briefing_kb())

    async def do_status(target: Message):
        from agents import neuro_bio
        await show_typing(target)
        await rich(target, await neuro_bio.run(services))

    async def do_meds(target: Message):
        from agents import medication
        await show_typing(target)
        await rich(target, await medication.schedule_text(services))

    async def do_reminders(target: Message):
        from agents import reminders
        await show_typing(target)
        await rich(target, await reminders.list_text(services))

    async def do_calendar(target: Message):
        from integrations import calendar
        await show_typing(target)
        await rich(target, await calendar.schedule_text(services))

    async def do_contacts(target: Message):
        from agents import network
        await show_typing(target)
        await rich(target, await network.list_text(services))

    async def do_health(target: Message):
        from agents import health
        await show_typing(target)
        await rich(target, await health.overview_text(services))

    async def do_digest(target: Message):
        from agents import decision_support
        from bot import richmsg
        await show_typing(target)
        await target.answer("Собираю итог дня…")
        md = await decision_support.run(services, mode="evening")
        await richmsg.send_rich_or_plain(services.bot, cfg.telegram_bot_token, target.chat.id, md)

    async def do_now(target):
        """⚡ Инбокс ассистента: что требует действия прямо сейчас."""
        from agents import medication, reminders
        await show_typing(target)
        today = datetime.now(cfg.tz).date()
        blocks = ["# 📋 Задачи — что сейчас от тебя"]
        dh = await crud.get_daily_health(db, today) or {}
        if dh.get("energy_subjective") is None:
            blocks.append("- ✍️ **Состояние** на сегодня не внесено — кнопка «Внести состояние» или /state")
        meds = await medication.schedule_text(services, header=False)
        if meds and "нет" not in meds.lower():
            blocks.append(f"## 💊 Таблетки сегодня\n{meds}")
        rem = await reminders.list_text(services)
        if rem and "нет" not in rem.lower():
            blocks.append(rem)
        if len(blocks) == 1:
            blocks.append("Всё закрыто — срочного ничего 👍")
        await rich(target, "\n\n".join(blocks))

    async def do_meeting(target: Message):
        from agents import communication
        await show_typing(target)
        m = await crud.latest_meeting(db, target.chat.id)
        if not m:
            await safe_send(target, "Пока нет разобранных встреч. Пришли запись разговора "
                            "(голосом, аудио или видео) — расшифрую и сделаю заметку.")
            return
        await safe_send(target, f"🎙 <b>{html.escape(m['title'])}</b>")
        body = m.get("summary") or await communication.format_meeting(services, m["id"], "protocol")
        await send_meeting_summary(target, body)
        await target.answer("Выбери формат, скачай транскрипт или поделись 👇",
                            reply_markup=meeting_kb(m["id"]))

    async def run_menu_action(target, action: str):
        """Единая точка для кнопок панели И старого инлайн-меню — одно действие
        в одном месте (никаких дублей логики)."""
        if action == "briefing":
            await do_briefing(target)
        elif action == "status":
            await do_status(target)
        elif action == "meds":
            await do_meds(target)
        elif action == "reminders":
            await do_reminders(target)
        elif action == "calendar":
            await do_calendar(target)
        elif action == "contacts":
            await do_contacts(target)
        elif action == "health":
            await do_health(target)
            await target.answer("💊 Таблетки и 🩺 визиты — кнопками ниже. "
                                "🧪 А ещё пришли фото/PDF анализов — разберу.",
                                reply_markup=health_hub_kb())
        elif action == "visits":
            from agents import health
            await rich(target, await health.visits_text(services))
        elif action == "digest":
            await do_digest(target)
        elif action == "now":
            await do_now(target)
        elif action == "day":
            from agents import esoteric
            await show_typing(target)
            await target.answer("🔮 Считаю качество дня…")
            await rich(target, await esoteric.day_quality(services), reply_markup=esoteric_kb())
        elif action == "meeting":
            await do_meeting(target)
        elif action == "help":
            await target.answer(HELP, reply_markup=main_reply_kb())
        elif action == "state":
            pending[target.chat.id] = {}
            await ask_state(target, "energy")

    async def _send_transcript_file(target, meeting: dict):
        from aiogram.types import BufferedInputFile
        data = (meeting.get("transcript") or "").encode("utf-8")
        name = re.sub(r'[\\/:*?"<>|]+', " ", meeting.get("title") or "Транскрипт")[:50].strip()
        await target.answer_document(BufferedInputFile(data, filename=f"{name or 'Транскрипт'}.txt"))

    async def handle_meeting(m: Message, file_id: str, file_size, src_name, suffix):
        """Запись встречи → распознавание → сводка + кнопки. Общий путь для
        голосовых-длинных / аудио / видео / документов-аудио."""
        from agents import communication
        from bot.upload import download_to_tempfile
        if file_size and file_size > MEETING_MAX_BYTES:
            await m.answer("📦 Запись больше 20 МБ — столько Telegram пока не отдаёт боту. "
                           "Пришли покороче (примерно до 40 минут). Длинные записи включим позже.")
            return
        if m.chat.id in meeting_busy:
            await m.answer("⏳ Секунду — ещё разбираю предыдущую запись.")
            return
        meeting_busy.add(m.chat.id)
        status = await m.answer("🎧 Принял запись встречи. Распознаю речь — это займёт минуту…")
        path = None
        try:
            await show_typing(m)
            path = await download_to_tempfile(services, file_id, suffix)
            if not path:
                await status.edit_text("Не смог скачать запись. Попробуй ещё раз.")
                return
            res = await communication.process_recording(services, path, src_name, m.chat.id)
            if not res.get("ok"):
                await status.edit_text("⚠️ " + res.get("error", "Не получилось разобрать запись."))
                return
            try:
                await status.delete()
            except Exception:
                pass
            await safe_send(m, f"🎙 <b>{html.escape(res['title'])}</b> — разобрал встречу.")
            if res.get("summary"):
                await send_meeting_summary(m, res["summary"])
            else:
                await safe_send(m, "Сводка не вышла сразу — нажми «Протокол» ниже.")
            await m.answer(
                "Готово 👇 Можно выбрать другой формат, перенести дела в напоминания, "
                "скачать транскрипт, поделиться или задать вопрос по встрече.",
                reply_markup=meeting_kb(res["meeting_id"]))
        except Exception:
            log.exception("handle_meeting")
            try:
                await status.edit_text("⚠️ Не получилось разобрать запись. Попробуй ещё раз.")
            except Exception:
                pass
        finally:
            meeting_busy.discard(m.chat.id)
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass

    # ---------- команды ----------
    @router.message(CommandStart())
    async def _start(m: Message):
        await crud.upsert_user(db, m.from_user.id, m.chat.id, m.from_user.full_name)
        await m.answer(WELCOME, reply_markup=main_reply_kb())

    @router.message(Command("help"))
    async def _help(m: Message):
        await m.answer(HELP, reply_markup=main_reply_kb())

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
                await show_typing(m)
                await safe_send(m, await calendar.schedule_text(services))
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
        await safe_send(m, f"✅ Календарь подключён. Событий сегодня: {n}.\n\n"
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
        await rich(m, await health.visits_text(services))

    @router.message(Command("birth"))
    async def _birth(m: Message):
        from integrations import geocode
        from agents import esoteric
        from orchestrator.tools import parse_date, parse_time
        arg = (m.text or "").partition(" ")[2].strip()
        if not arg:
            b = await crud.get_birth(db)
            await safe_send(m, "🔮 Данные рождения: " + esoteric.birth_summary(b)
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
        await safe_send(m, "✅ Записал: " + esoteric.birth_summary(birth) + "\nПопробуй /day.")

    @router.message(Command("day"))
    async def _day(m: Message):
        from agents import esoteric
        await show_typing(m)
        await m.answer("🔮 Считаю качество дня…")
        await rich(m, await esoteric.day_quality(services), reply_markup=esoteric_kb())

    @router.message(Command("why"))
    async def _why(m: Message):
        from agents import esoteric
        await rich(m, await esoteric.facts_text(services))

    @router.callback_query(F.data == "eso:facts")
    async def _eso_facts(cb: CallbackQuery):
        from agents import esoteric
        await rich(cb.message, await esoteric.facts_text(services))
        await cb.answer()

    @router.message(Command("state"))
    async def _state(m: Message):
        pending[m.chat.id] = {}
        await ask_state(m, "energy")

    # ---------- старое инлайн-меню (fallback для прежних сообщений) ----------
    @router.callback_query(F.data.startswith("menu:"))
    async def _menu(cb: CallbackQuery):
        await run_menu_action(cb.message, cb.data.split(":", 1)[1])
        await cb.answer()

    # ---------- подменю групп (кнопки нижней панели) ----------
    @router.callback_query(F.data.startswith("grp:"))
    async def _grp_cb(cb: CallbackQuery):
        action = cb.data.split(":", 1)[1]
        await cb.answer()
        if action == "back":
            try:
                await cb.message.delete()   # свернуть подменю
            except Exception:
                pass
            return
        await run_menu_action(cb.message, action)

    # ---------- пошаговый ввод состояния ----------
    @router.callback_query(F.data.startswith("st:"))
    async def _state_cb(cb: CallbackQuery):
        parts = cb.data.split(":")
        if len(parts) != 3 or parts[1] not in STATE_ORDER:
            await cb.answer(STALE_BTN)
            return
        _, field, value = parts
        chat = cb.message.chat.id
        st = pending.setdefault(chat, {})
        if field in SCALE_FIELDS:
            if not value.isdigit():
                await cb.answer(STALE_BTN)
                return
            st[field] = int(value)
        else:
            st[field] = (value == "yes")

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
        parts = cb.data.split(":")
        if len(parts) != 4:
            await cb.answer(STALE_BTN)
            return
        _, action, mid, ts = parts
        try:
            med_id = int(mid)
            scheduled = datetime.strptime(ts, "%Y%m%d%H%M")
        except ValueError:
            await cb.answer(STALE_BTN)
            return
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
            await cb.message.edit_text(f"{html.escape(cb.message.text or '')}\n\n{note}")
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
        parts = cb.data.split(":")
        if len(parts) != 4:
            await cb.answer(STALE_BTN)
            return
        _, action, rid, ts = parts
        try:
            rem_id = int(rid)
            scheduled = datetime.strptime(ts, "%Y%m%d%H%M")
        except ValueError:
            await cb.answer(STALE_BTN)
            return
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
            await cb.message.edit_text(f"{html.escape(cb.message.text or '')}\n\n{note}")
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
        await safe_send(m, await health.ingest_file(services, data, "image/jpeg", "photo"))

    @router.message(F.document)
    async def _document(m: Message):
        from bot.upload import download_bytes
        from agents import health
        doc = m.document
        mime = (doc.mime_type or "").lower()
        name = (doc.file_name or "").lower()
        is_pdf = mime == "application/pdf" or name.endswith(".pdf")
        is_img = mime.startswith("image/") or name.endswith((".jpg", ".jpeg", ".png", ".webp"))
        is_audio = mime.startswith("audio/") or name.endswith(_AUDIO_EXT)
        is_video = mime.startswith("video/") or name.endswith(_VIDEO_EXT)
        # Анализы (фото/PDF) → Health
        if is_pdf or is_img:
            await m.answer("🧪 Разбираю анализы…")
            data = await download_bytes(services, doc.file_id)
            if not data:
                await m.answer("Не смог скачать файл. Попробуй ещё раз.")
                return
            media_type = "application/pdf" if is_pdf else (mime if mime.startswith("image/") else "image/jpeg")
            await safe_send(m, await health.ingest_file(services, data, media_type, "pdf" if is_pdf else "photo"))
            return
        # Запись встречи (аудио/видео-файл) → Communication
        if is_audio or is_video:
            suffix = os.path.splitext(name)[1] or (".mp4" if is_video else ".mp3")
            await handle_meeting(m, doc.file_id, doc.file_size, doc.file_name, suffix)
            return
        await m.answer("Пришли фото/PDF анализов — разберу; или запись встречи "
                       "(аудио/видео) — расшифрую и сделаю сводку.")

    # ---------- записи встреч: аудио / видео ----------
    @router.message(F.audio | F.video | F.video_note)
    async def _media(m: Message):
        media = m.audio or m.video or m.video_note
        src_name = getattr(media, "file_name", None)
        ext = os.path.splitext(src_name)[1] if src_name else ""
        suffix = ext or (".mp4" if (m.video or m.video_note) else ".mp3")
        await handle_meeting(m, media.file_id, getattr(media, "file_size", None), src_name, suffix)

    # ---------- голос: короткое = команда, длинное = запись встречи ----------
    @router.message(F.voice)
    async def _voice(m: Message):
        if (getattr(m.voice, "duration", 0) or 0) > VOICE_MEETING_SECONDS:
            await handle_meeting(m, m.voice.file_id, m.voice.file_size, None, ".ogg")
            return
        from bot.voice import handle_voice
        await show_typing(m)
        text = await handle_voice(services, m)
        if not text:
            await m.answer("🎙 Не разобрал голос — попробуй ещё раз или напиши текстом.")
            return
        await safe_send(m, f"🎙 Распознал: <i>{html.escape(text)}</i>")
        await show_typing(m)
        await stream_reply(m, text)

    # ---------- кнопки под разобранной встречей ----------
    @router.callback_query(F.data.startswith("comm:"))
    async def _comm_cb(cb: CallbackQuery):
        from agents import communication
        parts = cb.data.split(":")
        action = parts[1] if len(parts) > 1 else ""
        try:
            if action == "fmt":
                key, mid = parts[2], int(parts[3])
            else:
                mid = int(parts[2])
        except (IndexError, ValueError):
            await cb.answer(STALE_BTN)
            return
        await cb.answer()
        if action == "fmt":
            await show_typing(cb.message)
            body = await communication.format_meeting(services, mid, key)
            label = communication.FORMATS.get(key, ("📋 Заметка", ""))[0]
            await send_meeting_note(cb.message, label, body)
        elif action == "tasks":
            await show_typing(cb.message)
            items = await communication.extract_action_items(services, mid)
            if not items:
                await cb.message.answer("Не нашёл конкретных задач в этой встрече.")
                return
            created = timed = 0
            for it in items:
                due = None
                raw = it.get("datetime")
                if raw:
                    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S"):
                        try:
                            due = datetime.strptime(raw, fmt)
                            break
                        except ValueError:
                            pass
                await crud.add_reminder(db, title=it["title"], due_at=due)
                created += 1
                timed += 1 if due else 0
            msg = f"📌 Добавил в напоминания: {created}."
            if timed:
                msg += f" Со сроком (придут вовремя): {timed}."
            if created - timed:
                msg += f" Без срока: {created - timed} — лежат в /reminders, поставь время при желании."
            await cb.message.answer(msg)
        elif action == "tr":
            meeting = await crud.get_meeting(db, mid)
            if not meeting:
                await cb.message.answer("Встреча не найдена.")
                return
            await _send_transcript_file(cb.message, meeting)
        elif action == "share":
            await show_typing(cb.message)
            recap = await communication.share_recap(services, mid)
            await cb.message.answer("📤 Готово к пересылке участникам — перешли заметку ниже 👇")
            await send_meeting_note(cb.message, "📤 Итоги встречи", recap)
        elif action == "nego":
            await show_typing(cb.message)
            res = await communication.analyze_negotiation(services, mid)
            if not res.get("ok"):
                await cb.message.answer(res.get("text", "Не получилось разобрать."))
                return
            if res.get("risk") == "high":
                await cb.message.answer("⚠️ <b>Высокий риск по этим переговорам.</b> Детали ниже 👇")
            await send_meeting_note(cb.message, "🕵️ Разбор переговоров", res["text"])

    @router.message(Command("meeting"))
    async def _meeting(m: Message):
        await do_meeting(m)

    @router.message(F.text)
    async def _text(m: Message):
        txt = (m.text or "").strip()
        # Нажал кнопку-ГРУППУ нижней панели → открываем её подменю прямо в чате.
        gkey = GROUP_BY_LABEL.get(txt)
        if gkey:
            label, _ = GROUPS[gkey]
            await m.answer(f"{label} — выбери:", reply_markup=group_kb(gkey))
            return
        # Прямая кнопка панели (📋 Задачи) → действие сразу, без подменю.
        direct = DIRECT_ACTIONS.get(txt)
        if direct:
            await run_menu_action(m, direct)
            return
        # Fallback: прежние прямые кнопки (если у кого-то осталась старая панель).
        action = MAIN_BUTTON_ACTIONS.get(txt)
        if action:
            await run_menu_action(m, action)
            return
        await show_typing(m)
        await stream_reply(m, m.text)

    return router
