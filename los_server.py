"""
LOS Mini App — полный standalone сервер
Чистый Python stdlib: http.server + sqlite3 + json
Порт 5000. Зависимости: НОЛЬ.
"""
import http.server
import json
import os
import re
import sqlite3
import threading
import urllib.parse
from datetime import date, datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "los_miniapp.db")
PUBLIC_DIR = os.path.join(os.path.dirname(__file__), "public")


# ─────────────────────────── DB bootstrap ───────────────────────────

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS medications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    dosage TEXT,
    schedule_times TEXT DEFAULT '[]',
    days_of_week TEXT,
    with_food TEXT,
    is_active INTEGER DEFAULT 1,
    is_critical INTEGER DEFAULT 0,
    supply_units INTEGER,
    end_date TEXT,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS medication_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    medication_id INTEGER,
    scheduled_at TEXT,
    taken_at TEXT,
    status TEXT DEFAULT 'pending',
    FOREIGN KEY(medication_id) REFERENCES medications(id)
);

CREATE TABLE IF NOT EXISTS medication_intake_log (
    medication_id INTEGER NOT NULL,
    scheduled_at TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    reminders_sent INTEGER DEFAULT 0,
    confirmed_at TEXT,
    PRIMARY KEY (medication_id, scheduled_at)
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

CREATE TABLE IF NOT EXISTS lab_panels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lab_name TEXT,
    taken_on TEXT,
    source TEXT,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS lab_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    panel_id INTEGER,
    taken_on TEXT,
    marker TEXT,
    marker_key TEXT,
    value REAL,
    value_text TEXT,
    unit TEXT,
    ref_low REAL,
    ref_high REAL,
    flag TEXT DEFAULT 'normal',
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(panel_id) REFERENCES lab_panels(id)
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

CREATE TABLE IF NOT EXISTS finance_limits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT,
    monthly_limit REAL
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

CREATE TABLE IF NOT EXISTS daily_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    state_date TEXT UNIQUE,
    energy_subjective INTEGER,
    sleep_score INTEGER,
    readiness_score INTEGER,
    hrv_avg REAL,
    workout_done INTEGER DEFAULT 0,
    massage_done INTEGER DEFAULT 0,
    alcohol INTEGER DEFAULT 0,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS briefings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    briefing_type TEXT DEFAULT 'morning',
    content TEXT,
    briefing_date TEXT DEFAULT (date('now')),
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TEXT DEFAULT (datetime('now'))
);
""")

    # Seed if empty
    row = conn.execute("SELECT COUNT(*) FROM medications").fetchone()[0]
    if row == 0:
        today = date.today().isoformat()
        tomorrow = (date.today() + timedelta(1)).isoformat()
        next_week = (date.today() + timedelta(7)).isoformat()
        day_minus1 = (date.today() - timedelta(1)).isoformat()
        day_minus2 = (date.today() - timedelta(2)).isoformat()
        day_minus3 = (date.today() - timedelta(3)).isoformat()
        day_minus5 = (date.today() - timedelta(5)).isoformat()
        day_minus7 = (date.today() - timedelta(7)).isoformat()
        day_plus3 = (date.today() + timedelta(3)).isoformat()

        cur = conn.cursor()
        cur.executemany(
            "INSERT INTO medications(name,dosage,schedule_times,is_critical,is_active) VALUES (?,?,?,?,?)",
            [
                ('Витамин D3','5000 МЕ','["09:00"]',0,1),
                ('Магний','400 мг','["21:00"]',0,1),
                ('Омега-3','2000 мг','["09:00","14:00"]',0,1),
                ('Мелатонин','3 мг','["22:30"]',0,1),
            ])
        cur.executemany(
            "INSERT INTO medication_logs(medication_id,scheduled_at,status) VALUES (?,?,?)",
            [
                (1,f'{today} 09:00','pending'),
                (2,f'{today} 21:00','pending'),
                (3,f'{today} 09:00','taken'),
                (3,f'{today} 14:00','pending'),
                (4,f'{today} 22:30','pending'),
            ])
        cur.executemany(
            "INSERT INTO medical_visits(specialty,doctor,visit_date,status,reason) VALUES (?,?,?,?,?)",
            [
                ('Кардиология','Иванов А.В.',next_week,'planned','Плановый осмотр, ЭКГ'),
                ('Остеопатия','Смирнова Е.Н.',tomorrow,'planned','Сеанс коррекции позвоночника'),
                ('Нутрициология','Козлов М.П.',None,'planned','Разбор анализов'),
            ])
        cur.execute("INSERT INTO lab_panels(lab_name,taken_on) VALUES (?,?)", ('Инвитро', today))
        cur.executemany(
            "INSERT INTO lab_results(panel_id,marker,value,unit,ref_low,ref_high,flag) VALUES (?,?,?,?,?,?,?)",
            [
                (1,'Витамин D',45.3,'нг/мл',30,100,'normal'),
                (1,'Ферритин',18.5,'нг/мл',20,250,'low'),
                (1,'B12',380,'пг/мл',200,900,'normal'),
                (1,'Тестостерон общий',22.4,'нмоль/л',12,35,'normal'),
                (1,'TSH',2.1,'мкМЕ/мл',0.4,4.0,'normal'),
                (1,'Гемоглобин',155,'г/л',130,170,'normal'),
                (1,'СРБ',0.8,'мг/л',0,5,'normal'),
                (1,'Гомоцистеин',14.2,'мкмоль/л',5,12,'high'),
            ])
        cur.executemany(
            "INSERT INTO calendar_events(event_date,title,start_time,end_time,meeting_type,cognitive_load,location,description) VALUES (?,?,?,?,?,?,?,?)",
            [
                (today,'Встреча с командой','10:00','11:30','work','high','Офис','Планёрка по проекту LOS'),
                (tomorrow,'Остеопат','12:00','13:00','health','low','Клиника','Сеанс коррекции'),
                (tomorrow,'Звонок с инвестором','15:00','16:00','work','high','Zoom','Питч проекта'),
                (today,'Тренировка','19:00','20:30','personal','medium','Зал','Силовая'),
                (day_plus3,'День рождения Маши','','','personal','low','',''),
            ])
        cur.executemany(
            "INSERT INTO expenses(amount,category,description,expense_date) VALUES (?,?,?,?)",
            [
                (3500,'Еда','Рестораны',today),
                (1200,'Транспорт','Яндекс Go',today),
                (8000,'Здоровье','Клиника',today),
                (2300,'Продукты','ВкусВилл',day_minus1),
                (15000,'Развлечения','Билеты на концерт',day_minus3),
                (12000,'Спорт','Абонемент в зал',day_minus5),
                (5600,'Одежда','Новые кроссовки',day_minus7),
            ])
        cur.execute(
            "INSERT INTO income(amount,source,income_date) VALUES (?,?,?)",
            (450000,'Оплата проекта',day_minus2))
        cur.executemany(
            "INSERT INTO budget_limits(category,monthly_limit) VALUES (?,?)",
            [
                ('Еда',50000),('Транспорт',15000),('Развлечения',30000),('Здоровье',40000),
            ])
        cur.executemany(
            "INSERT INTO contacts(name,circle,relation,city,birthday,notes) VALUES (?,?,?,?,?,?)",
            [
                ('Аня Иванова','core','Ассистент','Москва','1995-03-15',''),
                ('Дима Козлов','close','Друг','Москва','1988-07-22',''),
                ('Маша Петрова','close','Подруга','Санкт-Петербург',day_plus3,''),
                ('Сергей Лавров','work','Партнёр','Москва','1982-11-03',''),
                ('Катя Смирнова','work','Коллега','Москва','1990-04-18',''),
                ('Алексей Борисов','extended','Знакомый','Лондон','1985-09-27',''),
                ('Виктор Новиков','work','Инвестор','Дубай','1979-01-14',''),
            ])
        cur.executemany(
            "INSERT INTO daily_state(state_date,energy_subjective,sleep_score,readiness_score,hrv_avg,workout_done) VALUES (?,?,?,?,?,?)",
            [
                (today,7,8,72,45.3,1),
                (day_minus1,6,7,65,38.1,0),
                (day_minus2,8,9,81,52.0,1),
                (day_minus3,5,6,58,33.4,0),
            ])
        import json as _json
        briefing_content = _json.dumps({
            "priorities": ["Встреча с командой в 10:00 — подготовить слайды","Ферритин низкий — рассмотреть добавку железа"],
            "schedule": ["10:00 Встреча с командой (офис)","19:00 Тренировка (зал)"],
            "state": {"energy": 7, "sleep": 8, "readiness": 72},
            "important_dates": ["Завтра: Звонок с инвестором в 15:00",f"Через 3 дня: ДР Маши"]
        })
        cur.execute(
            "INSERT INTO briefings(briefing_date,briefing_type,content) VALUES (?,?,?)",
            (today,'morning', briefing_content))
        conn.commit()
    conn.close()


# ─────────────────────────── DB helpers ─────────────────────────────

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def rows(conn, sql, params=()):
    return [dict(r) for r in conn.execute(sql, params).fetchall()]

def one(conn, sql, params=()):
    r = conn.execute(sql, params).fetchone()
    return dict(r) if r else None


# ─────────────────────────── API handlers ───────────────────────────

def today_str():
    return date.today().isoformat()

def handle_api(method, path, query, body):
    """Route API requests. Returns (status_code, data_dict)."""
    c = db()
    try:
        # ── Dashboard ──────────────────────────────────────────────
        if path == "/dashboard" and method == "GET":
            tod = today_str()
            state = one(c, "SELECT * FROM daily_state WHERE state_date=?", (tod,))
            meds_pending = c.execute(
                "SELECT COUNT(*) FROM medication_logs WHERE DATE(scheduled_at)=? AND status='pending'", (tod,)
            ).fetchone()[0]
            meds_total = c.execute(
                "SELECT COUNT(*) FROM medication_logs WHERE DATE(scheduled_at)=?", (tod,)
            ).fetchone()[0]
            today_ev = c.execute(
                "SELECT COUNT(*) FROM calendar_events WHERE event_date=?", (tod,)
            ).fetchone()[0]
            next_visit = one(c,
                "SELECT * FROM medical_visits WHERE status='planned' AND visit_date>=? ORDER BY visit_date LIMIT 1", (tod,))
            month_start = tod[:7] + "-01"
            month_exp = c.execute(
                "SELECT COALESCE(SUM(amount),0) FROM finances WHERE type='expense' AND expense_date>=?", (month_start,)
            ).fetchone()[0]
            bdays = rows(c, "SELECT * FROM contacts WHERE birthday IS NOT NULL AND birthday!= ''")
            bday_soon = []
            for b in bdays:
                try:
                    bday = datetime.strptime(b["birthday"][:10], "%Y-%m-%d").date()
                    this_year = bday.replace(year=date.today().year)
                    if this_year < date.today(): this_year = this_year.replace(year=date.today().year+1)
                    days_until = (this_year - date.today()).days
                    if days_until <= 30:
                        bday_soon.append({"id": b["id"], "name": b["name"], "days_until": days_until})
                except: pass
            bday_soon.sort(key=lambda x: x["days_until"])
            return 200, {
                "today": tod,
                "state": state,
                "state_logged": state is not None,
                "medications_total": meds_total,
                "medications_pending": meds_pending,
                "today_events_count": today_ev,
                "next_medical_visit": next_visit,
                "month_expenses": month_exp,
                "upcoming_birthdays": bday_soon[:5],
            }

        # ── Health: medications ────────────────────────────────────
        if path == "/health/medications" and method == "GET":
            meds = rows(c, "SELECT * FROM medications WHERE is_active=1 ORDER BY id")
            tod = today_str()
            for m in meds:
                logs = rows(c,
                    "SELECT * FROM medication_logs WHERE medication_id=? AND DATE(scheduled_at)=? ORDER BY scheduled_at",
                    (m["id"], tod))
                m["today_log"] = logs
            return 200, meds

        if path == "/health/medications" and method == "POST":
            b = body or {}
            times = b.get("schedule_times", "[]")
            c.execute("INSERT INTO medications(name,dosage,schedule_times,is_critical) VALUES(?,?,?,?)",
                (b.get("name",""), b.get("dosage",""), times, 0))
            med_id = c.lastrowid
            # Create today logs
            try:
                schedule = json.loads(times)
                tod = today_str()
                for t in schedule:
                    c.execute("INSERT INTO medication_logs(medication_id,scheduled_at,status) VALUES(?,?,?)",
                        (med_id, f"{tod} {t}", "pending"))
            except: pass
            c.commit()
            return 200, {"ok": True}

        m = re.match(r"^/health/medications/(\d+)/intake$", path)
        if m and method == "POST":
            med_id = int(m.group(1))
            b = body or {}
            sched = b.get("scheduled_at", "")
            status = b.get("status", "taken")
            taken_at = datetime.now().isoformat() if status == "taken" else None
            existing = one(c,
                "SELECT * FROM medication_logs WHERE medication_id=? AND scheduled_at=?",
                (med_id, sched))
            if existing:
                c.execute("UPDATE medication_logs SET status=?,taken_at=? WHERE id=?",
                    (status, taken_at, existing["id"]))
            else:
                c.execute("INSERT INTO medication_logs(medication_id,scheduled_at,status,taken_at) VALUES(?,?,?,?)",
                    (med_id, sched, status, taken_at))
            c.commit()
            return 200, {"ok": True}

        # ── Health: visits ─────────────────────────────────────────
        if path == "/health/visits" and method == "GET":
            return 200, rows(c, "SELECT * FROM medical_visits ORDER BY visit_date NULLS LAST, id")

        # ── Health: labs ───────────────────────────────────────────
        if path == "/health/labs" and method == "GET":
            panels = rows(c, "SELECT * FROM lab_panels ORDER BY taken_on DESC")
            for p in panels:
                p["results"] = rows(c, "SELECT * FROM lab_results WHERE panel_id=?", (p["id"],))
            return 200, panels

        # ── Calendar ───────────────────────────────────────────────
        if path == "/calendar/events" and method == "GET":
            days = int(query.get("days", ["7"])[0])
            tod = today_str()
            end = (date.today() + timedelta(days)).isoformat()
            return 200, rows(c,
                "SELECT * FROM calendar_events WHERE event_date>=? AND event_date<=? ORDER BY event_date,start_time",
                (tod, end))

        # ── Finances ───────────────────────────────────────────────
        if path == "/finances/summary" and method == "GET":
            month_start = today_str()[:7] + "-01"
            exp = c.execute("SELECT COALESCE(SUM(amount),0) FROM finances WHERE type='expense' AND expense_date>=?",
                (month_start,)).fetchone()[0]
            inc = c.execute("SELECT COALESCE(SUM(amount),0) FROM finances WHERE type='income' AND expense_date>=?",
                (month_start,)).fetchone()[0]
            by_cat = rows(c,
                "SELECT category,SUM(amount) as total FROM finances WHERE type='expense' AND expense_date>=? GROUP BY category ORDER BY total DESC",
                (month_start,))
            limits = rows(c, "SELECT * FROM finance_limits")
            recent = rows(c, "SELECT * FROM finances WHERE type='expense' ORDER BY id DESC LIMIT 10")
            return 200, {
                "month_expenses": exp,
                "month_income": inc,
                "balance": inc - exp,
                "by_category": by_cat,
                "limits": limits,
                "recent_expenses": recent,
            }

        if path == "/finances/expenses" and method == "POST":
            b = body or {}
            c.execute("INSERT INTO finances(amount,category,description,expense_date,type) VALUES(?,?,?,?,?)",
                (b.get("amount",0), b.get("category","Другое"), b.get("description",""),
                 today_str(), "expense"))
            c.commit()
            return 200, {"ok": True}

        # ── State ──────────────────────────────────────────────────
        if path == "/state/today" and method == "GET":
            return 200, one(c, "SELECT * FROM daily_state WHERE state_date=?", (today_str(),))

        if path == "/state/history" and method == "GET":
            days = int(query.get("days", ["7"])[0])
            since = (date.today() - timedelta(days)).isoformat()
            return 200, rows(c, "SELECT * FROM daily_state WHERE state_date>=? ORDER BY state_date DESC", (since,))

        if path == "/state/log" and method == "POST":
            b = body or {}
            tod = today_str()
            existing = one(c, "SELECT id FROM daily_state WHERE state_date=?", (tod,))
            if existing:
                c.execute("""UPDATE daily_state SET energy_subjective=?,sleep_score=?,
                    workout_done=?,massage_done=?,alcohol=? WHERE state_date=?""",
                    (b.get("energy_subjective"), b.get("sleep_score"),
                     b.get("workout_done",0), b.get("massage_done",0), b.get("alcohol",0), tod))
            else:
                c.execute("""INSERT INTO daily_state(state_date,energy_subjective,sleep_score,
                    workout_done,massage_done,alcohol) VALUES(?,?,?,?,?,?)""",
                    (tod, b.get("energy_subjective"), b.get("sleep_score"),
                     b.get("workout_done",0), b.get("massage_done",0), b.get("alcohol",0)))
            c.commit()
            return 200, {"ok": True}

        # ── Briefing ───────────────────────────────────────────────
        if path == "/briefing/today" and method == "GET":
            brs = rows(c, "SELECT * FROM briefings WHERE briefing_date=? ORDER BY id DESC", (today_str(),))
            for br in brs:
                try: br["content"] = json.loads(br["content"])
                except: pass
            return 200, brs

        # ── Contacts ───────────────────────────────────────────────
        if path == "/contacts" and method == "GET":
            return 200, rows(c, "SELECT * FROM contacts ORDER BY circle,name")

        if path == "/contacts/birthdays" and method == "GET":
            days = int(query.get("days", ["30"])[0])
            contacts = rows(c, "SELECT * FROM contacts WHERE birthday IS NOT NULL AND birthday!=''")
            result = []
            for b in contacts:
                try:
                    bday = datetime.strptime(b["birthday"][:10], "%Y-%m-%d").date()
                    this_year = bday.replace(year=date.today().year)
                    if this_year < date.today(): this_year = this_year.replace(year=date.today().year+1)
                    du = (this_year - date.today()).days
                    if du <= days:
                        result.append({**b, "days_until": du})
                except: pass
            result.sort(key=lambda x: x["days_until"])
            return 200, result

        # ── Settings ───────────────────────────────────────────────
        if path == "/settings" and method == "GET":
            return 200, one(c, "SELECT * FROM settings WHERE id=1") or {}

        if path == "/settings" and method == "POST":
            b = body or {}
            existing = one(c, "SELECT id FROM settings WHERE id=1")
            if existing:
                c.execute("""UPDATE settings SET natal_date=?,natal_time=?,natal_city=?,
                    briefing_morning_time=?,briefing_evening_time=? WHERE id=1""",
                    (b.get("natal_date"), b.get("natal_time"), b.get("natal_city"),
                     b.get("briefing_morning_time","07:00"), b.get("briefing_evening_time","22:00")))
            else:
                c.execute("""INSERT INTO settings(id,natal_date,natal_time,natal_city,
                    briefing_morning_time,briefing_evening_time) VALUES(1,?,?,?,?,?)""",
                    (b.get("natal_date"), b.get("natal_time"), b.get("natal_city"),
                     b.get("briefing_morning_time","07:00"), b.get("briefing_evening_time","22:00")))
            c.commit()
            return 200, {"ok": True}

        return 404, {"error": "Not found", "path": path}

    finally:
        c.close()


# ─────────────────────────── HTTP Handler ───────────────────────────

MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css",
    ".js": "application/javascript",
    ".json": "application/json",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".woff2": "font/woff2",
}

class LOSHandler(http.server.BaseHTTPRequestHandler):

    def _send(self, status, content_type, body):
        if isinstance(body, str): body = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status, data):
        self._send(status, "application/json", json.dumps(data, ensure_ascii=False, default=str))

    def _serve_file(self, filepath):
        ext = os.path.splitext(filepath)[1].lower()
        ct = MIME.get(ext, "application/octet-stream")
        with open(filepath, "rb") as f:
            data = f.read()
        self._send(200, ct, data)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _handle(self, method):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # ── API routes ─────────────────────────────────────────────
        if path.startswith("/api/"):
            api_path = path[4:]  # strip /api
            body = None
            if method == "POST":
                length = int(self.headers.get("Content-Length", 0))
                if length:
                    try: body = json.loads(self.rfile.read(length))
                    except: body = {}
            try:
                status, data = handle_api(method, api_path, query, body)
                self._json(status, data)
            except Exception as e:
                self._json(500, {"error": str(e)})
            return

        # ── Static files ───────────────────────────────────────────
        if method == "GET":
            # Strip leading slash, map to public/
            rel = path.lstrip("/") or "index.html"
            filepath = os.path.join(PUBLIC_DIR, rel)

            if os.path.isfile(filepath):
                self._serve_file(filepath)
            else:
                # SPA fallback → index.html
                index = os.path.join(PUBLIC_DIR, "index.html")
                if os.path.isfile(index):
                    self._serve_file(index)
                else:
                    self._json(404, {"error": "index.html not found"})
        else:
            self._json(405, {"error": "Method not allowed"})

    def do_GET(self):  self._handle("GET")
    def do_POST(self): self._handle("POST")

    def log_message(self, fmt, *args):
        # Only show non-200 responses to keep logs clean
        if args and len(args) >= 2 and not str(args[1]).startswith("2"):
            super().log_message(fmt, *args)


# ─────────────────────────── Main ───────────────────────────────────

if __name__ == "__main__":
    import http.server

    print("🗃️  Initialising database...")
    init_db()

    os.makedirs(PUBLIC_DIR, exist_ok=True)

    server = http.server.ThreadingHTTPServer(("0.0.0.0", 5000), LOSHandler)
    print("🚀 LOS server running on http://0.0.0.0:5000")
    print("📱 Open Preview to see the Mini App")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n✋ Stopped")
