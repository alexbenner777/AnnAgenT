"""APScheduler: утренний промпт 07:00 → нъюдж +5/+10 мин → авто-бриф +15 мин,
вечерний дайджест 22:00, тик напоминаний о препаратах раз в минуту.
Таймзона — pytz (требование APScheduler 3.x)."""
import json
import logging
import os
from datetime import datetime

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from database import crud

log = logging.getLogger("los.scheduler")


def _miniapp_url(path: str = "") -> str | None:
    """Возвращает публичный URL мини-аппа на Replit или None."""
    domain = os.getenv("REPLIT_DEV_DOMAIN", "").strip()
    if domain:
        return f"https://{domain}{path}"
    return None


async def get_target_chats(services) -> list:
    # 🔒 Только владелец(ы). Раньше слалось во ВСЕ сохранённые чаты — посторонний,
    # нажавший /start, начинал получать личные напоминания. Теперь — никогда.
    return list(services.config.owner_ids)


async def morning_briefing(services):
    """07:00 МСК — приглашение заполнить утренний бриф через мини-апп."""
    from bot.keyboards import morning_prompt_kb
    url = _miniapp_url("/briefing-form")
    text = (
        "☀️ <b>Доброе утро!</b>\n\n"
        "Давай заполним утренний бриф — 3 тапа и готово.\n"
        "Данные помогут подобрать оптимальное расписание и рекомендации на день."
    )
    kb = morning_prompt_kb(url)
    for chat in await get_target_chats(services):
        try:
            await services.bot.send_message(chat, text, parse_mode="HTML", reply_markup=kb)
        except Exception as e:
            log.error("morning_prompt → %s: %s", chat, e)


async def state_nudge(services, stage: int):
    """Пинг на заполнение брифа (ТЗ §4.1): +5 мин после промпта, затем ещё +5.
    Если состояние за сегодня уже введено — молчим."""
    from bot.keyboards import morning_prompt_kb
    now = datetime.now(services.config.tz)
    dh = await crud.get_daily_health(services.db, now.date()) or {}
    if dh.get("energy_subjective") is not None:
        return
    url = _miniapp_url("/briefing-form")
    if stage == 1:
        text = "📝 Ещё не заполнен утренний бриф. Займёт меньше минуты — данные помогут Ане выстроить день."
    else:
        text = ("📝 Последнее напоминание: бриф не заполнен.\n"
                "Если не заполнишь — сформирую по данным Oura и истории автоматически.")
    kb = morning_prompt_kb(url)
    for chat in await get_target_chats(services):
        try:
            await services.bot.send_message(chat, text, reply_markup=kb)
        except Exception as e:
            log.error("state_nudge → %s: %s", chat, e)


async def auto_brief_if_needed(services):
    """+15 мин после промпта: если бриф не заполнен — генерируем по данным Oura/истории
    и сохраняем в БД, чтобы мини-апп тоже показал."""
    from agents import decision_support
    from bot import richmsg
    from bot.keyboards import briefing_kb

    now = datetime.now(services.config.tz)
    dh = await crud.get_daily_health(services.db, now.date()) or {}
    if dh.get("energy_subjective") is not None:
        log.info("auto_brief: состояние заполнено, авто-генерация не нужна")
        return

    log.info("auto_brief: состояние не заполнено — генерируем по данным Oura/истории")
    text = await decision_support.run(services, mode="morning")

    # Сохраняем в DB (los_miniapp.db через services.db)
    today = now.date().isoformat()
    content_json = json.dumps({"raw_text": text, "source": "auto"}, ensure_ascii=False)
    try:
        await services.db.execute(
            "INSERT OR REPLACE INTO briefings (briefing_type, content, briefing_date) VALUES (?,?,?)",
            "morning", content_json, today)
    except Exception as e:
        log.warning("auto_brief: не удалось сохранить в briefings: %s", e)

    url = _miniapp_url("/briefing-form")
    for chat in await get_target_chats(services):
        try:
            await richmsg.send_rich_or_plain(
                services.bot, services.config.telegram_bot_token,
                chat, text, reply_markup=briefing_kb(url))
        except Exception as e:
            log.error("auto_brief → %s: %s", chat, e)


async def evening_digest(services):
    from agents import decision_support
    from bot import richmsg
    text = await decision_support.run(services, mode="evening")

    # Сохраняем вечерний дайджест в БД
    now = datetime.now(services.config.tz)
    today = now.date().isoformat()
    content_json = json.dumps({"raw_text": text, "source": "auto"}, ensure_ascii=False)
    try:
        await services.db.execute(
            "INSERT OR REPLACE INTO briefings (briefing_type, content, briefing_date) VALUES (?,?,?)",
            "evening", content_json, today)
    except Exception as e:
        log.warning("evening_digest: не удалось сохранить: %s", e)

    for chat in await get_target_chats(services):
        try:
            await richmsg.send_rich_or_plain(services.bot, services.config.telegram_bot_token, chat, text)
        except Exception as e:
            log.error("evening → %s: %s", chat, e)


async def medication_tick(services):
    """Раз в минуту: кому пора принять препарат — шлём напоминание с кнопками."""
    from agents import medication
    from bot.keyboards import med_action_kb

    now = datetime.now(services.config.tz).replace(tzinfo=None)
    due = await medication.compute_due(services, now)
    if not due:
        return
    chats = await get_target_chats(services)
    if not chats:
        return
    for med, scheduled in due:
        await crud.record_reminder(services.db, med["id"], scheduled)
        text = medication.reminder_text(med, scheduled)
        kb = med_action_kb(med["id"], scheduled)
        for chat in chats:
            try:
                await services.bot.send_message(chat, text, reply_markup=kb)
            except Exception as e:
                log.error("med → %s: %s", chat, e)


async def send_single_reminder(services, chat_id, med, scheduled):
    """Разовое напоминание о препарате (для «Отложить»)."""
    from agents import medication
    from bot.keyboards import med_action_kb
    await crud.record_reminder(services.db, med["id"], scheduled)
    try:
        await services.bot.send_message(
            chat_id, medication.reminder_text(med, scheduled),
            reply_markup=med_action_kb(med["id"], scheduled))
    except Exception as e:
        log.error("snooze → %s: %s", chat_id, e)


async def reminder_tick(services):
    """Раз в минуту: общие напоминания (разовые и повторяющиеся)."""
    from agents import reminders
    from bot.keyboards import reminder_action_kb

    now = datetime.now(services.config.tz).replace(tzinfo=None)
    due = await reminders.compute_due(services, now)
    if not due:
        return
    chats = await get_target_chats(services)
    if not chats:
        return
    for rem, scheduled in due:
        await crud.record_reminder_fire(services.db, rem["id"], scheduled)
        text = reminders.reminder_text(rem, scheduled)
        kb = reminder_action_kb(rem["id"], scheduled)
        for chat in chats:
            try:
                await services.bot.send_message(chat, text, reply_markup=kb)
            except Exception as e:
                log.error("reminder → %s: %s", chat, e)


async def send_single_reminder_rem(services, chat_id, rem, scheduled):
    """Разовая переотправка общего напоминания (для «Отложить»)."""
    from agents import reminders
    from bot.keyboards import reminder_action_kb
    await crud.record_reminder_fire(services.db, rem["id"], scheduled)
    try:
        await services.bot.send_message(
            chat_id, reminders.reminder_text(rem, scheduled),
            reply_markup=reminder_action_kb(rem["id"], scheduled))
    except Exception as e:
        log.error("rem snooze → %s: %s", chat_id, e)


async def nightly_reflection(services):
    """Ночью перечитываем день и сами складываем стойкие факты в память."""
    from memory import reflection
    try:
        n = await reflection.reflect(services)
        if n:
            log.info("Ночная рефлексия: +%d фактов", n)
    except Exception as e:
        log.error("nightly_reflection: %s", e)


async def daily_relationships(services):
    """Утром: дни рождения (сегодня/+2/+7) и кто давно без касания."""
    from agents import network
    blocks = [b for b in (await network.upcoming_text(services),
                          await network.cooling_text(services)) if b]
    if not blocks:
        return
    text = "🤝 ЛЮДИ:\n" + "\n".join(blocks)
    for chat in await get_target_chats(services):
        try:
            await services.bot.send_message(chat, text)
        except Exception as e:
            log.error("relationships → %s: %s", chat, e)


def setup_scheduler(services) -> AsyncIOScheduler:
    cfg = services.config
    tz = pytz.timezone(cfg.timezone_name)
    sch = AsyncIOScheduler(timezone=tz)

    h, m = map(int, cfg.morning_briefing_time.split(":"))
    # 07:00 — утренний промпт с кнопкой открыть мини-апп
    sch.add_job(morning_briefing, CronTrigger(hour=h, minute=m), args=[services], id="morning")
    base = h * 60 + m
    # +5 мин — первый пинг
    for plus, stage in ((5, 1), (10, 2)):
        t = base + plus
        sch.add_job(state_nudge, CronTrigger(hour=(t // 60) % 24, minute=t % 60),
                    args=[services, stage], id=f"state_nudge{stage}")
    # +15 мин — авто-бриф если не заполнено
    t15 = base + 15
    sch.add_job(auto_brief_if_needed, CronTrigger(hour=(t15 // 60) % 24, minute=t15 % 60),
                args=[services], id="auto_brief")

    eh, em = map(int, cfg.evening_digest_time.split(":"))
    sch.add_job(evening_digest, CronTrigger(hour=eh, minute=em), args=[services], id="evening")
    sch.add_job(medication_tick, IntervalTrigger(minutes=1), args=[services], id="med_tick")
    sch.add_job(reminder_tick, IntervalTrigger(minutes=1), args=[services], id="reminder_tick")
    sch.add_job(nightly_reflection, CronTrigger(hour=3, minute=30), args=[services], id="reflection")
    sch.add_job(daily_relationships, CronTrigger(hour=9, minute=0), args=[services], id="relationships")
    return sch
