"""
LOS Mini App — FastAPI REST layer
Serves all data for the Telegram Mini App frontend.
Port: 8001
"""
import sqlite3
import json
import os
from datetime import datetime, date, timedelta
from typing import Optional, List, Any
from contextlib import asynccontextmanager

try:
    from fastapi import FastAPI, HTTPException, Query
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "fastapi", "uvicorn[standard]", "--quiet"])
    from fastapi import FastAPI, HTTPException, Query
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel

DB_PATH = os.environ.get("LOS_DB_PATH", "los_miniapp.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS user_profile (
        telegram_user_id INTEGER PRIMARY KEY,
        chat_id INTEGER,
        name TEXT,
        role TEXT DEFAULT 'viewer',
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS daily_health (
        date TEXT PRIMARY KEY,
        readiness_score INTEGER,
        hrv_avg REAL,
        sleep_score INTEGER,
        sleep_hours REAL,
        heart_rate_avg INTEGER,
        energy_subjective INTEGER,
        workout_done INTEGER DEFAULT 0,
        massage_done INTEGER DEFAULT 0,
        alcohol INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS medications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        dosage TEXT,
        schedule_times TEXT,
        days_of_week TEXT,
        with_food TEXT,
        is_critical INTEGER DEFAULT 0,
        supply_units INTEGER,
        is_active INTEGER DEFAULT 1,
        end_date TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS medication_intake_log (
        medication_id INTEGER NOT NULL,
        scheduled_at TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        reminders_sent INTEGER DEFAULT 0,
        confirmed_at TEXT,
        PRIMARY KEY (medication_id, scheduled_at)
    );

    CREATE TABLE IF NOT EXISTS calendar_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_date TEXT NOT NULL,
        title TEXT,
        start_time TEXT,
        end_time TEXT,
        meeting_type TEXT DEFAULT 'work',
        cognitive_load TEXT DEFAULT 'medium',
        location TEXT,
        description TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        amount REAL NOT NULL,
        category TEXT,
        description TEXT,
        expense_date TEXT DEFAULT (date('now')),
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS income (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        amount REAL NOT NULL,
        source TEXT,
        income_date TEXT DEFAULT (date('now')),
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS budget_limits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL,
        monthly_limit REAL NOT NULL,
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS contacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        relation TEXT,
        circle TEXT DEFAULT 'extended',
        birthday TEXT,
        bday_md TEXT,
        interests TEXT,
        language TEXT,
        notes TEXT,
        city TEXT,
        occupation TEXT,
        last_contact TEXT,
        touch_days INTEGER,
        is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS gift_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contact_id INTEGER,
        gift TEXT,
        direction TEXT DEFAULT 'given',
        occasion TEXT,
        gift_date TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS meetings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        transcript TEXT,
        summary TEXT,
        meeting_date TEXT DEFAULT (date('now')),
        participants TEXT,
        format TEXT DEFAULT 'protocol',
        risk_flag TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        notes TEXT,
        due_at TEXT,
        schedule_times TEXT,
        days_of_week TEXT,
        is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS reminder_log (
        reminder_id INTEGER NOT NULL,
        scheduled_at TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        confirmed_at TEXT,
        PRIMARY KEY (reminder_id, scheduled_at)
    );

    CREATE TABLE IF NOT EXISTS lab_panels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        taken_on TEXT,
        lab_name TEXT,
        source TEXT,
        notes TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS lab_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        panel_id INTEGER,
        taken_on TEXT,
        marker TEXT NOT NULL,
        marker_key TEXT,
        value REAL,
        value_text TEXT,
        unit TEXT,
        ref_low REAL,
        ref_high REAL,
        flag TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS medical_visits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        visit_date TEXT,
        doctor TEXT,
        specialty TEXT,
        reason TEXT,
        outcome TEXT,
        followup_date TEXT,
        schedule_pattern TEXT,
        status TEXT DEFAULT 'planned',
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT,
        updated_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS briefings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        briefing_type TEXT DEFAULT 'morning',
        content TEXT,
        briefing_date TEXT DEFAULT (date('now')),
        created_at TEXT DEFAULT (datetime('now'))
    );
    """)

    conn.commit()
    _seed_demo_data(conn)
    conn.close()

def _seed_demo_data(conn):
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM daily_health")
    if cur.fetchone()[0] > 0:
        return

    today = date.today()
    for i in range(7):
        d = (today - timedelta(days=6-i)).isoformat()
        cur.execute("""INSERT OR IGNORE INTO daily_health
            (date, readiness_score, hrv_avg, sleep_score, sleep_hours,
             heart_rate_avg, energy_subjective, workout_done, massage_done, alcohol)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (d, 70+i*2, 45+i*3, 72+i, 7.2+i*0.1, 62-i, 7+i%3-1,
             1 if i%2==0 else 0, 1 if i%3==0 else 0, 1 if i==1 else 0))

    meds = [
        ("Магний B6", "2 таб.", '["09:00","21:00"]', None, "with", 0, 60, 1, None),
        ("Омега-3", "1 капс.", '["08:00"]', None, "with", 0, 90, 1, None),
        ("Витамин D3", "1 капс.", '["09:00"]', None, "with", 0, 120, 1, None),
        ("Коэнзим Q10", "1 капс.", '["12:00"]', None, "any", 0, 45, 1, None),
    ]
    for m in meds:
        cur.execute("""INSERT OR IGNORE INTO medications
            (name, dosage, schedule_times, days_of_week, with_food, is_critical, supply_units, is_active, end_date)
            VALUES (?,?,?,?,?,?,?,?,?)""", m)

    med_ids = [row[0] for row in cur.execute("SELECT id FROM medications").fetchall()]
    for mid in med_ids:
        for h in ["09:00", "21:00"]:
            cur.execute("""INSERT OR IGNORE INTO medication_intake_log
                (medication_id, scheduled_at, status)
                VALUES (?,?,?)""",
                (mid, f"{today.isoformat()} {h}:00", "pending"))

    events = [
        (today.isoformat(), "Созвон с командой", "10:00", "11:00", "work", "medium", "Zoom", "Еженедельный синк"),
        (today.isoformat(), "Обед с партнёрами", "13:00", "14:30", "work", "low", "Ресторан Пушкин", ""),
        (today.isoformat(), "Стратегическая сессия", "16:00", "18:00", "work", "high", "Офис", "Квартальное планирование"),
        ((today + timedelta(days=1)).isoformat(), "Встреча с инвестором", "11:00", "12:00", "work", "high", "Офис", ""),
        ((today + timedelta(days=2)).isoformat(), "Йога", "08:00", "09:00", "personal", "low", "Студия", ""),
        ((today + timedelta(days=3)).isoformat(), "Дантист", "15:00", "16:00", "health", "medium", "Клиника", "Плановый осмотр"),
    ]
    for e in events:
        cur.execute("""INSERT OR IGNORE INTO calendar_events
            (event_date, title, start_time, end_time, meeting_type, cognitive_load, location, description)
            VALUES (?,?,?,?,?,?,?,?)""", e)

    expenses_data = [
        (5000, "Еда", "Садик", (today - timedelta(days=1)).isoformat()),
        (3200, "Транспорт", "Такси", (today - timedelta(days=2)).isoformat()),
        (12000, "Рестораны", "Ужин с партнёрами", (today - timedelta(days=3)).isoformat()),
        (8500, "Здоровье", "Аптека", (today - timedelta(days=4)).isoformat()),
        (45000, "Образование", "Онлайн-курс", (today - timedelta(days=5)).isoformat()),
        (2300, "Еда", "Продукты", today.isoformat()),
        (1500, "Транспорт", "Метро + автобус", today.isoformat()),
        (15000, "Развлечения", "Театр", (today - timedelta(days=6)).isoformat()),
    ]
    for exp in expenses_data:
        cur.execute("INSERT OR IGNORE INTO expenses (amount, category, description, expense_date) VALUES (?,?,?,?)", exp)

    cur.execute("INSERT OR IGNORE INTO income (amount, source, income_date) VALUES (?,?,?)",
                (500000, "Основной доход", (today.replace(day=1)).isoformat()))

    limits = [
        ("Еда", 80000), ("Транспорт", 30000), ("Рестораны", 50000),
        ("Здоровье", 40000), ("Развлечения", 30000), ("Образование", 60000),
    ]
    for lim in limits:
        cur.execute("INSERT OR IGNORE INTO budget_limits (category, monthly_limit) VALUES (?,?)", lim)

    contacts_data = [
        ("Мария Иванова", "партнёр", "core", "1985-03-15", "03-15", "кино, йога, путешествия", "ru", "Близкий человек", "Москва", "Дизайнер", "2024-06-25", 7),
        ("Алексей Смирнов", "друг", "close", "1983-07-22", "07-22", "спорт, технологии, горы", "ru", "Давний друг", "Москва", "Предприниматель", "2024-06-20", 14),
        ("Елена Козлова", "клиент", "work", "1990-09-10", "09-10", "бизнес, искусство", "ru", "Ключевой клиент", "СПб", "CEO", "2024-06-15", 30),
        ("Дмитрий Петров", "инвестор", "work", "1978-12-05", "12-05", "финансы, теннис", "ru", "Потенциальный инвестор", "Москва", "Венчурный инвестор", "2024-06-10", 21),
        ("Анна Сидорова", "семья", "core", "1988-06-30", "06-30", "семья, книги, готовка", "ru", "Сестра", "Москва", "", "2024-06-28", 3),
    ]
    for c in contacts_data:
        cur.execute("""INSERT OR IGNORE INTO contacts
            (name, relation, circle, birthday, bday_md, interests, language, notes, city, occupation, last_contact, touch_days)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""", c)

    cur.execute("""INSERT OR IGNORE INTO medical_visits
        (visit_date, doctor, specialty, reason, outcome, followup_date, schedule_pattern, status)
        VALUES (?,?,?,?,?,?,?,?)""",
        ((today + timedelta(days=5)).isoformat(), "Иванов А.В.", "Кардиолог",
         "Плановый осмотр", None, (today + timedelta(days=90)).isoformat(), None, "planned"))
    cur.execute("""INSERT OR IGNORE INTO medical_visits
        (visit_date, doctor, specialty, reason, outcome, followup_date, schedule_pattern, status)
        VALUES (?,?,?,?,?,?,?,?)""",
        ((today - timedelta(days=10)).isoformat(), "Козлова Е.П.", "Стоматолог",
         "Чистка", "Профессиональная чистка, назначен контроль через 6 мес.",
         (today + timedelta(days=170)).isoformat(), None, "done"))
    cur.execute("""INSERT OR IGNORE INTO medical_visits
        (visit_date, doctor, specialty, reason, outcome, followup_date, schedule_pattern, status)
        VALUES (?,?,?,?,?,?,?,?)""",
        (None, "Петрова М.С.", "Невролог", "Плановый осмотр", None, None, "по вт/чт в 15:00", "planned"))

    panel_id = cur.execute("""INSERT INTO lab_panels (taken_on, lab_name, source, notes)
        VALUES (?,?,?,?)""",
        ((today - timedelta(days=30)).isoformat(), "Инвитро", "pdf", "Общий анализ крови + биохимия")).lastrowid
    lab_results_data = [
        (panel_id, (today - timedelta(days=30)).isoformat(), "Витамин D 25-OH", "vitamin_d", 28.5, "28.5", "нг/мл", 30, 100, "low"),
        (panel_id, (today - timedelta(days=30)).isoformat(), "Ферритин", "ferritin", 45, "45", "нг/мл", 30, 300, "normal"),
        (panel_id, (today - timedelta(days=30)).isoformat(), "ТТГ", "tsh", 1.8, "1.8", "мкМЕ/мл", 0.4, 4.0, "normal"),
        (panel_id, (today - timedelta(days=30)).isoformat(), "Гемоглобин", "hgb", 138, "138", "г/л", 130, 170, "normal"),
        (panel_id, (today - timedelta(days=30)).isoformat(), "Общий холестерин", "cholesterol", 5.8, "5.8", "ммоль/л", 0, 5.2, "high"),
    ]
    for lr in lab_results_data:
        cur.execute("""INSERT OR IGNORE INTO lab_results
            (panel_id, taken_on, marker, marker_key, value, value_text, unit, ref_low, ref_high, flag)
            VALUES (?,?,?,?,?,?,?,?,?,?)""", lr)

    reminders_data = [
        ("Выпить воду", None, None, '["08:00","12:00","18:00"]', None),
        ("Позвонить юристу", "По поводу договора", f"{(today + timedelta(days=1)).isoformat()} 09:00:00", None, None),
        ("Витамины", None, None, '["09:00"]', None),
    ]
    for r in reminders_data:
        cur.execute("""INSERT OR IGNORE INTO reminders
            (title, notes, due_at, schedule_times, days_of_week)
            VALUES (?,?,?,?,?)""", r)

    cur.execute("""INSERT OR IGNORE INTO meetings
        (title, transcript, summary, meeting_date, participants, format, risk_flag)
        VALUES (?,?,?,?,?,?,?)""",
        ("Переговоры с партнёром о доле", None,
         "Обсудили распределение доли 60/40. Партнёр настаивает на равном разделе. Договорились вернуться через неделю с юридическим заключением.",
         (today - timedelta(days=2)).isoformat(), "Ден, Алексей Смирнов", "negotiations", "medium"))

    cur.execute("""INSERT OR IGNORE INTO settings (key, value) VALUES (?,?)""",
                ("natal_date", "1983-07-22"))
    cur.execute("""INSERT OR IGNORE INTO settings (key, value) VALUES (?,?)""",
                ("natal_time", "14:30"))
    cur.execute("""INSERT OR IGNORE INTO settings (key, value) VALUES (?,?)""",
                ("natal_city", "Москва"))
    cur.execute("""INSERT OR IGNORE INTO settings (key, value) VALUES (?,?)""",
                ("briefing_morning_time", "07:00"))
    cur.execute("""INSERT OR IGNORE INTO settings (key, value) VALUES (?,?)""",
                ("briefing_evening_time", "22:00"))
    cur.execute("""INSERT OR IGNORE INTO settings (key, value) VALUES (?,?)""",
                ("readiness_threshold", "60"))

    morning_content = json.dumps({
        "type": "morning",
        "date": today.isoformat(),
        "state": {"energy": 8, "sleep": 7.5, "readiness": 82},
        "day_quality": {"numerology_day": 6, "astro_note": "Меркурий в трине с Юпитером — день для переговоров и контрактов"},
        "schedule": ["10:00 Созвон с командой", "13:00 Обед с партнёрами", "16:00 Стратегическая сессия"],
        "important_dates": ["Послезавтра — день рождения Анны Сидоровой"],
        "finances": {"balance_trend": "в норме", "alert": None},
        "priorities": ["Закрыть вопрос с юристом по договору", "Подготовить материалы к стратсессии"]
    })
    cur.execute("""INSERT OR IGNORE INTO briefings (briefing_type, content, briefing_date)
        VALUES (?,?,?)""", ("morning", morning_content, today.isoformat()))

    conn.commit()


app = FastAPI(title="LOS Mini App API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()


# ── HEALTH ──────────────────────────────────────────────────────────────

@app.get("/api/health/daily")
def get_daily_health(days: int = Query(7)):
    conn = get_db()
    rows = conn.execute("""SELECT * FROM daily_health ORDER BY date DESC LIMIT ?""", (days,)).fetchall()
    conn.close()
    return [dict(r) for r in reversed(rows)]

@app.post("/api/health/daily")
def post_daily_health(data: dict):
    conn = get_db()
    today = date.today().isoformat()
    fields = ["readiness_score","hrv_avg","sleep_score","sleep_hours","heart_rate_avg",
              "energy_subjective","workout_done","massage_done","alcohol"]
    updates = {f: data[f] for f in fields if f in data}
    if not updates:
        raise HTTPException(400, "No valid fields")
    set_clause = ", ".join(f"{k}=?" for k in updates)
    conn.execute(f"INSERT OR IGNORE INTO daily_health (date) VALUES (?)", (today,))
    conn.execute(f"UPDATE daily_health SET {set_clause} WHERE date=?", (*updates.values(), today))
    conn.commit(); conn.close()
    return {"ok": True}

@app.get("/api/health/medications")
def get_medications():
    conn = get_db()
    meds = conn.execute("SELECT * FROM medications WHERE is_active=1").fetchall()
    today = date.today().isoformat()
    result = []
    for med in meds:
        m = dict(med)
        log = conn.execute("""SELECT * FROM medication_intake_log
            WHERE medication_id=? AND scheduled_at LIKE ?""",
            (m["id"], f"{today}%")).fetchall()
        m["today_log"] = [dict(l) for l in log]
        result.append(m)
    conn.close()
    return result

@app.post("/api/health/medications/{med_id}/intake")
def log_medication_intake(med_id: int, data: dict):
    conn = get_db()
    scheduled_at = data.get("scheduled_at")
    status = data.get("status", "taken")
    conn.execute("""INSERT OR REPLACE INTO medication_intake_log
        (medication_id, scheduled_at, status, confirmed_at)
        VALUES (?,?,?,datetime('now'))""", (med_id, scheduled_at, status))
    conn.commit(); conn.close()
    return {"ok": True}

@app.post("/api/health/medications")
def add_medication(data: dict):
    conn = get_db()
    conn.execute("""INSERT INTO medications
        (name, dosage, schedule_times, days_of_week, with_food, is_critical, supply_units)
        VALUES (?,?,?,?,?,?,?)""",
        (data.get("name"), data.get("dosage"), data.get("schedule_times"),
         data.get("days_of_week"), data.get("with_food"), data.get("is_critical", 0),
         data.get("supply_units")))
    conn.commit(); conn.close()
    return {"ok": True}

@app.get("/api/health/visits")
def get_medical_visits():
    conn = get_db()
    rows = conn.execute("SELECT * FROM medical_visits ORDER BY visit_date ASC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/health/visits")
def add_medical_visit(data: dict):
    conn = get_db()
    conn.execute("""INSERT INTO medical_visits
        (visit_date, doctor, specialty, reason, schedule_pattern, status)
        VALUES (?,?,?,?,?,?)""",
        (data.get("visit_date"), data.get("doctor"), data.get("specialty"),
         data.get("reason"), data.get("schedule_pattern"), data.get("status","planned")))
    conn.commit(); conn.close()
    return {"ok": True}

@app.get("/api/health/labs")
def get_lab_results():
    conn = get_db()
    panels = conn.execute("SELECT * FROM lab_panels ORDER BY taken_on DESC").fetchall()
    result = []
    for p in panels:
        panel = dict(p)
        results = conn.execute("SELECT * FROM lab_results WHERE panel_id=?", (p["id"],)).fetchall()
        panel["results"] = [dict(r) for r in results]
        result.append(panel)
    conn.close()
    return result

@app.get("/api/health/labs/trends")
def get_lab_trends(marker_key: str = Query(...)):
    conn = get_db()
    rows = conn.execute("""SELECT taken_on, marker, value, unit, flag
        FROM lab_results WHERE marker_key=? ORDER BY taken_on ASC""", (marker_key,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── CALENDAR ─────────────────────────────────────────────────────────────

@app.get("/api/calendar/events")
def get_calendar_events(days: int = Query(7)):
    conn = get_db()
    today = date.today().isoformat()
    end = (date.today() + timedelta(days=days)).isoformat()
    rows = conn.execute("""SELECT * FROM calendar_events
        WHERE event_date BETWEEN ? AND ? ORDER BY event_date, start_time""",
        (today, end)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/calendar/events")
def add_calendar_event(data: dict):
    conn = get_db()
    conn.execute("""INSERT INTO calendar_events
        (event_date, title, start_time, end_time, meeting_type, cognitive_load, location, description)
        VALUES (?,?,?,?,?,?,?,?)""",
        (data.get("event_date"), data.get("title"), data.get("start_time"),
         data.get("end_time"), data.get("meeting_type","work"),
         data.get("cognitive_load","medium"), data.get("location"), data.get("description")))
    conn.commit(); conn.close()
    return {"ok": True}

@app.get("/api/calendar/today")
def get_today_events():
    conn = get_db()
    today = date.today().isoformat()
    rows = conn.execute("""SELECT * FROM calendar_events
        WHERE event_date=? ORDER BY start_time""", (today,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── FINANCES ─────────────────────────────────────────────────────────────

@app.get("/api/finances/summary")
def get_finances_summary():
    conn = get_db()
    today = date.today()
    month_start = today.replace(day=1).isoformat()

    total_exp = conn.execute("""SELECT SUM(amount) FROM expenses
        WHERE expense_date >= ?""", (month_start,)).fetchone()[0] or 0
    total_inc = conn.execute("""SELECT SUM(amount) FROM income
        WHERE income_date >= ?""", (month_start,)).fetchone()[0] or 0
    by_category = conn.execute("""SELECT category, SUM(amount) as total
        FROM expenses WHERE expense_date >= ? GROUP BY category""",
        (month_start,)).fetchall()
    limits = conn.execute("SELECT * FROM budget_limits").fetchall()
    recent = conn.execute("""SELECT * FROM expenses
        ORDER BY created_at DESC LIMIT 10""").fetchall()

    conn.close()
    return {
        "month_income": total_inc,
        "month_expenses": total_exp,
        "balance": total_inc - total_exp,
        "by_category": [dict(r) for r in by_category],
        "limits": [dict(r) for r in limits],
        "recent_expenses": [dict(r) for r in recent],
    }

@app.post("/api/finances/expenses")
def add_expense(data: dict):
    conn = get_db()
    conn.execute("""INSERT INTO expenses (amount, category, description, expense_date)
        VALUES (?,?,?,?)""",
        (data.get("amount"), data.get("category"),
         data.get("description"), data.get("expense_date", date.today().isoformat())))
    conn.commit(); conn.close()
    return {"ok": True}

@app.get("/api/finances/expenses")
def get_expenses(days: int = Query(30)):
    conn = get_db()
    since = (date.today() - timedelta(days=days)).isoformat()
    rows = conn.execute("""SELECT * FROM expenses
        WHERE expense_date >= ? ORDER BY expense_date DESC""", (since,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.get("/api/finances/monthly-trend")
def get_monthly_trend():
    conn = get_db()
    rows = conn.execute("""SELECT strftime('%Y-%m', expense_date) as month,
        category, SUM(amount) as total
        FROM expenses GROUP BY month, category ORDER BY month""").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── STATE (NEURO & BIO) ───────────────────────────────────────────────────

@app.get("/api/state/history")
def get_state_history(days: int = Query(7)):
    conn = get_db()
    rows = conn.execute("""SELECT * FROM daily_health ORDER BY date DESC LIMIT ?""", (days,)).fetchall()
    conn.close()
    return [dict(r) for r in reversed(rows)]

@app.post("/api/state/log")
def log_state(data: dict):
    conn = get_db()
    today = date.today().isoformat()
    conn.execute("INSERT OR IGNORE INTO daily_health (date) VALUES (?)", (today,))
    allowed = ["energy_subjective", "sleep_score", "sleep_hours", "workout_done", "massage_done", "alcohol"]
    updates = {k: v for k, v in data.items() if k in allowed}
    if updates:
        set_clause = ", ".join(f"{k}=?" for k in updates)
        conn.execute(f"UPDATE daily_health SET {set_clause} WHERE date=?", (*updates.values(), today))
    conn.commit(); conn.close()
    return {"ok": True}

@app.get("/api/state/today")
def get_today_state():
    conn = get_db()
    today = date.today().isoformat()
    row = conn.execute("SELECT * FROM daily_health WHERE date=?", (today,)).fetchone()
    conn.close()
    return dict(row) if row else {}


# ── BRIEFING / SUMMARY ────────────────────────────────────────────────────

@app.get("/api/briefing/today")
def get_today_briefing():
    conn = get_db()
    today = date.today().isoformat()
    rows = conn.execute("""SELECT * FROM briefings WHERE briefing_date=? ORDER BY created_at""",
        (today,)).fetchall()
    conn.close()
    result = []
    for r in rows:
        b = dict(r)
        try:
            b["content"] = json.loads(b["content"])
        except:
            pass
        result.append(b)
    return result

@app.get("/api/briefing/history")
def get_briefing_history(days: int = Query(7)):
    conn = get_db()
    since = (date.today() - timedelta(days=days)).isoformat()
    rows = conn.execute("""SELECT * FROM briefings WHERE briefing_date >= ?
        ORDER BY briefing_date DESC, created_at""", (since,)).fetchall()
    conn.close()
    result = []
    for r in rows:
        b = dict(r)
        try:
            b["content"] = json.loads(b["content"])
        except:
            pass
        result.append(b)
    return result


# ── CONTACTS ──────────────────────────────────────────────────────────────

@app.get("/api/contacts")
def get_contacts(circle: Optional[str] = Query(None)):
    conn = get_db()
    if circle:
        rows = conn.execute("SELECT * FROM contacts WHERE circle=? AND is_active=1 ORDER BY name", (circle,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM contacts WHERE is_active=1 ORDER BY circle, name").fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/contacts")
def add_contact(data: dict):
    conn = get_db()
    bday = data.get("birthday","")
    bday_md = bday[5:] if len(bday) >= 10 else None
    conn.execute("""INSERT INTO contacts
        (name, relation, circle, birthday, bday_md, interests, language, notes, city, occupation, touch_days)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (data.get("name"), data.get("relation"), data.get("circle","extended"),
         bday, bday_md, data.get("interests"), data.get("language","ru"),
         data.get("notes"), data.get("city"), data.get("occupation"), data.get("touch_days")))
    conn.commit(); conn.close()
    return {"ok": True}

@app.get("/api/contacts/birthdays")
def get_upcoming_birthdays(days: int = Query(30)):
    conn = get_db()
    today = date.today()
    rows = conn.execute("SELECT * FROM contacts WHERE is_active=1 AND bday_md IS NOT NULL").fetchall()
    upcoming = []
    for r in rows:
        c = dict(r)
        bday_md = c["bday_md"]
        try:
            bd = date(today.year, int(bday_md[:2]), int(bday_md[3:]))
            if bd < today:
                bd = date(today.year + 1, int(bday_md[:2]), int(bday_md[3:]))
            diff = (bd - today).days
            if diff <= days:
                c["days_until"] = diff
                c["next_birthday"] = bd.isoformat()
                upcoming.append(c)
        except:
            pass
    conn.close()
    return sorted(upcoming, key=lambda x: x["days_until"])


# ── MEETINGS ──────────────────────────────────────────────────────────────

@app.get("/api/meetings")
def get_meetings():
    conn = get_db()
    rows = conn.execute("SELECT * FROM meetings ORDER BY meeting_date DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/meetings")
def add_meeting(data: dict):
    conn = get_db()
    conn.execute("""INSERT INTO meetings
        (title, transcript, summary, meeting_date, participants, format, risk_flag)
        VALUES (?,?,?,?,?,?,?)""",
        (data.get("title"), data.get("transcript"), data.get("summary"),
         data.get("meeting_date", date.today().isoformat()),
         data.get("participants"), data.get("format","protocol"), data.get("risk_flag")))
    conn.commit(); conn.close()
    return {"ok": True}

@app.get("/api/meetings/{meeting_id}")
def get_meeting(meeting_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM meetings WHERE id=?", (meeting_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "Meeting not found")
    return dict(row)


# ── REMINDERS ─────────────────────────────────────────────────────────────

@app.get("/api/reminders")
def get_reminders():
    conn = get_db()
    rows = conn.execute("SELECT * FROM reminders WHERE is_active=1 ORDER BY due_at").fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/reminders")
def add_reminder(data: dict):
    conn = get_db()
    conn.execute("""INSERT INTO reminders
        (title, notes, due_at, schedule_times, days_of_week)
        VALUES (?,?,?,?,?)""",
        (data.get("title"), data.get("notes"), data.get("due_at"),
         data.get("schedule_times"), data.get("days_of_week")))
    conn.commit(); conn.close()
    return {"ok": True}

@app.post("/api/reminders/{reminder_id}/action")
def reminder_action(reminder_id: int, data: dict):
    conn = get_db()
    status = data.get("status", "done")
    conn.execute("""INSERT OR REPLACE INTO reminder_log
        (reminder_id, scheduled_at, status, confirmed_at)
        VALUES (?,datetime('now'),?,datetime('now'))""", (reminder_id, status))
    conn.commit(); conn.close()
    return {"ok": True}


# ── SETTINGS ──────────────────────────────────────────────────────────────

@app.get("/api/settings")
def get_settings():
    conn = get_db()
    rows = conn.execute("SELECT * FROM settings").fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}

@app.post("/api/settings")
def update_settings(data: dict):
    conn = get_db()
    for key, value in data.items():
        conn.execute("""INSERT OR REPLACE INTO settings (key, value, updated_at)
            VALUES (?,?,datetime('now'))""", (key, str(value)))
    conn.commit(); conn.close()
    return {"ok": True}


# ── DASHBOARD SUMMARY ─────────────────────────────────────────────────────

@app.get("/api/dashboard")
def get_dashboard():
    conn = get_db()
    today = date.today().isoformat()

    state = conn.execute("SELECT * FROM daily_health WHERE date=?", (today,)).fetchone()
    meds = conn.execute("SELECT COUNT(*) FROM medications WHERE is_active=1").fetchone()[0]
    pending_meds = conn.execute("""SELECT COUNT(*) FROM medication_intake_log
        WHERE scheduled_at LIKE ? AND status='pending'""", (f"{today}%",)).fetchone()[0]
    next_visit = conn.execute("""SELECT * FROM medical_visits
        WHERE visit_date >= ? AND status='planned' ORDER BY visit_date LIMIT 1""",
        (today,)).fetchone()
    today_events = conn.execute("""SELECT COUNT(*) FROM calendar_events
        WHERE event_date=?""", (today,)).fetchone()[0]
    month_start = date.today().replace(day=1).isoformat()
    month_expenses = conn.execute("""SELECT SUM(amount) FROM expenses
        WHERE expense_date >= ?""", (month_start,)).fetchone()[0] or 0
    upcoming_birthdays = conn.execute("""SELECT name, bday_md FROM contacts
        WHERE is_active=1 AND bday_md IS NOT NULL""").fetchall()

    bday_soon = []
    for c in upcoming_birthdays:
        try:
            bday_md = c["bday_md"]
            now = date.today()
            bd = date(now.year, int(bday_md[:2]), int(bday_md[3:]))
            if bd < now:
                bd = date(now.year + 1, int(bday_md[:2]), int(bday_md[3:]))
            if (bd - now).days <= 7:
                bday_soon.append({"name": c["name"], "days_until": (bd - now).days})
        except:
            pass

    conn.close()
    return {
        "today": today,
        "state": dict(state) if state else None,
        "state_logged": state is not None and state["energy_subjective"] is not None,
        "medications_total": meds,
        "medications_pending": pending_meds,
        "today_events_count": today_events,
        "next_medical_visit": dict(next_visit) if next_visit else None,
        "month_expenses": month_expenses,
        "upcoming_birthdays": bday_soon,
    }


if __name__ == "__main__":
    try:
        import uvicorn
    except ImportError:
        import subprocess, sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "uvicorn", "--quiet"])
        import uvicorn
    uvicorn.run("miniapp_api:app", host="0.0.0.0", port=8001, reload=True)
