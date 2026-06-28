"""CRUD на SQLite. Всё сохраняется в файл и переживает перезапуск.

Соглашения:
- списки (времена приёма, дни недели) — JSON-текст в БД, объекты в Python;
- даты — 'YYYY-MM-DD'; время приёма (scheduled_at) — наивный datetime → 'YYYY-MM-DD HH:MM:SS';
- булевы — int 0/1.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, date as date_cls, time as time_cls

log = logging.getLogger("los.crud")

_DT_FMT = "%Y-%m-%d %H:%M:%S"


# ---------- сериализация ----------
def _parse_hhmm(s):
    if isinstance(s, time_cls):
        return s
    h, m = str(s).split(":")
    return time_cls(int(h), int(m))


def _times_to_json(times):
    return json.dumps([(_parse_hhmm(t)).strftime("%H:%M") for t in (times or [])])


def _times_from_json(s):
    return [_parse_hhmm(x) for x in json.loads(s or "[]")]


def _days_to_json(days):
    return json.dumps(list(days)) if days else None


def _days_from_json(s):
    return json.loads(s) if s else None


def _b(v):
    return None if v is None else int(bool(v))


def _dt(scheduled: datetime) -> str:
    return scheduled.strftime(_DT_FMT)


# ---------- пользователи ----------
async def upsert_user(db, telegram_user_id: int, chat_id: int, name: str = None):
    await db.execute(
        """INSERT INTO user_profile(telegram_user_id, chat_id, name) VALUES(?,?,?)
           ON CONFLICT(telegram_user_id) DO UPDATE SET
             chat_id=excluded.chat_id,
             name=COALESCE(excluded.name, user_profile.name)""",
        telegram_user_id, chat_id, name)


async def get_all_chat_ids(db) -> list:
    rows = await db.fetchall("SELECT DISTINCT chat_id FROM user_profile WHERE chat_id IS NOT NULL")
    return [r["chat_id"] for r in rows]


# ---------- ежедневное состояние ----------
_DH_COLS = [
    "readiness_score", "hrv_avg", "sleep_score", "sleep_hours", "heart_rate_avg",
    "energy_subjective", "focus_subjective", "mood_subjective",
    "workout_done", "massage_done", "alcohol",
]
_DH_BOOL = {"workout_done", "massage_done", "alcohol"}


async def upsert_daily_health(db, d: date_cls, **fields) -> dict:
    fields = {k: v for k, v in fields.items() if k in _DH_COLS and v is not None}
    if not fields:
        await db.execute("INSERT OR IGNORE INTO daily_health(date) VALUES(?)", d.isoformat())
        return await get_daily_health(db, d)
    cols = list(fields.keys())
    vals = [(_b(fields[c]) if c in _DH_BOOL else fields[c]) for c in cols]
    insert_cols = ["date"] + cols
    placeholders = ", ".join("?" for _ in insert_cols)
    updates = ", ".join(f"{c}=excluded.{c}" for c in cols)
    q = (f"INSERT INTO daily_health({', '.join(insert_cols)}) VALUES({placeholders}) "
         f"ON CONFLICT(date) DO UPDATE SET {updates}")
    await db.execute(q, d.isoformat(), *vals)
    return await get_daily_health(db, d)


async def get_daily_health(db, d: date_cls):
    row = await db.fetchone("SELECT * FROM daily_health WHERE date=?", d.isoformat())
    return dict(row) if row else None


async def get_recent_health(db, days: int = 7) -> list:
    rows = await db.fetchall("SELECT * FROM daily_health ORDER BY date DESC LIMIT ?", days)
    return [dict(r) for r in rows]


# ---------- препараты ----------
def _med_row(row) -> dict:
    m = dict(row)
    m["schedule_times"] = _times_from_json(m.get("schedule_times"))
    m["days_of_week"] = _days_from_json(m.get("days_of_week"))
    m["is_critical"] = bool(m.get("is_critical"))
    return m


async def add_medication(db, name, dosage=None, schedule_times=None, days_of_week=None,
                         with_food=None, is_critical=False, supply_units=None, end_date=None) -> dict:
    mid = await db.execute(
        """INSERT INTO medications(name, dosage, schedule_times, days_of_week, with_food,
                                   is_critical, supply_units, end_date, is_active)
           VALUES(?,?,?,?,?,?,?,?,1)""",
        name, dosage, _times_to_json(schedule_times), _days_to_json(days_of_week),
        with_food, _b(is_critical), supply_units,
        end_date.isoformat() if hasattr(end_date, "isoformat") else end_date)
    row = await db.fetchone("SELECT * FROM medications WHERE id=?", mid)
    return _med_row(row)


async def list_active_medications(db) -> list:
    today = datetime.now().date().isoformat()
    rows = await db.fetchall(
        """SELECT * FROM medications
           WHERE is_active=1 AND (end_date IS NULL OR end_date >= ?)
           ORDER BY id""", today)
    return [_med_row(r) for r in rows]


async def get_today_intakes(db, day: date_cls) -> list:
    rows = await db.fetchall(
        """SELECT medication_id, scheduled_at, status, reminders_sent
           FROM medication_intake_log WHERE substr(scheduled_at,1,10)=?""", day.isoformat())
    out = []
    for r in rows:
        d = dict(r)
        d["scheduled_at"] = datetime.strptime(d["scheduled_at"], _DT_FMT)
        out.append(d)
    return out


async def record_reminder(db, med_id: int, scheduled_at: datetime) -> int:
    await db.execute(
        """INSERT INTO medication_intake_log(medication_id, scheduled_at, status, reminders_sent)
           VALUES(?,?,'pending',1)
           ON CONFLICT(medication_id, scheduled_at)
           DO UPDATE SET reminders_sent = reminders_sent + 1""",
        med_id, _dt(scheduled_at))
    row = await db.fetchone(
        "SELECT reminders_sent FROM medication_intake_log WHERE medication_id=? AND scheduled_at=?",
        med_id, _dt(scheduled_at))
    return row["reminders_sent"] if row else 1


async def set_intake_status(db, med_id: int, scheduled_at: datetime, status: str):
    await db.execute(
        """INSERT INTO medication_intake_log(medication_id, scheduled_at, status, confirmed_at)
           VALUES(?,?,?,datetime('now'))
           ON CONFLICT(medication_id, scheduled_at)
           DO UPDATE SET status=excluded.status, confirmed_at=datetime('now')""",
        med_id, _dt(scheduled_at), status)


# ---------- общие напоминания ----------
def _rem_row(row) -> dict:
    r = dict(row)
    r["schedule_times"] = _times_from_json(r.get("schedule_times")) if r.get("schedule_times") else []
    r["days_of_week"] = _days_from_json(r.get("days_of_week"))
    r["due_at"] = datetime.strptime(r["due_at"], _DT_FMT) if r.get("due_at") else None
    return r


async def add_reminder(db, title, due_at=None, schedule_times=None, days_of_week=None, notes=None) -> dict:
    due_s = _dt(due_at) if isinstance(due_at, datetime) else due_at
    rid = await db.execute(
        """INSERT INTO reminders(title, notes, due_at, schedule_times, days_of_week, is_active)
           VALUES(?,?,?,?,?,1)""",
        title, notes, due_s,
        _times_to_json(schedule_times) if schedule_times else None,
        _days_to_json(days_of_week))
    row = await db.fetchone("SELECT * FROM reminders WHERE id=?", rid)
    return _rem_row(row)


async def list_active_reminders(db) -> list:
    rows = await db.fetchall("SELECT * FROM reminders WHERE is_active=1 ORDER BY id")
    return [_rem_row(r) for r in rows]


async def get_reminder(db, reminder_id: int):
    row = await db.fetchone("SELECT * FROM reminders WHERE id=?", reminder_id)
    return _rem_row(row) if row else None


async def deactivate_reminder(db, reminder_id: int):
    await db.execute("UPDATE reminders SET is_active=0 WHERE id=?", reminder_id)


async def get_reminder_log_map(db, cutoff_iso: str) -> dict:
    rows = await db.fetchall(
        """SELECT reminder_id, scheduled_at, status, reminders_sent
           FROM reminder_log WHERE scheduled_at >= ?""", cutoff_iso)
    m = {}
    for r in rows:
        m[(r["reminder_id"], datetime.strptime(r["scheduled_at"], _DT_FMT))] = dict(r)
    return m


async def record_reminder_fire(db, reminder_id: int, scheduled_at: datetime) -> int:
    await db.execute(
        """INSERT INTO reminder_log(reminder_id, scheduled_at, status, reminders_sent)
           VALUES(?,?,'pending',1)
           ON CONFLICT(reminder_id, scheduled_at)
           DO UPDATE SET reminders_sent = reminders_sent + 1""",
        reminder_id, _dt(scheduled_at))
    row = await db.fetchone(
        "SELECT reminders_sent FROM reminder_log WHERE reminder_id=? AND scheduled_at=?",
        reminder_id, _dt(scheduled_at))
    return row["reminders_sent"] if row else 1


async def set_reminder_status(db, reminder_id: int, scheduled_at: datetime, status: str):
    await db.execute(
        """INSERT INTO reminder_log(reminder_id, scheduled_at, status, confirmed_at)
           VALUES(?,?,?,datetime('now'))
           ON CONFLICT(reminder_id, scheduled_at)
           DO UPDATE SET status=excluded.status, confirmed_at=datetime('now')""",
        reminder_id, _dt(scheduled_at), status)


# ---------- смысловая память (факты) ----------
import re as _re

_STOP = set((
    "и в во не на я с со что а то все она так его но да ты к у же вы за бы по только "
    "его ее мне было вот от меня нет про для мы тебя их чем кто это эта этот эти как "
    "когда где какой какая мой моя про что-то").split())


def _keywords(q):
    words = _re.findall(r"\w+", (q or "").lower())
    return [w for w in words if len(w) >= 3 and w not in _STOP][:6]


async def add_fact(db, text, category=None, source=None) -> dict:
    text = (text or "").strip()
    if not text:
        return None
    dup = await db.fetchone("SELECT * FROM facts WHERE is_active=1 AND text=?", text)
    if dup:
        return dict(dup)
    fid = await db.execute(
        "INSERT INTO facts(text, category, source) VALUES(?,?,?)", text, category, source)
    row = await db.fetchone("SELECT * FROM facts WHERE id=?", fid)
    return dict(row)


async def list_facts(db, limit: int = 50) -> list:
    rows = await db.fetchall(
        "SELECT * FROM facts WHERE is_active=1 ORDER BY updated_at DESC, id DESC LIMIT ?", limit)
    return [dict(r) for r in rows]


def _stems(query):
    # грубый стемминг под русские окончания: «Ивана»→«иван», «встречу»→«встр»
    return [k[:max(4, len(k) - 3)] for k in _keywords(query)]


async def search_facts(db, query, limit: int = 8) -> list:
    # фильтрация в Python: SQLite LIKE/lower() не понимают кириллицу (только ASCII)
    items = await list_facts(db, 500)
    stems = _stems(query)
    if not stems:
        return items[:limit]
    out = [f for f in items if any(st in (f["text"] or "").lower() for st in stems)]
    return out[:limit]


async def recall_for_context(db, query, limit: int = 8) -> list:
    """Тексты релевантных фактов для подмешивания в системный промпт."""
    texts = [f["text"] for f in await search_facts(db, query, limit)]
    if len(texts) < limit:
        for f in await list_facts(db, limit):
            if f["text"] not in texts:
                texts.append(f["text"])
            if len(texts) >= limit:
                break
    return texts[:limit]


async def deactivate_fact(db, fact_id: int):
    await db.execute("UPDATE facts SET is_active=0 WHERE id=?", fact_id)


# ---------- настройки (key/value) ----------
async def get_setting(db, key: str):
    row = await db.fetchone("SELECT value FROM settings WHERE key=?", key)
    return row["value"] if row and row["value"] else None


async def set_setting(db, key: str, value: str):
    await db.execute(
        """INSERT INTO settings(key, value) VALUES(?,?)
           ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=datetime('now')""",
        key, value)


async def set_birth(db, birth: dict):
    await set_setting(db, "birth", json.dumps(birth, ensure_ascii=False))
    await set_setting(db, "eso_day", "")          # сбросить дневной кэш эзотерики


async def get_birth(db):
    raw = await get_setting(db, "birth")
    return json.loads(raw) if raw else None


# ---------- контакты (Network) ----------
def _bday_md(s):
    if not s:
        return None
    s = str(s).strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d.%m", "%m-%d", "%d/%m/%Y", "%d/%m"):
        try:
            return datetime.strptime(s, fmt).strftime("%m-%d")
        except ValueError:
            pass
    return None


async def add_contact(db, name, relation=None, circle=None, birthday=None, interests=None,
                      touch_days=None, language=None, notes=None) -> dict:
    cid = await db.execute(
        """INSERT INTO contacts(name, relation, circle, birthday, bday_md, interests,
                                touch_days, language, notes, is_active)
           VALUES(?,?,?,?,?,?,?,?,?,1)""",
        name, relation, circle, birthday, _bday_md(birthday), interests,
        touch_days, language, notes)
    row = await db.fetchone("SELECT * FROM contacts WHERE id=?", cid)
    return dict(row)


async def list_contacts(db, limit: int = 100) -> list:
    rows = await db.fetchall(
        "SELECT * FROM contacts WHERE is_active=1 ORDER BY name LIMIT ?", limit)
    return [dict(r) for r in rows]


async def find_contacts(db, query, limit: int = 5) -> list:
    # фильтрация в Python: SQLite LIKE/lower() не понимают кириллицу (только ASCII)
    items = await list_contacts(db, 500)
    stems = _stems(query)
    if not stems:
        return items[:limit]
    out = [c for c in items if any(st in (c["name"] or "").lower() for st in stems)]
    return out[:limit]


async def get_contact_by_name(db, name):
    found = await find_contacts(db, name, 1)
    return found[0] if found else None


async def set_last_contact(db, contact_id: int, date_iso: str):
    await db.execute("UPDATE contacts SET last_contact=? WHERE id=?", date_iso, contact_id)


async def birthdays_on(db, md_list) -> list:
    if not md_list:
        return []
    qs = ",".join("?" for _ in md_list)
    rows = await db.fetchall(
        f"SELECT * FROM contacts WHERE is_active=1 AND bday_md IN ({qs})", *md_list)
    return [dict(r) for r in rows]


async def add_greeting(db, contact_id: int, occasion: str, text: str):
    await db.execute(
        "INSERT INTO greeting_history(contact_id, occasion, text) VALUES(?,?,?)",
        contact_id, occasion, text)


async def past_greetings(db, contact_id: int, limit: int = 5) -> list:
    rows = await db.fetchall(
        "SELECT text FROM greeting_history WHERE contact_id=? ORDER BY id DESC LIMIT ?",
        contact_id, limit)
    return [r["text"] for r in rows]


# ---------- ❤️ Health: анализы ----------
def norm_marker_key(s) -> str:
    """Нормализуем имя показателя для матчинга трендов между загрузками:
    нижний регистр, только буквы/цифры (рус+лат). «Витамин D, 25-OH» → 'витаминd25oh'."""
    return _re.sub(r"[^0-9a-zа-яё]+", "", (s or "").lower())


def _flag(value, low, high):
    if value is None:
        return None
    if low is not None and value < low:
        return "low"
    if high is not None and value > high:
        return "high"
    if low is not None or high is not None:
        return "normal"
    return None


async def add_lab_panel(db, taken_on=None, lab_name=None, source=None, notes=None) -> int:
    return await db.execute(
        "INSERT INTO lab_panels(taken_on, lab_name, source, notes) VALUES(?,?,?,?)",
        taken_on, lab_name, source, notes)


async def add_lab_result(db, panel_id, taken_on, marker, value=None, value_text=None,
                         unit=None, ref_low=None, ref_high=None) -> dict:
    flag = _flag(value, ref_low, ref_high)
    rid = await db.execute(
        """INSERT INTO lab_results(panel_id, taken_on, marker, marker_key, value, value_text,
                                   unit, ref_low, ref_high, flag)
           VALUES(?,?,?,?,?,?,?,?,?,?)""",
        panel_id, taken_on, marker, norm_marker_key(marker), value, value_text,
        unit, ref_low, ref_high, flag)
    row = await db.fetchone("SELECT * FROM lab_results WHERE id=?", rid)
    return dict(row)


async def latest_lab_results(db, limit: int = 40) -> list:
    """Последнее значение по каждому показателю (по дате сдачи, затем по id)."""
    rows = await db.fetchall(
        """SELECT r.* FROM lab_results r
           JOIN (SELECT marker_key, MAX(COALESCE(taken_on,'') || printf('%012d', id)) AS mx
                 FROM lab_results GROUP BY marker_key) m
             ON r.marker_key = m.marker_key
            AND (COALESCE(r.taken_on,'') || printf('%012d', r.id)) = m.mx
           ORDER BY (r.flag IN ('low','high')) DESC, r.marker LIMIT ?""", limit)
    return [dict(r) for r in rows]


async def marker_series(db, marker_key: str, limit: int = 12) -> list:
    """Хронология одного показателя (старые → новые) для тренда."""
    rows = await db.fetchall(
        """SELECT * FROM lab_results WHERE marker_key=?
           ORDER BY COALESCE(taken_on,'') ASC, id ASC LIMIT ?""", marker_key, limit)
    return [dict(r) for r in rows]


async def find_markers(db, query, limit: int = 5) -> list:
    """Подобрать показатели по запросу (фильтрация в Python — кириллица)."""
    rows = await db.fetchall("SELECT DISTINCT marker, marker_key FROM lab_results")
    items = [dict(r) for r in rows]
    stems = _stems(query)
    qkey = norm_marker_key(query)
    if qkey:
        exact = [c for c in items if qkey in (c["marker_key"] or "")]
        if exact:
            return exact[:limit]
    if not stems:
        return items[:limit]
    out = [c for c in items if any(st in (c["marker"] or "").lower() for st in stems)]
    return out[:limit]


# ---------- ❤️ Health: визиты к врачам ----------
async def add_visit(db, visit_date=None, doctor=None, specialty=None, reason=None,
                    followup_date=None) -> dict:
    vid = await db.execute(
        """INSERT INTO medical_visits(visit_date, doctor, specialty, reason, followup_date, status)
           VALUES(?,?,?,?,?,'planned')""",
        visit_date, doctor, specialty, reason, followup_date)
    row = await db.fetchone("SELECT * FROM medical_visits WHERE id=?", vid)
    return dict(row)


async def list_visits(db, upcoming_only: bool = False, limit: int = 30) -> list:
    if upcoming_only:
        today = datetime.now().date().isoformat()
        rows = await db.fetchall(
            """SELECT * FROM medical_visits
               WHERE status='planned' AND (visit_date IS NULL OR visit_date >= ?)
               ORDER BY COALESCE(visit_date,'9999') ASC LIMIT ?""", today, limit)
    else:
        rows = await db.fetchall(
            """SELECT * FROM medical_visits
               ORDER BY (status='planned') DESC, COALESCE(visit_date,'') DESC LIMIT ?""", limit)
    return [dict(r) for r in rows]


async def get_visit(db, visit_id: int):
    row = await db.fetchone("SELECT * FROM medical_visits WHERE id=?", visit_id)
    return dict(row) if row else None


async def update_visit(db, visit_id: int, **fields):
    cols = [c for c in ("visit_date", "doctor", "specialty", "reason", "outcome",
                        "followup_date", "status") if fields.get(c) is not None]
    if not cols:
        return
    sets = ", ".join(f"{c}=?" for c in cols)
    await db.execute(f"UPDATE medical_visits SET {sets} WHERE id=?",
                     *[fields[c] for c in cols], visit_id)
