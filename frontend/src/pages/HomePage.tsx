import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Zap, Calendar, Wallet, Activity,
  Stethoscope, Gift, TrendingUp, ChevronRight, Pill, Clock
} from 'lucide-react'
import GlassCard from '../components/GlassCard'
import LoadingSpinner from '../components/LoadingSpinner'
import { dashboardApi, calendarApi, briefingApi } from '../api'
import { useUser } from '../App'

function getGreeting() {
  const h = new Date().getHours()
  if (h < 5)  return 'Ночью'
  if (h < 12) return 'Доброе утро'
  if (h < 17) return 'Добрый день'
  if (h < 22) return 'Добрый вечер'
  return 'Поздний вечер'
}

function formatDate() {
  return new Date().toLocaleDateString('ru-RU', { weekday: 'long', day: 'numeric', month: 'long' })
}

// Медицинские типы встреч — не показываем Дену
const HEALTH_TYPES = new Set(['health', 'medical', 'doctor', 'clinic'])
function isMedical(ev: any) {
  return HEALTH_TYPES.has(ev.meeting_type) || HEALTH_TYPES.has(ev.cognitive_load) || HEALTH_TYPES.has(ev.category)
}

// ─── Главная Ани ──────────────────────────────────────────────────────────────
function AnyaHome({ data }: { data: any }) {
  const navigate = useNavigate()

  const urgentItems: { text: string; onClick?: () => void }[] = []
  if (data) {
    if (!data.state_logged) urgentItems.push({ text: 'Внести состояние сегодня', onClick: () => navigate('/state') })
    if (data.medications_pending > 0) urgentItems.push({
      text: `Таблетки: ${data.medications_pending} ${data.medications_pending === 1 ? 'не принята' : 'не приняты'}`,
      onClick: () => navigate('/health'),
    })
    data.upcoming_birthdays?.forEach((b: any) => {
      if (b.days_until === 0) urgentItems.push({ text: `🎂 Сегодня ДР: ${b.name}`, onClick: () => navigate('/contacts') })
      else if (b.days_until <= 2) urgentItems.push({ text: `🎂 Через ${b.days_until} дн. ДР: ${b.name}`, onClick: () => navigate('/contacts') })
    })
    data.active_reminders?.forEach((r: any) => {
      urgentItems.push({ text: `⏰ ${r.title}`, onClick: () => navigate('/reminders') })
    })
    if (data.next_medical_visit) urgentItems.push({
      text: `🏥 Ближайший визит: ${data.next_medical_visit.specialty} · ${data.next_medical_visit.visit_date}`,
      onClick: () => navigate('/health'),
    })
  }

  return (
    <>
      {/* ⚡ Сейчас важно */}
      {urgentItems.length > 0 && (
        <GlassCard delay={0.05} className="p-4">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-7 h-7 rounded-xl bg-amber-100 flex items-center justify-center">
              <Zap size={14} className="text-amber-500" />
            </div>
            <span className="font-semibold text-gray-800 text-sm">Сейчас важно</span>
          </div>
          <div className="space-y-2">
            {urgentItems.map((item, i) => (
              <button
                key={i}
                onClick={item.onClick}
                className="w-full flex items-start gap-2.5 text-left active:opacity-70 transition-opacity"
              >
                <div className="w-1.5 h-1.5 rounded-full bg-amber-400 mt-1.5 flex-shrink-0" />
                <p className="text-sm text-gray-700">{item.text}</p>
              </button>
            ))}
          </div>
        </GlassCard>
      )}

      {/* Метрики */}
      <button
        className="grid grid-cols-2 gap-3 w-full text-left"
        onClick={() => navigate('/state')}
        aria-label="Открыть состояние"
      >
        <GlassCard delay={0.08} className="p-4">
          <p className="text-xs text-gray-500 font-medium mb-1">Готовность</p>
          <p className="text-4xl font-bold text-gray-900">{data?.state?.readiness_score ?? '—'}</p>
          {data?.state?.readiness_score && (
            <div className="mt-2 h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div className="h-full rounded-full bg-gradient-to-r from-accent to-accent-light" style={{ width: `${data.state.readiness_score}%` }} />
            </div>
          )}
        </GlassCard>
        <GlassCard delay={0.1} className="p-4">
          <p className="text-xs text-gray-500 font-medium mb-1">Энергия</p>
          <p className="text-4xl font-bold text-gray-900">
            {data?.state?.energy_subjective ?? '—'}
            {data?.state?.energy_subjective && <span className="text-lg text-gray-400">/10</span>}
          </p>
          {data?.state?.energy_subjective && (
            <div className="mt-2 h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div className="h-full rounded-full bg-gradient-to-r from-emerald-400 to-emerald-500" style={{ width: `${(data.state.energy_subjective / 10) * 100}%` }} />
            </div>
          )}
        </GlassCard>
      </button>

      {/* Ближайший визит (только Аня) */}
      {data?.next_medical_visit && (
        <GlassCard delay={0.12} className="p-4" onClick={() => navigate('/health')}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-red-50 flex items-center justify-center">
                <Stethoscope size={18} className="text-red-400" />
              </div>
              <div>
                <p className="text-xs text-gray-500">Ближайший визит</p>
                <p className="text-sm font-semibold text-gray-800">{data.next_medical_visit.specialty}</p>
                <p className="text-xs text-gray-500">{data.next_medical_visit.doctor} · {data.next_medical_visit.visit_date}</p>
              </div>
            </div>
            <ChevronRight size={16} className="text-gray-300" />
          </div>
        </GlassCard>
      )}

      {/* Таблетки (только Аня) */}
      {data?.medications_pending > 0 && (
        <GlassCard delay={0.14} className="p-4" onClick={() => navigate('/health')}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-blue-50 flex items-center justify-center">
                <Pill size={18} className="text-blue-400" />
              </div>
              <div>
                <p className="text-xs text-gray-500">Таблетки сегодня</p>
                <p className="text-sm font-semibold text-gray-800">{data.medications_pending} ожидают приёма</p>
              </div>
            </div>
            <ChevronRight size={16} className="text-gray-300" />
          </div>
        </GlassCard>
      )}

      {/* Расходы */}
      <GlassCard delay={0.16} className="p-4" onClick={() => navigate('/finances')}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-emerald-50 flex items-center justify-center">
              <TrendingUp size={18} className="text-emerald-500" />
            </div>
            <div>
              <p className="text-xs text-gray-500">Расходы за месяц</p>
              <p className="text-sm font-semibold text-gray-800">
                {data?.month_expenses ? `${(data.month_expenses / 1000).toFixed(0)} тыс. ₽` : '—'}
              </p>
            </div>
          </div>
          <ChevronRight size={16} className="text-gray-300" />
        </div>
      </GlassCard>

      {/* Именинники */}
      {data?.upcoming_birthdays?.length > 0 && (
        <GlassCard delay={0.18} className="p-4" onClick={() => navigate('/contacts')}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-pink-50 flex items-center justify-center">
                <Gift size={18} className="text-pink-400" />
              </div>
              <div>
                <p className="text-xs text-gray-500">Именинники</p>
                {data.upcoming_birthdays.slice(0, 2).map((b: any, i: number) => (
                  <p key={i} className="text-sm font-semibold text-gray-800">
                    {b.name} {b.days_until === 0 ? '— сегодня! 🎉' : `— через ${b.days_until} дн.`}
                  </p>
                ))}
              </div>
            </div>
            <ChevronRight size={16} className="text-gray-300" />
          </div>
        </GlassCard>
      )}
    </>
  )
}

// ─── Главная Дена ─────────────────────────────────────────────────────────────
function DenHome({ data }: { data: any }) {
  const navigate = useNavigate()
  const [todayEvents, setTodayEvents] = useState<any[]>([])
  const [priorities, setPriorities] = useState<string[]>([])

  useEffect(() => {
    // Расписание дня (только не-медицинские)
    calendarApi.getToday()
      .then(evs => setTodayEvents(evs.filter((e: any) => !isMedical(e))))
      .catch(() => {})

    // Приоритеты из брифинга (немедицинские — берём из morning briefing)
    briefingApi.getToday()
      .then(briefings => {
        const morning = briefings.find((b: any) => b.briefing_type === 'morning')
        const raw: string[] = morning?.content?.priorities ?? []
        // Фильтруем любые строки с медицинскими ключевыми словами
        const MEDICAL_KW = /таблет|витамин|врач|визит|анализ|укол|лекарств|клиник|больниц/i
        setPriorities(raw.filter((p: string) => !MEDICAL_KW.test(p)))
      })
      .catch(() => {})
  }, [])

  return (
    <>
      {/* Метрики — Готовность + Энергия (Дену оставляем) */}
      <button
        className="grid grid-cols-2 gap-3 w-full text-left"
        onClick={() => navigate('/state')}
        aria-label="Открыть состояние"
      >
        <GlassCard delay={0.05} className="p-4">
          <p className="text-xs text-gray-500 font-medium mb-1">Готовность</p>
          <p className="text-4xl font-bold text-gray-900">{data?.state?.readiness_score ?? '—'}</p>
          {data?.state?.readiness_score && (
            <div className="mt-2 h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div className="h-full rounded-full bg-gradient-to-r from-accent to-accent-light" style={{ width: `${data.state.readiness_score}%` }} />
            </div>
          )}
        </GlassCard>
        <GlassCard delay={0.07} className="p-4">
          <p className="text-xs text-gray-500 font-medium mb-1">Энергия</p>
          <p className="text-4xl font-bold text-gray-900">
            {data?.state?.energy_subjective ?? '—'}
            {data?.state?.energy_subjective && <span className="text-lg text-gray-400">/10</span>}
          </p>
          {data?.state?.energy_subjective && (
            <div className="mt-2 h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div className="h-full rounded-full bg-gradient-to-r from-emerald-400 to-emerald-500" style={{ width: `${(data.state.energy_subjective / 10) * 100}%` }} />
            </div>
          )}
        </GlassCard>
      </button>

      {/* Расписание дня */}
      {todayEvents.length > 0 && (
        <GlassCard delay={0.1} className="p-4" onClick={() => navigate('/calendar')}>
          <div className="flex items-center gap-2 mb-3">
            <div className="w-7 h-7 rounded-xl bg-blue-50 flex items-center justify-center">
              <Calendar size={14} className="text-blue-500" />
            </div>
            <span className="font-semibold text-gray-800 text-sm">Расписание дня</span>
            <ChevronRight size={14} className="text-gray-300 ml-auto" />
          </div>
          <div className="space-y-2">
            {todayEvents.slice(0, 4).map((ev: any, i: number) => (
              <div key={ev.id ?? i} className="flex items-start gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-blue-400 mt-1.5 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-800 truncate">{ev.title}</p>
                  {ev.start_time && (
                    <p className="text-xs text-gray-400 flex items-center gap-1 mt-0.5">
                      <Clock size={10} /> {ev.start_time}{ev.end_time ? `–${ev.end_time}` : ''}
                    </p>
                  )}
                </div>
              </div>
            ))}
            {todayEvents.length > 4 && (
              <p className="text-xs text-gray-400 pl-4">+ ещё {todayEvents.length - 4}</p>
            )}
          </div>
        </GlassCard>
      )}

      {/* Приоритеты дня (из брифа, немедицинские) */}
      {priorities.length > 0 && (
        <GlassCard delay={0.12} className="p-4">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-7 h-7 rounded-xl bg-amber-100 flex items-center justify-center">
              <Zap size={14} className="text-amber-500" />
            </div>
            <span className="font-semibold text-gray-800 text-sm">Приоритеты дня</span>
          </div>
          <div className="space-y-2">
            {priorities.slice(0, 4).map((p, i) => (
              <div key={i} className="flex items-start gap-2.5">
                <div className="w-1.5 h-1.5 rounded-full bg-amber-400 mt-1.5 flex-shrink-0" />
                <p className="text-sm text-gray-700">{p}</p>
              </div>
            ))}
          </div>
        </GlassCard>
      )}

      {/* Финансы — короткий статус */}
      <GlassCard delay={0.14} className="p-4" onClick={() => navigate('/finances')}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-emerald-50 flex items-center justify-center">
              <Wallet size={18} className="text-emerald-500" />
            </div>
            <div>
              <p className="text-xs text-gray-500">Расходы за месяц</p>
              <p className="text-sm font-semibold text-gray-800">
                {data?.month_expenses ? `${(data.month_expenses / 1000).toFixed(0)} тыс. ₽` : '—'}
              </p>
            </div>
          </div>
          <ChevronRight size={16} className="text-gray-300" />
        </div>
      </GlassCard>

      {/* Именинники */}
      {data?.upcoming_birthdays?.length > 0 && (
        <GlassCard delay={0.16} className="p-4" onClick={() => navigate('/contacts')}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-pink-50 flex items-center justify-center">
                <Gift size={18} className="text-pink-400" />
              </div>
              <div>
                <p className="text-xs text-gray-500">Именинники</p>
                {data.upcoming_birthdays.slice(0, 2).map((b: any, i: number) => (
                  <p key={i} className="text-sm font-semibold text-gray-800">
                    {b.name} {b.days_until === 0 ? '— сегодня! 🎉' : `— через ${b.days_until} дн.`}
                  </p>
                ))}
              </div>
            </div>
            <ChevronRight size={16} className="text-gray-300" />
          </div>
        </GlassCard>
      )}

      {/* Кнопка к состоянию (для чтения) */}
      <GlassCard delay={0.18} className="p-4" onClick={() => navigate('/state')}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-violet-50 flex items-center justify-center">
              <Activity size={18} className="text-violet-500" />
            </div>
            <div>
              <p className="text-xs text-gray-500">Данные Ани</p>
              <p className="text-sm font-semibold text-gray-800">Сон, тренировка, алкоголь</p>
            </div>
          </div>
          <ChevronRight size={16} className="text-gray-300" />
        </div>
      </GlassCard>
    </>
  )
}

// ─── Корневой компонент ───────────────────────────────────────────────────────
export default function HomePage() {
  const { role, name } = useUser()
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    dashboardApi.get()
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) return (
    <div className="px-4 pt-6">
      <LoadingSpinner text="Загружаем дашборд..." />
    </div>
  )

  return (
    <div className="page-scroll h-full overflow-y-auto">
      <div className="px-4 pt-6 pb-4 space-y-4">

        {/* Header */}
        <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
          <p className="text-sm text-gray-500 font-medium capitalize">{getGreeting()}</p>
          <h1 className="text-2xl font-bold text-gray-900">{name} 👋</h1>
          <p className="text-sm text-gray-400 mt-0.5 capitalize">{formatDate()}</p>
        </motion.div>

        {role === 'anya' ? <AnyaHome data={data} /> : <DenHome data={data} />}

        <div className="h-4" />
      </div>
    </div>
  )
}
