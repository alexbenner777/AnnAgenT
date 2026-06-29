"""🤝 Network & Relationship Agent
Контакты, дни рождения (за 7/2/0 дней), «давно не общались», личные поздравления.
Опирается на уже готовый принцип «никогда не забывать»."""
from __future__ import annotations

from datetime import datetime, timedelta

from agents.base import chat
from database import crud

_CIRCLE = {"core": "ядро", "close": "близкий", "work": "рабочий", "extended": "расширенный"}


def card(c: dict) -> str:
    parts = [f"👤 {c['name']}"]
    if c.get("relation"):
        parts.append(f"кто: {c['relation']}")
    if c.get("circle"):
        parts.append(f"круг: {_CIRCLE.get(c['circle'], c['circle'])}")
    if c.get("birthday"):
        parts.append(f"день рождения: {c['birthday']}")
    if c.get("interests"):
        parts.append(f"интересы: {c['interests']}")
    if c.get("last_contact"):
        parts.append(f"последний контакт: {c['last_contact']}")
    if c.get("notes"):
        parts.append(f"заметки: {c['notes']}")
    return "\n".join(parts)


async def list_text(services) -> str:
    cs = await crud.list_contacts(services.db)
    if not cs:
        return ("👥 Контактов пока нет. Добавь, например: "
                "«добавь контакт Иван Петров, партнёр, ДР 14.03, любит гольф».")
    lines = []
    for c in cs:
        b = f" 🎂 {c['birthday']}" if c.get("birthday") else ""
        rel = f" — {c['relation']}" if c.get("relation") else ""
        lines.append(f"• {c['name']}{rel}{b}")
    return "## 👥 Контакты\n" + "\n".join(lines)


async def write_greeting(services, contact: dict, occasion: str = "день рождения") -> str:
    past = await crud.past_greetings(services.db, contact["id"])
    system = ("Ты пишешь тёплые личные поздравления на русском. Кратко (2–4 предложения), "
              "искренне, без шаблонов и канцелярита. Не повторяй тон, образы и структуру "
              "прошлых поздравлений.")
    user = f"Кому: {contact['name']}"
    if contact.get("relation"):
        user += f" ({contact['relation']})"
    if contact.get("interests"):
        user += f"\nИнтересы: {contact['interests']}"
    user += f"\nПовод: {occasion}"
    if past:
        user += "\nПрошлые поздравления (НЕ повторяй):\n" + "\n".join(f"- {p}" for p in past)
    text = await chat(services, system, user, max_tokens=400)
    if not text:
        return "(Не удалось сгенерировать — Claude недоступен.)"
    await crud.add_greeting(services.db, contact["id"], occasion, text)
    return text


async def upcoming_text(services) -> str:
    """Дни рождения: сегодня / через 2 дня / через неделю."""
    tz = services.config.tz
    today = datetime.now(tz).date()
    out = []
    for label, delta in (("сегодня", 0), ("через 2 дня", 2), ("через неделю", 7)):
        md = (today + timedelta(days=delta)).strftime("%m-%d")
        for c in await crud.birthdays_on(services.db, [md]):
            rel = f" ({c['relation']})" if c.get("relation") else ""
            out.append(f"🎂 ДР {label}: {c['name']}{rel}")
    return "\n".join(out)


async def cooling_text(services) -> str:
    """Кого давно не касались (last_contact > 2× желаемого ритма)."""
    tz = services.config.tz
    today = datetime.now(tz).date()
    out = []
    for c in await crud.list_contacts(services.db):
        td, lc = c.get("touch_days"), c.get("last_contact")
        if not td or not lc:
            continue
        try:
            last = datetime.strptime(lc, "%Y-%m-%d").date()
        except ValueError:
            continue
        if (today - last).days > 2 * td:
            out.append(f"❄️ давно не общались: {c['name']} (последний раз {lc})")
    return "\n".join(out)
