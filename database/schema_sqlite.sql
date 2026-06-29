-- LOS — постоянное хранилище (SQLite). Идемпотентно.
-- Списки (времена приёма, дни недели) храним как JSON-текст; даты/время — ISO-строки.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS user_profile (
  telegram_user_id INTEGER PRIMARY KEY,
  chat_id INTEGER,
  name TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS daily_health (
  date TEXT PRIMARY KEY,                 -- 'YYYY-MM-DD'
  readiness_score INTEGER,
  hrv_avg REAL,
  sleep_score INTEGER,
  sleep_hours REAL,
  heart_rate_avg INTEGER,
  energy_subjective INTEGER,
  focus_subjective INTEGER,
  mood_subjective INTEGER,
  workout_done INTEGER,
  massage_done INTEGER,
  alcohol INTEGER,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS medications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  dosage TEXT,
  schedule_times TEXT,                   -- JSON: ["09:00","21:00"]
  days_of_week TEXT,                     -- JSON: [5]  (Пн=0..Вс=6); NULL = каждый день
  with_food TEXT,                        -- before / with / after / any
  is_critical INTEGER DEFAULT 0,
  supply_units INTEGER,
  is_active INTEGER DEFAULT 1,
  end_date TEXT,                         -- 'YYYY-MM-DD' или NULL
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS medication_intake_log (
  medication_id INTEGER NOT NULL,
  scheduled_at TEXT NOT NULL,            -- 'YYYY-MM-DD HH:MM:SS' (локальное время)
  status TEXT DEFAULT 'pending',         -- pending/taken/skipped/snoozed/missed
  reminders_sent INTEGER DEFAULT 0,
  confirmed_at TEXT,
  PRIMARY KEY (medication_id, scheduled_at)
);

-- Встречи (задел; Google Calendar — позже)
CREATE TABLE IF NOT EXISTS calendar_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date TEXT NOT NULL,
  title TEXT,
  start_time TEXT,
  meeting_type TEXT,
  cognitive_load TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);

-- Эпизодическая память (история реплик)
CREATE TABLE IF NOT EXISTS conversation_episodes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  role TEXT,
  content TEXT NOT NULL,
  agent_involved TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);

-- Общие напоминания (о чём угодно, не только таблетки)
CREATE TABLE IF NOT EXISTS reminders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  notes TEXT,
  due_at TEXT,                  -- разовое: 'YYYY-MM-DD HH:MM:SS'; повторяющееся: NULL
  schedule_times TEXT,          -- повторяющееся: JSON ["08:00"]; разовое: NULL
  days_of_week TEXT,            -- повторяющееся: JSON [0..6]; NULL = каждый день
  is_active INTEGER DEFAULT 1,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS reminder_log (
  reminder_id INTEGER NOT NULL,
  scheduled_at TEXT NOT NULL,
  status TEXT DEFAULT 'pending',   -- pending/taken/skipped/snoozed
  reminders_sent INTEGER DEFAULT 0,
  confirmed_at TEXT,
  PRIMARY KEY (reminder_id, scheduled_at)
);

-- Настройки в рантайме (напр. секретная ссылка Google Календаря)
CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT,
  updated_at TEXT DEFAULT (datetime('now'))
);

-- Смысловая память: факты и предпочтения (что бот знает и должен вспоминать)
CREATE TABLE IF NOT EXISTS facts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  text TEXT NOT NULL,
  category TEXT,                   -- preference/health/relationship/work/other
  source TEXT,                     -- 'аня' / 'рефлексия'
  is_active INTEGER DEFAULT 1,
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);

-- Network: контакты и отношения
CREATE TABLE IF NOT EXISTS contacts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  relation TEXT,                   -- кто это: партнёр/друг/семья/клиент…
  circle TEXT,                     -- core/close/work/extended
  birthday TEXT,                   -- как ввели (для показа)
  bday_md TEXT,                    -- 'MM-DD' для матчинга
  interests TEXT,
  language TEXT,
  notes TEXT,
  last_contact TEXT,               -- 'YYYY-MM-DD'
  touch_days INTEGER,              -- желаемый ритм касания, дней
  is_active INTEGER DEFAULT 1,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS greeting_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  contact_id INTEGER,
  occasion TEXT,
  text TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);

-- ❤️ Health: загруженные панели анализов (один бланк/сдача = одна панель)
CREATE TABLE IF NOT EXISTS lab_panels (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  taken_on TEXT,                   -- 'YYYY-MM-DD' дата сдачи (из бланка или дата загрузки)
  lab_name TEXT,                   -- лаборатория (Инвитро/Гемотест…), если распозналась
  source TEXT,                     -- photo / pdf / manual / text
  notes TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);

-- ❤️ Health: отдельные показатели анализов (много на панель), для трендов
CREATE TABLE IF NOT EXISTS lab_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  panel_id INTEGER,
  taken_on TEXT,                   -- денормализуем дату сдачи для трендов
  marker TEXT NOT NULL,            -- имя показателя по-русски, напр. «Витамин D 25-OH»
  marker_key TEXT,                 -- нормализованный ключ для матчинга трендов
  value REAL,                      -- числовое значение (NULL если нечисловое)
  value_text TEXT,                 -- оригинал, если не число («отрицательно», «<0.5»)
  unit TEXT,
  ref_low REAL,
  ref_high REAL,
  flag TEXT,                       -- low / high / normal / NULL
  created_at TEXT DEFAULT (datetime('now'))
);

-- ❤️ Health: визиты к врачам (план и факт)
CREATE TABLE IF NOT EXISTS medical_visits (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  visit_date TEXT,                 -- 'YYYY-MM-DD'
  doctor TEXT,                     -- ФИО/кто
  specialty TEXT,                  -- кардиолог/стоматолог…
  reason TEXT,                     -- повод
  outcome TEXT,                    -- что назначили/итог (заполняется после визита)
  followup_date TEXT,              -- когда повторно, 'YYYY-MM-DD'
  status TEXT DEFAULT 'planned',   -- planned / done / cancelled
  created_at TEXT DEFAULT (datetime('now'))
);

-- 🎙 Communication: разобранные встречи/переговоры (запись → транскрипт → сводка)
CREATE TABLE IF NOT EXISTS meetings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  chat_id INTEGER,
  title TEXT,                      -- короткое название встречи
  transcript TEXT,                 -- полная расшифровка
  summary TEXT,                    -- сводка-протокол (дефолтный формат)
  created_at TEXT DEFAULT (datetime('now'))
);
