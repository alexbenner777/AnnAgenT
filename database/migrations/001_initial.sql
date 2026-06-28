-- LOS core schema (без pgvector). Идемпотентно: можно запускать повторно.
-- pgvector-часть вынесена в 002_pgvector.sql (необязательна для MVP).

-- Пользователь системы (босс / Аня-интерфейс)
CREATE TABLE IF NOT EXISTS user_profile (
  id SERIAL PRIMARY KEY,
  telegram_user_id BIGINT UNIQUE NOT NULL,
  chat_id BIGINT,
  name VARCHAR(100),
  timezone VARCHAR(50) DEFAULT 'Europe/Moscow',
  birth_date DATE,
  birth_time TIME,
  birth_place VARCHAR(200),
  birth_name VARCHAR(200),
  created_at TIMESTAMP DEFAULT NOW()
);

-- Ежедневные данные здоровья (Oura + субъективный ввод)
CREATE TABLE IF NOT EXISTS daily_health (
  id SERIAL PRIMARY KEY,
  date DATE NOT NULL UNIQUE,
  readiness_score INTEGER,
  hrv_avg FLOAT,
  sleep_score INTEGER,
  sleep_hours FLOAT,
  heart_rate_avg INTEGER,
  energy_subjective INTEGER,
  focus_subjective INTEGER,
  mood_subjective INTEGER,
  workout_done BOOLEAN,
  massage_done BOOLEAN,
  alcohol BOOLEAN,
  data_conflict BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Встречи из календаря (Phase 1: задел; Google Calendar — позже)
CREATE TABLE IF NOT EXISTS calendar_events (
  id SERIAL PRIMARY KEY,
  date DATE NOT NULL,
  title VARCHAR(500),
  start_time TIMESTAMP,
  end_time TIMESTAMP,
  meeting_type VARCHAR(50),
  cognitive_load VARCHAR(20),
  participants TEXT[],
  is_protected BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Эпизодическая память (история разговоров)
CREATE TABLE IF NOT EXISTS conversation_episodes (
  id SERIAL PRIMARY KEY,
  session_id UUID,
  role VARCHAR(20),
  content TEXT NOT NULL,
  agent_involved VARCHAR(50),
  created_at TIMESTAMP DEFAULT NOW()
);

-- ===== Medication Reminder Agent =====
CREATE TABLE IF NOT EXISTS medications (
  id SERIAL PRIMARY KEY,
  name VARCHAR(200),
  dosage VARCHAR(100),
  frequency VARCHAR(100),
  schedule_times TIME[],                 -- времена приёма: {'08:00','21:00'}
  with_food VARCHAR(20),                 -- before / with / after / any
  is_supplement BOOLEAN DEFAULT FALSE,
  is_critical BOOLEAN DEFAULT FALSE,     -- напоминать даже в неприкосновенных блоках
  supply_units INTEGER,                  -- остаток, шт.
  supply_low_days INTEGER DEFAULT 5,
  prescribed_by VARCHAR(200),
  start_date DATE,
  end_date DATE,
  is_active BOOLEAN DEFAULT TRUE,
  research_summary TEXT,                 -- ресёрч от Health Agent (Фаза 2)
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS medication_intake_log (
  id SERIAL PRIMARY KEY,
  medication_id INTEGER REFERENCES medications(id),
  scheduled_at TIMESTAMP NOT NULL,       -- когда должен был принять (локальное время)
  status VARCHAR(20) DEFAULT 'pending',  -- pending/taken/skipped/snoozed/missed
  confirmed_at TIMESTAMP,
  reminders_sent INTEGER DEFAULT 0,
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(medication_id, scheduled_at)
);

-- ===== Phase 2 (задел схемы) =====
CREATE TABLE IF NOT EXISTS contacts (
  id SERIAL PRIMARY KEY,
  full_name VARCHAR(200) NOT NULL,
  role VARCHAR(100),
  circle VARCHAR(20),
  interests TEXT[],
  occupation VARCHAR(200),
  marital_status VARCHAR(50),
  religion VARCHAR(100),
  country VARCHAR(100),
  city VARCHAR(100),
  birth_date DATE,
  notes TEXT,
  summary TEXT,
  last_contact DATE,
  contact_frequency_days INTEGER,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS gift_history (
  id SERIAL PRIMARY KEY,
  contact_id INTEGER REFERENCES contacts(id),
  occasion VARCHAR(200),
  gift_description TEXT,
  direction VARCHAR(10),
  date DATE,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS greeting_history (
  id SERIAL PRIMARY KEY,
  contact_id INTEGER REFERENCES contacts(id),
  occasion VARCHAR(200),
  greeting_text TEXT,
  sent_date DATE,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS health_tests (
  id SERIAL PRIMARY KEY,
  test_name VARCHAR(200),
  test_date DATE,
  value FLOAT,
  unit VARCHAR(50),
  normal_min FLOAT,
  normal_max FLOAT,
  notes TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS doctor_visits (
  id SERIAL PRIMARY KEY,
  doctor_name VARCHAR(200),
  specialty VARCHAR(100),
  visit_date DATE,
  next_visit_date DATE,
  notes TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS meeting_analyses (
  id SERIAL PRIMARY KEY,
  meeting_date DATE,
  participants TEXT[],
  context TEXT,
  manipulation_detected TEXT[],
  hidden_conflicts TEXT[],
  sincerity_issues TEXT[],
  personality_profiles JSONB,
  legal_risks TEXT,
  recommendations TEXT,
  risk_level VARCHAR(20),
  created_at TIMESTAMP DEFAULT NOW()
);

-- Настройки системы
CREATE TABLE IF NOT EXISTS system_settings (
  key VARCHAR(100) PRIMARY KEY,
  value TEXT,
  updated_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO system_settings (key, value) VALUES
  ('morning_briefing_time', '07:00'),
  ('evening_digest_time', '22:00'),
  ('timezone', 'Europe/Moscow'),
  ('readiness_low_threshold', '65'),
  ('reminder_ping_interval_minutes', '5'),
  ('max_pings', '2'),
  ('medication_reminder_repeat_minutes', '15'),
  ('medication_max_reminders', '3'),
  ('medication_supply_low_days', '5')
ON CONFLICT (key) DO NOTHING;
