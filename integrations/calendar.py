"""Google Календарь через секретную iCal-ссылку (только чтение).

Удобство: подключение — одной ссылкой (.ics из настроек Google Календаря),
переключение тест→основной — просто другой ссылкой. Без Google Cloud/OAuth.
Ссылка хранится в settings (команда /calendar) или в env GOOGLE_CALENDAR_ICS_URL.
"""
from __future__ import annotations

import datetime as dt
import logging
import time as _time

import httpx

log = logging.getLogger("los.calendar")

_CACHE = {}      # url -> (monotonic_ts, day_iso, events)
_TTL = 300       # 5 минут


def normalize(url):
    if url and url.startswith("webcal://"):
        return "https://" + url[len("webcal://"):]
    return url


async def get_url(services):
    from database import crud
    url = await crud.get_setting(services.db, "gcal_ics_url")
    return normalize(url or services.config.gcal_ics_url)


def _parse_today(ics_text: str, tz) -> list:
    """Разобрать .ics и вернуть события на СЕГОДНЯ (с разворотом повторяющихся)."""
    import icalendar
    import recurring_ical_events

    cal = icalendar.Calendar.from_ical(ics_text)
    day = dt.datetime.now(tz).date()
    start = dt.datetime.combine(day, dt.time.min).replace(tzinfo=tz)
    end = dt.datetime.combine(day, dt.time.max).replace(tzinfo=tz)

    out = []
    for e in recurring_ical_events.of(cal).between(start, end):
        summary = str(e.get("SUMMARY") or "(без названия)")
        ds = e.get("DTSTART")
        d = ds.dt if ds is not None else None
        if isinstance(d, dt.datetime):
            local = d.astimezone(tz) if d.tzinfo else d.replace(tzinfo=tz)
            label, key = local.strftime("%H:%M"), local.strftime("%H%M")
        elif isinstance(d, dt.date):
            label, key = "весь день", "0000"
        else:
            label, key = "—", "9999"
        out.append({"title": summary, "time": label, "_k": key})
    out.sort(key=lambda x: x["_k"])
    return out


async def _fetch_today(url: str, tz) -> list:
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as c:
        r = await c.get(url)
        r.raise_for_status()
        text = r.text
    return _parse_today(text, tz)


async def probe(url: str, tz):
    """Проверка ссылки: число событий сегодня или None при ошибке."""
    try:
        return len(await _fetch_today(normalize(url), tz))
    except Exception as e:
        log.warning("calendar probe: %s", e)
        return None


async def events_today(services) -> list:
    url = await get_url(services)
    if not url:
        return []
    day_iso = dt.datetime.now(services.config.tz).date().isoformat()
    cached = _CACHE.get(url)
    if cached and cached[1] == day_iso and (_time.monotonic() - cached[0]) < _TTL:
        return cached[2]
    try:
        events = await _fetch_today(url, services.config.tz)
    except Exception as e:
        log.warning("calendar fetch: %s", e)
        return cached[2] if (cached and cached[1] == day_iso) else []
    _CACHE[url] = (_time.monotonic(), day_iso, events)
    return events


async def schedule_text(services) -> str:
    url = await get_url(services)
    if not url:
        return "📅 Календарь не подключён. Набери /calendar — покажу, как подключить за 30 секунд."
    events = await events_today(services)
    if not events:
        return "📅 На сегодня встреч нет."
    return "📅 СЕГОДНЯ:\n" + "\n".join(f"• {e['time']} — {e['title']}" for e in events)
