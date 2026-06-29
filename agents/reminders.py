"""⏰ Reminders — общие напоминания о чём угодно (не только таблетки).
Тот же надёжный движок: разовые (due_at) и повторяющиеся (times + дни недели),
fire-once через reminder_log, догон после рестарта, подтверждение кнопками."""
from __future__ import annotations

from datetime import datetime, timedelta

from database import crud

_WD = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]


def reminder_text(rem: dict, scheduled: datetime) -> str:
    s = f"⏰ НАПОМИНАНИЕ: {rem['title']}"
    if rem.get("notes"):
        s += f"\n{rem['notes']}"
    return s


async def list_text(services) -> str:
    rems = await crud.list_active_reminders(services.db)
    if not rems:
        return "⏰ Активных напоминаний нет."
    lines = []
    for r in rems:
        if r["due_at"]:
            when = r["due_at"].strftime("%d.%m %H:%M")
        elif r["schedule_times"]:
            times = ", ".join(t.strftime("%H:%M") for t in r["schedule_times"])
            days = ", ".join(_WD[d] for d in r["days_of_week"]) if r["days_of_week"] else "каждый день"
            when = f"{days} в {times}"
        else:
            when = "—"
        lines.append(f"#{r['id']} {r['title']} — {when}")
    return "## ⏰ Напоминания\n" + "\n".join(lines)


async def compute_due(services, now: datetime) -> list:
    """(rem, scheduled_naive) которым пора напомнить. now — наивный локальный datetime."""
    cfg = services.config
    repeat = cfg.medication_repeat_minutes
    maxr = cfg.medication_max_reminders
    today = now.date()

    rems = await crud.list_active_reminders(services.db)
    if not rems:
        return []
    cutoff = (now - timedelta(days=8)).strftime("%Y-%m-%d %H:%M:%S")
    logmap = await crud.get_reminder_log_map(services.db, cutoff)

    due = []
    for r in rems:
        if r["due_at"]:
            occs = [r["due_at"]]
            window = 7 * 24 * 60          # разовое: добираем до недели после простоя
        else:
            dow = r["days_of_week"]
            if dow and now.weekday() not in dow:
                continue                   # не тот день недели
            occs = [datetime.combine(today, t) for t in (r["schedule_times"] or [])]
            window = 18 * 60               # повторяющееся: тот же день

        for scheduled in occs:
            delta = (now - scheduled).total_seconds() / 60.0
            if delta < 0:
                continue
            row = logmap.get((r["id"], scheduled))
            status = row["status"] if row else "pending"
            if status in ("taken", "skipped", "snoozed"):
                continue
            sent = row["reminders_sent"] if row else 0
            if sent == 0:
                if 0 <= delta < window:
                    due.append((r, scheduled))
            elif sent < maxr and delta >= sent * repeat:
                due.append((r, scheduled))
    return due
