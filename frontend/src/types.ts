// Telegram WebApp global type
declare global {
  interface Window {
    Telegram?: {
      WebApp: {
        ready: () => void
        expand: () => void
        close: () => void
        setHeaderColor: (color: string) => void
        setBackgroundColor: (color: string) => void
        MainButton: {
          text: string
          show: () => void
          hide: () => void
          onClick: (fn: () => void) => void
          enable: () => void
          disable: () => void
        }
        showAlert: (message: string, callback?: () => void) => void
        showConfirm: (message: string, callback?: (confirmed: boolean) => void) => void
        HapticFeedback: {
          impactOccurred: (style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft') => void
          notificationOccurred: (type: 'error' | 'success' | 'warning') => void
          selectionChanged: () => void
        }
        initData: string
        initDataUnsafe: {
          user?: {
            id: number
            first_name: string
            last_name?: string
            username?: string
          }
        }
        themeParams: {
          bg_color?: string
          text_color?: string
          hint_color?: string
          link_color?: string
          button_color?: string
          button_text_color?: string
        }
        colorScheme: 'light' | 'dark'
      }
    }
  }
}

// API Types
export interface DailyHealth {
  date: string
  readiness_score?: number
  hrv_avg?: number
  sleep_score?: number
  sleep_hours?: number
  heart_rate_avg?: number
  energy_subjective?: number
  workout_done?: number
  massage_done?: number
  alcohol?: number
}

export interface Medication {
  id: number
  name: string
  dosage?: string
  schedule_times?: string
  days_of_week?: string
  with_food?: string
  is_critical?: number
  supply_units?: number
  is_active?: number
  end_date?: string
  today_log?: MedicationLog[]
}

export interface MedicationLog {
  medication_id: number
  scheduled_at: string
  status: 'pending' | 'taken' | 'skipped' | 'snoozed'
  confirmed_at?: string
}

export interface CalendarEvent {
  id: number
  event_date: string
  title?: string
  start_time?: string
  end_time?: string
  meeting_type?: string
  cognitive_load?: string
  location?: string
  description?: string
}

export interface Expense {
  id: number
  amount: number
  category?: string
  description?: string
  expense_date?: string
}

export interface FinancesSummary {
  month_income: number
  month_expenses: number
  balance: number
  by_category: { category: string; total: number }[]
  limits: { id: number; category: string; monthly_limit: number }[]
  recent_expenses: Expense[]
}

export interface Contact {
  id: number
  name: string
  relation?: string
  circle?: string
  birthday?: string
  bday_md?: string
  interests?: string
  language?: string
  notes?: string
  city?: string
  occupation?: string
  last_contact?: string
  touch_days?: number
  days_until?: number
  next_birthday?: string
}

export interface Meeting {
  id: number
  title?: string
  transcript?: string
  summary?: string
  meeting_date?: string
  participants?: string
  format?: string
  risk_flag?: string
}

export interface Reminder {
  id: number
  title: string
  notes?: string
  due_at?: string
  schedule_times?: string
  days_of_week?: string
  is_active?: number
}

export interface MedicalVisit {
  id: number
  visit_date?: string
  doctor?: string
  specialty?: string
  reason?: string
  outcome?: string
  followup_date?: string
  schedule_pattern?: string
  status?: string
}

export interface LabPanel {
  id: number
  taken_on?: string
  lab_name?: string
  source?: string
  notes?: string
  results?: LabResult[]
}

export interface LabResult {
  id: number
  panel_id?: number
  taken_on?: string
  marker: string
  marker_key?: string
  value?: number
  value_text?: string
  unit?: string
  ref_low?: number
  ref_high?: number
  flag?: string
}

export interface Dashboard {
  today: string
  state?: DailyHealth
  state_logged: boolean
  medications_total: number
  medications_pending: number
  today_events_count: number
  next_medical_visit?: MedicalVisit
  month_expenses: number
  upcoming_birthdays: { name: string; days_until: number }[]
}

export interface Briefing {
  id: number
  briefing_type: string
  content: any
  briefing_date: string
}

export interface Settings {
  natal_date?: string
  natal_time?: string
  natal_city?: string
  briefing_morning_time?: string
  briefing_evening_time?: string
  readiness_threshold?: string
  oura_token?: string
  gcal_ical_url?: string
}

// User role
export type UserRole = 'anya' | 'den'

export interface AppUser {
  name: string
  role: UserRole
  telegramId?: number
}
