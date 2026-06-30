import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  AreaChart, Area, ResponsiveContainer, Tooltip,
  PieChart, Pie, Cell,
} from 'recharts'
import {
  Zap, Calendar, Wallet, Activity,
  Stethoscope, Gift, ChevronRight, Pill, Clock, Moon, Dumbbell
} from 'lucide-react'
import GlassCard from '../components/GlassCard'
import LoadingSpinner from '../components/LoadingSpinner'
import { dashboardApi, calendarApi, briefingApi, stateApi } from '../api'
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

const HEALTH_TYPES = new Set(['health', 'medical', 'doctor', 'clinic'])
function isMedical(ev: any) {
  return HEALTH_TYPES.has(ev.meeting_type) || HEALTH_TYPES.has(ev.cognitive_load) || HEALTH_TYPES.has(ev.category)
}

// ─── Radial Ring ──────────────────────────────────────────────────────────────
function RadialRing({
  value, max = 100, size = 88, stroke = 9,
  color, trackColor = 'rgba(0,0,0,0.07)',
  label, sublabel, children
}: {
  value: number | null; max?: number; size?: number; stroke?: number;
  color: string; trackColor?: string;
  label?: string; sublabel?: string; children?: React.ReactNode
}) {
  const r = (size - stroke) / 2
  const circ = 2 * Math.PI * r
  const pct = value != null ? Math.min(value / max, 1) : 0
  const offset = circ * (1 - pct)

  return (
    <div className="flex flex-col items-center gap-1.5">
      <div style={{ width: size, height: size, position: 'relative' }}>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
          {/* Track */}
          <circle cx={size/2} cy={size/2} r={r} fill="none"
            stroke={trackColor} strokeWidth={stroke} strokeLinecap="round" />
          {/* Arc */}
          {value != null && (
            <motion.circle
              cx={size/2} cy={size/2} r={r} fill="none"
              stroke={color} strokeWidth={stroke} strokeLinecap="round"
              strokeDasharray={circ}
              initial={{ strokeDashoffset: circ }}
              animate={{ strokeDashoffset: offset }}
              transition={{ duration: 1.1, ease: [0.4, 0, 0.2, 1] }}
              style={{ transform: 'rotate(-90deg)', transformOrigin: 'center' }}
            />
          )}
        </svg>
        {/* Center content */}
        <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
          {children ?? (
            <>
              <span style={{ fontSize: 20, fontWeight: 800, color: '#1a1a2e', lineHeight: 1 }}>
                {value ?? '—'}
              </span>
              {sublabel && <span style={{ fontSize: 9, color: '#9ca3af', fontWeight: 600, marginTop: 1 }}>{sublabel}</span>}
            </>
          )}
        </div>
      </div>
      {label && <span style={{ fontSize: 11, fontWeight: 600, color: '#6b7280' }}>{label}</span>}
    </div>
  )
}

// ─── Sparkline Card ───────────────────────────────────────────────────────────
function WeekSparkline({ history }: { history: any[] }) {
  if (!history.length) return null
  const data = [...history].reverse().map(d => ({
    day: new Date(d.state_date).toLocaleDateString('ru-RU', { weekday: 'short' }),
    Готовность: d.readiness_score ?? 0,
    Энергия: d.energy_subjective ? d.energy_subjective * 10 : 0,
  }))

  return (
    <div style={{ height: 60, width: '100%' }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 4, right: 4, left: 4, bottom: 0 }}>
          <defs>
            <linearGradient id="gReady" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#5B9DB8" stopOpacity={0.35}/>
              <stop offset="95%" stopColor="#5B9DB8" stopOpacity={0}/>
            </linearGradient>
            <linearGradient id="gEnergy" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#34d399" stopOpacity={0.3}/>
              <stop offset="95%" stopColor="#34d399" stopOpacity={0}/>
            </linearGradient>
          </defs>
          <Tooltip
            contentStyle={{ background: 'rgba(255,255,255,0.92)', border: '1px solid rgba(255,255,255,0.8)', borderRadius: 12, fontSize: 11, backdropFilter: 'blur(12px)' }}
            labelStyle={{ fontWeight: 700, color: '#1a1a2e', fontSize: 11 }}
            itemStyle={{ fontSize: 11 }}
          />
          <Area type="monotone" dataKey="Готовность" stroke="#5B9DB8" strokeWidth={2} fill="url(#gReady)" dot={false} />
          <Area type="monotone" dataKey="Энергия" stroke="#34d399" strokeWidth={2} fill="url(#gEnergy)" dot={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

// ─── Finance Mini Donut ───────────────────────────────────────────────────────
const DONUT_COLORS = ['#5B9DB8', '#34d399', '#f59e0b', '#f87171', '#a78bfa', '#fb7185']

function FinanceDonut({ byCategory }: { byCategory: any[] }) {
  if (!byCategory?.length) return null
  const data = byCategory.slice(0, 5).map(c => ({ name: c.category, value: c.total }))
  return (
    <PieChart width={64} height={64}>
      <Pie data={data} cx={28} cy={28} innerRadius={18} outerRadius={28}
        dataKey="value" startAngle={90} endAngle={-270} stroke="none">
        {data.map((_, i) => <Cell key={i} fill={DONUT_COLORS[i % DONUT_COLORS.length]} />)}
      </Pie>
    </PieChart>
  )
}

// ─── Главная Ани ──────────────────────────────────────────────────────────────
function AnyaHome({ data, history }: { data: any; history: any[] }) {
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
    if (data.next_medical_visit) urgentItems.push({
      text: `🏥 Ближайший визит: ${data.next_medical_visit.specialty} · ${data.next_medical_visit.visit_date}`,
      onClick: () => navigate('/health'),
    })
  }

  const state = data?.state
  const readiness = state?.readiness_score ?? null
  const energy = state?.energy_subjective ?? null
  const sleep = state?.sleep_score ?? null

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
              <button key={i} onClick={item.onClick}
                className="w-full flex items-start gap-2.5 text-left active:opacity-70 transition-opacity">
                <div className="w-1.5 h-1.5 rounded-full bg-amber-400 mt-1.5 flex-shrink-0" />
                <p className="text-sm text-gray-700">{item.text}</p>
              </button>
            ))}
          </div>
        </GlassCard>
      )}

      {/* Витальные кольца */}
      <GlassCard delay={0.08} className="p-4" onClick={() => navigate('/state')}>
        <div className="flex items-center justify-between mb-3">
          <span className="font-semibold text-gray-800 text-sm">Состояние сегодня</span>
          <ChevronRight size={14} className="text-gray-300" />
        </div>
        <div className="flex justify-around">
          <RadialRing value={readiness} max={100} color="#5B9DB8" label="Готовность" sublabel="%" size={84} stroke={8} />
          <RadialRing value={energy} max={10} color="#34d399" label="Энергия" sublabel="/10" size={84} stroke={8} />
          <RadialRing value={sleep} max={100} color="#a78bfa" label="Сон" sublabel="%" size={84} stroke={8}>
            {sleep != null ? (
              <>
                <Moon size={13} color="#a78bfa" />
                <span style={{ fontSize: 17, fontWeight: 800, color: '#1a1a2e', lineHeight: 1, marginTop: 2 }}>{sleep}</span>
              </>
            ) : (
              <span style={{ fontSize: 18, fontWeight: 700, color: '#d1d5db' }}>—</span>
            )}
          </RadialRing>
        </div>

        {/* Дополнительные флаги */}
        <div className="flex gap-2 mt-4 justify-center">
          {[
            { label: 'Тренировка', done: state?.workout_done, icon: <Dumbbell size={11} /> },
            { label: 'Алкоголь', done: state?.alcohol ? false : null, icon: null },
          ].map((item, i) => (
            item.done !== undefined && item.done !== null ? (
              <div key={i} className={`flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold ${
                item.done ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-400'
              }`}>
                {item.icon}
                {item.label}
              </div>
            ) : null
          ))}
        </div>
      </GlassCard>

      {/* Спарклайн истории */}
      {history.length > 1 && (
        <GlassCard delay={0.11} className="p-4">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-7 h-7 rounded-xl bg-blue-50 flex items-center justify-center">
              <Activity size={14} className="text-blue-500" />
            </div>
            <span className="font-semibold text-gray-800 text-sm">Динамика за неделю</span>
            <div className="ml-auto flex gap-3 text-xs text-gray-400">
              <span className="flex items-center gap-1"><span className="inline-block w-2 h-2 rounded-full bg-[#5B9DB8]" />Готовность</span>
              <span className="flex items-center gap-1"><span className="inline-block w-2 h-2 rounded-full bg-emerald-400" />Энергия</span>
            </div>
          </div>
          <WeekSparkline history={history} />
        </GlassCard>
      )}

      {/* Таблетки */}
      {data?.medications_total > 0 && (
        <GlassCard delay={0.13} className="p-4" onClick={() => navigate('/health')}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-blue-50 flex items-center justify-center">
                <Pill size={18} className="text-blue-400" />
              </div>
              <div>
                <p className="text-xs text-gray-500">Таблетки сегодня</p>
                <p className="text-sm font-semibold text-gray-800">
                  {(data.medications_total - (data.medications_pending ?? 0))} из {data.medications_total} приняты
                </p>
              </div>
            </div>
            <div className="flex flex-col items-end gap-1">
              <div className="flex gap-1">
                {Array.from({ length: data.medications_total }).map((_,i) => (
                  <div key={i} className={`w-2.5 h-2.5 rounded-full ${i < (data.medications_total - data.medications_pending) ? 'bg-blue-400' : 'bg-gray-200'}`} />
                ))}
              </div>
              <ChevronRight size={14} className="text-gray-300" />
            </div>
          </div>
        </GlassCard>
      )}

      {/* Ближайший визит */}
      {data?.next_medical_visit && (
        <GlassCard delay={0.15} className="p-4" onClick={() => navigate('/health')}>
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

      {/* Именинники */}
      {data?.upcoming_birthdays?.length > 0 && (
        <GlassCard delay={0.17} className="p-4" onClick={() => navigate('/contacts')}>
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
function DenHome({ data, history }: { data: any; history: any[] }) {
  const navigate = useNavigate()
  const [todayEvents, setTodayEvents] = useState<any[]>([])
  const [priorities, setPriorities] = useState<string[]>([])
  const [finances, setFinances] = useState<any>(null)

  useEffect(() => {
    calendarApi.getToday()
      .then(evs => setTodayEvents(evs.filter((e: any) => !isMedical(e))))
      .catch(() => {})

    briefingApi.getToday()
      .then(briefings => {
        const morning = briefings.find((b: any) => b.briefing_type === 'morning')
        const raw: string[] = morning?.content?.priorities ?? []
        const MEDICAL_KW = /таблет|витамин|врач|визит|анализ|укол|лекарств|клиник|больниц/i
        setPriorities(raw.filter((p: string) => !MEDICAL_KW.test(p)))
      })
      .catch(() => {})

    import('../api').then(({ financesApi }) =>
      financesApi.getSummary().then(setFinances).catch(() => {})
    )
  }, [])

  const state = data?.state
  const readiness = state?.readiness_score ?? null
  const energy = state?.energy_subjective ?? null

  return (
    <>
      {/* Витальные кольца */}
      <GlassCard delay={0.05} className="p-4" onClick={() => navigate('/state')}>
        <div className="flex items-center justify-between mb-3">
          <div>
            <span className="font-semibold text-gray-800 text-sm">Моё состояние</span>
            <p className="text-[10px] text-gray-400 mt-0.5">ведёт Аня</p>
          </div>
          <ChevronRight size={14} className="text-gray-300" />
        </div>
        <div className="flex justify-around">
          <RadialRing value={readiness} max={100} color="#5B9DB8" label="Готовность" sublabel="%" size={84} stroke={8} />
          <RadialRing value={energy} max={10} color="#34d399" label="Энергия" sublabel="/10" size={84} stroke={8} />
          <div className="flex flex-col items-center gap-1.5">
            <div className="w-[84px] h-[84px] flex flex-col items-center justify-center rounded-full bg-gradient-to-br from-amber-50 to-amber-100 border-2 border-amber-200">
              <Dumbbell size={18} className={state?.workout_done ? 'text-amber-500' : 'text-gray-300'} />
              <span className="text-xs font-bold mt-1" style={{ color: state?.workout_done ? '#d97706' : '#d1d5db' }}>
                {state?.workout_done ? 'Да' : 'Нет'}
              </span>
            </div>
            <span className="text-xs font-semibold text-gray-500">Тренировка</span>
          </div>
        </div>
      </GlassCard>

      {/* Спарклайн */}
      {history.length > 1 && (
        <GlassCard delay={0.08} className="p-4">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-7 h-7 rounded-xl bg-blue-50 flex items-center justify-center">
              <Activity size={14} className="text-blue-500" />
            </div>
            <span className="font-semibold text-gray-800 text-sm">Динамика за неделю</span>
            <div className="ml-auto flex gap-3 text-xs text-gray-400">
              <span className="flex items-center gap-1"><span className="inline-block w-2 h-2 rounded-full bg-[#5B9DB8]" />Готовность</span>
              <span className="flex items-center gap-1"><span className="inline-block w-2 h-2 rounded-full bg-emerald-400" />Энергия</span>
            </div>
          </div>
          <WeekSparkline history={history} />
        </GlassCard>
      )}

      {/* Расписание дня */}
      {todayEvents.length > 0 && (
        <GlassCard delay={0.10} className="p-4" onClick={() => navigate('/calendar')}>
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
          </div>
        </GlassCard>
      )}

      {/* Приоритеты */}
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

      {/* Финансы с донатом */}
      <GlassCard delay={0.14} className="p-4" onClick={() => navigate('/finances')}>
        <div className="flex items-center gap-3">
          <div className="flex-shrink-0">
            {finances?.by_category?.length
              ? <FinanceDonut byCategory={finances.by_category} />
              : <div className="w-10 h-10 rounded-2xl bg-emerald-50 flex items-center justify-center"><Wallet size={18} className="text-emerald-500" /></div>
            }
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs text-gray-500">Расходы за месяц</p>
            <p className="text-base font-bold text-gray-900">
              {finances?.month_expenses != null ? `${(finances.month_expenses / 1000).toFixed(0)} тыс. ₽` : data?.month_expenses ? `${(data.month_expenses / 1000).toFixed(0)} тыс. ₽` : '—'}
            </p>
            {finances?.by_category?.slice(0, 2).map((c: any, i: number) => (
              <p key={i} className="text-xs text-gray-400 truncate">
                <span style={{ color: DONUT_COLORS[i] }}>●</span> {c.category}: {(c.total / 1000).toFixed(0)}к
              </p>
            ))}
          </div>
          <ChevronRight size={16} className="text-gray-300 flex-shrink-0" />
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
    </>
  )
}

// ─── Корневой компонент ───────────────────────────────────────────────────────
export default function HomePage() {
  const { role, name } = useUser()
  const [data, setData] = useState<any>(null)
  const [history, setHistory] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      dashboardApi.get().catch(() => null),
      stateApi.getHistory(7).catch(() => []),
    ]).then(([dash, hist]) => {
      setData(dash)
      setHistory(hist ?? [])
    }).finally(() => setLoading(false))
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

        {role === 'anya'
          ? <AnyaHome data={data} history={history} />
          : <DenHome data={data} history={history} />
        }

        <div className="h-4" />
      </div>
    </div>
  )
}
