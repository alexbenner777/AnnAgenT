"""💊 Medication Reminder Agent [MVP]
Держит график приёма препаратов, считает «что пора принять сейчас» и формирует
текст напоминания. Сам Ане не пишет — отдаёт данные планировщику/оркестратору.

Логика напоминаний (тик раз в минуту, см. scheduler/jobs.py):
- первое напоминание — когда наступило время приёма;
- если не подтверждено за repeat_minutes — повтор, до max_reminders раз;
- статусы taken/skipped — приём закрыт.
"""
from datetime import datetime

from database import crud

_COND = {"before": "натощак", "after": "после еды", "with": "с едой", "any": ""}


def _cond(with_food):
    return _COND.get((with_food or "").lower(), "")


def reminder_text(med: dict, scheduled: datetime) -> str:
    s = f"💊 ПОРА ПРИНЯТЬ: {scheduled.strftime('%H:%M')}\n• {med['name']}"
    if med.get("dosage"):
        s += f" — {med['dosage']}"
    c = _cond(med.get("with_food"))
    if c:
        s += f" — {c}"
    return s


async def schedule_text(services, header: bool = True) -> str:
    cfg = services.config
    today = datetime.now(cfg.tz).date()
    meds = await crud.list_active_medications(services.db)
    if not meds:
        return ("💊 Препараты не заданы. Добавь, например: "
                "«добавь витамин D 2000 МЕ в 09:00»." if header else "нет")

    intakes = {(i["medication_id"], i["scheduled_at"]): i
               for i in await crud.get_today_intakes(services.db, today)}
    marks = {"taken": "✅", "skipped": "⏭", "snoozed": "💤"}
    lines = []
    for m in meds:
        dow = m.get("days_of_week")
        if dow and today.weekday() not in dow:
            continue  # не сегодняшний день недели — в списке «на сегодня» не показываем
        for t in (m.get("schedule_times") or []):
            sched = datetime.combine(today, t)
            st = intakes.get((m["id"], sched))
            mark = marks.get(st["status"] if st else "", "•")
            c = _cond(m.get("with_food"))
            line = f"{mark} {t.strftime('%H:%M')} — {m['name']}"
            if m.get("dosage"):
                line += f" — {m['dosage']}"
            if c:
                line += f" ({c})"
            lines.append(line)
    body = "\n".join(sorted(lines)) if lines else "нет времён приёма"
    return f"💊 ПРЕПАРАТЫ СЕГОДНЯ:\n{body}" if header else body


async def run(services, question: str = None) -> str:
    """Точка для оркестратора: показать график на сегодня."""
    return await schedule_text(services)


async def compute_due(services, now: datetime) -> list:
    """Вернуть список (med, scheduled_naive), которым пора напомнить прямо сейчас.
    now — НАИВНЫЙ datetime в локальной таймзоне."""
    cfg = services.config
    repeat = cfg.medication_repeat_minutes
    maxr = cfg.medication_max_reminders
    today = now.date()

    meds = await crud.list_active_medications(services.db)
    if not meds:
        return []
    intakes = {(i["medication_id"], i["scheduled_at"]): i
               for i in await crud.get_today_intakes(services.db, today)}

    due = []
    for m in meds:
        dow = m.get("days_of_week")
        if dow and now.weekday() not in dow:
            continue  # сегодня не тот день недели (напр. «только по субботам»)
        for t in (m.get("schedule_times") or []):
            scheduled = datetime.combine(today, t)
            delta_min = (now - scheduled).total_seconds() / 60.0
            if delta_min < 0:
                continue  # ещё не время
            row = intakes.get((m["id"], scheduled))
            status = row["status"] if row else "pending"
            if status in ("taken", "skipped", "snoozed"):
                continue  # приём закрыт или отложен (отложенный придёт разовым job'ом)
            sent = row["reminders_sent"] if row else 0
            if sent == 0:
                # первое напоминание: добираем в течение того же дня — переживает
                # перезапуск бота (если лежал, всё равно напомнит, а не проглотит)
                if 0 <= delta_min < 18 * 60:
                    due.append((m, scheduled))
            elif sent < maxr and delta_min >= sent * repeat:
                due.append((m, scheduled))
    return due
