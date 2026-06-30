import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  AreaChart, Area, ResponsiveContainer, Tooltip,
  PieChart, Pie, Cell,
} from 'recharts'
import {
  Zap, Calendar, Wallet, Activity,
  Gift, ChevronRight, Pill, Clock, Moon, Dumbbell,
  Bell, Stethoscope, X, Plus, Mic, Users,
  CheckCircle2, Circle, TrendingDown, Star, ChevronDown, ChevronUp
} from 'lucide-react'
import GlassCard from '../components/GlassCard'
import LoadingSpinner from '../components/LoadingSpinner'
import { dashboardApi, calendarApi, briefingApi, stateApi, healthApi, remindersApi, financesApi } from '../api'
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

function haptic(s: 'light' | 'medium' = 'light') {
  window.Telegram?.WebApp?.HapticFeedback?.impactOccurred(s)
}

// ─── Types ────────────────────────────────────────────────────────────────────
interface FeedItem {
  id: string
  type: 'medication' | 'reminder' | 'visit' | 'birthday'
  title: string
  subtitle?: string
  urgent?: boolean
  onDone?: () => Promise<void> | void
}

interface RecoCard {
  id: string
  icon: string
  title: string
  action: string
  detail?: string
  color: 'amber' | 'green' | 'blue' | 'pink'
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
          <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={trackColor} strokeWidth={stroke} strokeLinecap="round" />
          {value != null && (
            <motion.circle cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth={stroke} strokeLinecap="round"
              strokeDasharray={circ} initial={{ strokeDashoffset: circ }} animate={{ strokeDashoffset: offset }}
              transition={{ duration: 1.1, ease: [0.4, 0, 0.2, 1] }} style={{ transform: 'rotate(-90deg)', transformOrigin: 'center' }} />
          )}
        </svg>
        <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
          {children ?? (
            <>
              <span style={{ fontSize: 20, fontWeight: 800, color: '#1a1a2e', lineHeight: 1 }}>{value ?? '—'}</span>
              {sublabel && <span style={{ fontSize: 9, color: '#9ca3af', fontWeight: 600, marginTop: 1 }}>{sublabel}</span>}
            </>
          )}
        </div>
      </div>
      {label && <span style={{ fontSize: 11, fontWeight: 600, color: '#6b7280' }}>{label}</span>}
    </div>
  )
}

// ─── Sparkline ────────────────────────────────────────────────────────────────
function WeekSparkline({ history }: { history: any[] }) {
  if (!history.length) return null
  const data = [...history].reverse().map(d => ({
    day: new Date(d.date ?? d.state_date).toLocaleDateString('ru-RU', { weekday: 'short' }),
    Готовность: d.readiness_score ?? 0,
    Энергия: d.energy_subjective ? d.energy_subjective * 10 : 0,
  }))
  return (
    <div style={{ height: 60, width: '100%' }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 4, right: 4, left: 4, bottom: 0 }}>
          <defs>
            <linearGradient id="gReady" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#5B9DB8" stopOpacity={0.35}/><stop offset="95%" stopColor="#5B9DB8" stopOpacity={0}/>
            </linearGradient>
            <linearGradient id="gEnergy" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#34d399" stopOpacity={0.3}/><stop offset="95%" stopColor="#34d399" stopOpacity={0}/>
            </linearGradient>
          </defs>
          <Tooltip contentStyle={{ background: 'rgba(255,255,255,0.92)', border: '1px solid rgba(255,255,255,0.8)', borderRadius: 12, fontSize: 11, backdropFilter: 'blur(12px)' }}
            labelStyle={{ fontWeight: 700, color: '#1a1a2e', fontSize: 11 }} itemStyle={{ fontSize: 11 }} />
          <Area type="monotone" dataKey="Готовность" stroke="#5B9DB8" strokeWidth={2} fill="url(#gReady)" dot={false} />
          <Area type="monotone" dataKey="Энергия" stroke="#34d399" strokeWidth={2} fill="url(#gEnergy)" dot={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

// ─── Finance Donut ────────────────────────────────────────────────────────────
const DONUT_COLORS = ['#5B9DB8', '#34d399', '#f59e0b', '#f87171', '#a78bfa', '#fb7185']
function FinanceDonut({ byCategory }: { byCategory: any[] }) {
  if (!byCategory?.length) return null
  const data = byCategory.slice(0, 5).map(c => ({ name: c.category, value: c.total }))
  return (
    <PieChart width={64} height={64}>
      <Pie data={data} cx={28} cy={28} innerRadius={18} outerRadius={28} dataKey="value" startAngle={90} endAngle={-270} stroke="none">
        {data.map((_, i) => <Cell key={i} fill={DONUT_COLORS[i % DONUT_COLORS.length]} />)}
      </Pie>
    </PieChart>
  )
}

// ─── Recommendation Card ──────────────────────────────────────────────────────
const RECO_STYLES: Record<string, { bg: string; border: string; iconBg: string; text: string }> = {
  amber: { bg: 'bg-amber-50/80',  border: 'border-amber-200/60', iconBg: 'bg-amber-100', text: 'text-amber-700' },
  green: { bg: 'bg-emerald-50/80', border: 'border-emerald-200/60', iconBg: 'bg-emerald-100', text: 'text-emerald-700' },
  blue:  { bg: 'bg-blue-50/80',   border: 'border-blue-200/60', iconBg: 'bg-blue-100', text: 'text-blue-700' },
  pink:  { bg: 'bg-pink-50/80',   border: 'border-pink-200/60', iconBg: 'bg-pink-100', text: 'text-pink-700' },
}

function RecoCardItem({ card, delay }: { card: RecoCard; delay: number }) {
  const [expanded, setExpanded] = useState(false)
  const s = RECO_STYLES[card.color]
  return (
    <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay, duration: 0.3 }}>
      <button onClick={() => { haptic(); setExpanded(e => !e) }}
        className={`w-full text-left rounded-2xl border p-3.5 transition-all ${s.bg} ${s.border}`}>
        <div className="flex items-start gap-3">
          <div className={`w-8 h-8 rounded-xl flex items-center justify-center text-base flex-shrink-0 ${s.iconBg}`}>
            {card.icon}
          </div>
          <div className="flex-1 min-w-0">
            <p className={`text-xs font-semibold ${s.text}`}>{card.title}</p>
            <p className="text-sm text-gray-700 mt-0.5">{card.action}</p>
            <AnimatePresence>
              {expanded && card.detail && (
                <motion.p initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}
                  className="text-xs text-gray-500 mt-1.5 leading-relaxed">
                  {card.detail}
                </motion.p>
              )}
            </AnimatePresence>
          </div>
          <div className="flex-shrink-0 mt-0.5">
            {expanded ? <ChevronUp size={13} className="text-gray-400" /> : <ChevronDown size={13} className="text-gray-400" />}
          </div>
        </div>
      </button>
    </motion.div>
  )
}

// ─── Quick Add Sheet ───────────────────────────────────────────────────────────
type QuickView = 'menu' | 'expense' | 'task'
const EXPENSE_CATS = ['Еда', 'Транспорт', 'Рестораны', 'Здоровье', 'Образование', 'Развлечения', 'Другое']

function QuickAddSheet({ open, onClose, onDone }: { open: boolean; onClose: () => void; onDone?: () => void }) {
  const navigate = useNavigate()
  const [view, setView] = useState<QuickView>('menu')
  const [taskText, setTaskText] = useState('')
  const [amount, setAmount] = useState('')
  const [cat, setCat] = useState('Еда')
  const [desc, setDesc] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => { if (!open) { setView('menu'); setTaskText(''); setAmount(''); setDesc('') } }, [open])

  const go = (path: string) => { onClose(); navigate(path) }

  const saveExpense = async () => {
    if (!amount) return
    setSaving(true)
    haptic('medium')
    try {
      await financesApi.addExpense({ amount: parseFloat(amount), category: cat, description: desc || cat })
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success')
      onClose(); onDone?.()
    } finally { setSaving(false) }
  }

  const saveTask = async () => {
    if (!taskText.trim()) return
    setSaving(true)
    haptic('medium')
    try {
      const tomorrow = new Date(); tomorrow.setDate(tomorrow.getDate() + 1)
      await remindersApi.add({ title: taskText.trim(), due_at: `${tomorrow.toISOString().slice(0,10)} 09:00:00` })
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success')
      onClose(); onDone?.()
    } finally { setSaving(false) }
  }

  const MENU_ITEMS = [
    { emoji: '🎙', label: 'Встреча',    action: () => go('/meetings')  },
    { emoji: '👤', label: 'Контакт',   action: () => go('/contacts')  },
    { emoji: '💸', label: 'Расход',    action: () => setView('expense') },
    { emoji: '🧠', label: 'Состояние', action: () => go('/state')     },
    { emoji: '🔬', label: 'Анализ',    action: () => go('/health')    },
    { emoji: '💊', label: 'Лекарство', action: () => go('/health')    },
    { emoji: '✅', label: 'Задача',    action: () => setView('task')  },
    { emoji: '🗓', label: 'Напомни',   action: () => go('/reminders') },
  ]

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div className="fixed inset-0 bg-black/30 z-40 backdrop-blur-sm"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={onClose} />
          <motion.div className="fixed bottom-0 left-0 right-0 z-50 bg-white rounded-t-3xl shadow-2xl"
            style={{ maxWidth: 430, margin: '0 auto' }}
            initial={{ y: '100%' }} animate={{ y: 0 }} exit={{ y: '100%' }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}>
            {/* Handle */}
            <div className="flex justify-center pt-3 pb-1">
              <div className="w-10 h-1 bg-gray-200 rounded-full" />
            </div>
            <div className="flex items-center justify-between px-5 pt-2 pb-3">
              <span className="text-base font-semibold text-gray-800">
                {view === 'menu' ? '+ Добавить' : view === 'expense' ? '💸 Расход' : '✅ Задача'}
              </span>
              <button onClick={view === 'menu' ? onClose : () => setView('menu')}
                className="w-8 h-8 flex items-center justify-center rounded-full bg-gray-100">
                <X size={16} className="text-gray-500" />
              </button>
            </div>

            {view === 'menu' && (
              <div className="grid grid-cols-4 gap-2 px-4 pb-8"
                style={{ paddingBottom: `max(32px, calc(env(safe-area-inset-bottom, 0px) + 24px))` }}>
                {MENU_ITEMS.map((item) => (
                  <button key={item.label} onClick={() => { haptic(); item.action() }}
                    className="flex flex-col items-center gap-2 p-3 rounded-2xl hover:bg-gray-50 active:bg-gray-100 active:scale-95 transition-all">
                    <div className="w-12 h-12 rounded-2xl bg-gray-100 flex items-center justify-center text-2xl">
                      {item.emoji}
                    </div>
                    <span className="text-[11px] font-medium text-gray-600 text-center leading-tight">{item.label}</span>
                  </button>
                ))}
              </div>
            )}

            {view === 'expense' && (
              <div className="px-4 pb-8 space-y-3" style={{ paddingBottom: `max(32px, calc(env(safe-area-inset-bottom, 0px) + 24px))` }}>
                <input type="number" inputMode="numeric" placeholder="Сумма, ₽"
                  className="w-full bg-gray-50 rounded-xl px-4 py-3 text-lg font-semibold outline-none border border-gray-200 focus:border-[#5B9DB8]"
                  value={amount} onChange={e => setAmount(e.target.value)} autoFocus />
                <div className="flex gap-2 flex-wrap">
                  {EXPENSE_CATS.map(c => (
                    <button key={c} onClick={() => setCat(c)}
                      className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all ${cat === c ? 'bg-[#5B9DB8] text-white' : 'bg-gray-100 text-gray-600'}`}>
                      {c}
                    </button>
                  ))}
                </div>
                <input placeholder="Описание (необязательно)"
                  className="w-full bg-gray-50 rounded-xl px-4 py-3 text-sm outline-none border border-gray-200 focus:border-[#5B9DB8]"
                  value={desc} onChange={e => setDesc(e.target.value)} />
                <button onClick={saveExpense} disabled={!amount || saving}
                  className="w-full py-3.5 rounded-xl font-semibold text-sm text-white transition-all disabled:opacity-50"
                  style={{ background: 'linear-gradient(135deg, #5B9DB8, #4a8aa5)' }}>
                  {saving ? 'Сохраняем...' : 'Сохранить расход'}
                </button>
              </div>
            )}

            {view === 'task' && (
              <div className="px-4 pb-8 space-y-3" style={{ paddingBottom: `max(32px, calc(env(safe-area-inset-bottom, 0px) + 24px))` }}>
                <input placeholder="Что нужно сделать?"
                  className="w-full bg-gray-50 rounded-xl px-4 py-3 text-sm outline-none border border-gray-200 focus:border-[#5B9DB8]"
                  value={taskText} onChange={e => setTaskText(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && saveTask()} autoFocus />
                <p className="text-xs text-gray-400 px-1">Задача появится в ленте «Сейчас важно» завтра в 09:00</p>
                <button onClick={saveTask} disabled={!taskText.trim() || saving}
                  className="w-full py-3.5 rounded-xl font-semibold text-sm text-white transition-all disabled:opacity-50"
                  style={{ background: 'linear-gradient(135deg, #5B9DB8, #4a8aa5)' }}>
                  {saving ? 'Сохраняем...' : 'Добавить задачу'}
                </button>
              </div>
            )}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}

// ─── Unified Action Feed ───────────────────────────────────────────────────────
const FEED_ICON_STYLES: Record<string, string> = {
  medication: 'bg-blue-50 text-blue-400',
  reminder:   'bg-purple-50 text-purple-400',
  visit:      'bg-red-50 text-red-400',
  birthday:   'bg-pink-50 text-pink-400',
}
const FEED_ICONS: Record<string, any> = {
  medication: Pill, reminder: Bell, visit: Stethoscope, birthday: Gift,
}

function ActionFeed({ items, onCheck }: { items: FeedItem[]; onCheck: (id: string, cb?: () => Promise<void> | void) => void }) {
  const [done, setDone] = useState<Set<string>>(new Set())

  const active = items.filter(i => !done.has(i.id))
  const completed = items.filter(i => done.has(i.id))

  const handleCheck = async (item: FeedItem) => {
    haptic('medium')
    setDone(prev => new Set([...prev, item.id]))
    window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success')
    try { if (item.onDone) await item.onDone() } catch { /* already marked done visually */ }
  }

  if (items.length === 0) return (
    <div className="flex flex-col items-center justify-center py-6 gap-2">
      <div className="w-10 h-10 rounded-full bg-emerald-50 flex items-center justify-center">
        <CheckCircle2 size={20} className="text-emerald-500" />
      </div>
      <p className="text-sm text-gray-400">Всё сделано!</p>
    </div>
  )

  return (
    <div className="space-y-2">
      {active.map((item, i) => {
        const Icon = FEED_ICONS[item.type] || Bell
        const iconStyle = FEED_ICON_STYLES[item.type]
        return (
          <motion.div key={item.id} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.04 }}
            layout exit={{ opacity: 0, x: 20, height: 0 }}>
            <div className={`flex items-center gap-3 py-2.5 px-1 rounded-xl ${item.urgent ? 'bg-amber-50/50' : ''}`}>
              <div className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 ${iconStyle}`}>
                <Icon size={14} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5">
                  <p className="text-sm text-gray-800 truncate">{item.title}</p>
                  {item.urgent && <span className="text-amber-500 text-xs">⚡</span>}
                </div>
                {item.subtitle && <p className="text-xs text-gray-400 mt-0.5">{item.subtitle}</p>}
              </div>
              <button onClick={() => handleCheck(item)}
                className="w-7 h-7 rounded-full border-2 border-gray-200 flex items-center justify-center flex-shrink-0 active:scale-90 transition-all hover:border-emerald-400">
                <Circle size={12} className="text-gray-300" />
              </button>
            </div>
          </motion.div>
        )
      })}

      {completed.length > 0 && (
        <div className="pt-1 space-y-1.5">
          <p className="text-[10px] font-semibold text-gray-300 uppercase tracking-wider px-1">Выполнено</p>
          {completed.map(item => (
            <div key={item.id} className="flex items-center gap-3 px-1 py-1.5 opacity-40">
              <CheckCircle2 size={16} className="text-emerald-500 flex-shrink-0" />
              <p className="text-sm text-gray-500 line-through truncate">{item.title}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Build feed items from API data ───────────────────────────────────────────
function buildFeedItems(meds: any[], reminders: any[], dashData: any): FeedItem[] {
  const items: FeedItem[] = []
  const today = new Date().toISOString().slice(0, 10)
  const now = new Date()

  // 1. Medications — each pending log entry
  for (const med of meds) {
    const pendingLogs = (med.today_log || []).filter((l: any) => l.status === 'pending')
    for (const log of pendingLogs) {
      const time = new Date(log.scheduled_at).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
      items.push({
        id: `med_${med.id}_${log.scheduled_at}`,
        type: 'medication',
        title: `${med.name}${med.dosage ? ` — ${med.dosage}` : ''}`,
        subtitle: `Приём в ${time}`,
        urgent: !!med.is_critical,
        onDone: () => healthApi.logIntake(med.id, { scheduled_at: log.scheduled_at, status: 'taken' }),
      })
    }
  }

  // 2. Reminders — due today (one-time) or recurring (always shown)
  for (const r of reminders) {
    if (r.schedule_times) {
      // Recurring reminder — always in today's feed
      let times = ''
      try { times = JSON.parse(r.schedule_times).join(', ') } catch { times = r.schedule_times }
      items.push({
        id: `rem_${r.id}`,
        type: 'reminder',
        title: r.title,
        subtitle: times ? `🔄 ${times}` : undefined,
        onDone: () => remindersApi.action(r.id, { status: 'done' }),
      })
    } else if (r.due_at) {
      // One-time: show if due today or overdue
      const due = new Date(r.due_at)
      const dueDate = r.due_at.slice(0, 10)
      if (dueDate <= today) {
        items.push({
          id: `rem_${r.id}`,
          type: 'reminder',
          title: r.title,
          subtitle: r.notes ?? (due < now ? '⏰ Просрочено' : undefined),
          urgent: due < now,
          onDone: () => remindersApi.action(r.id, { status: 'done' }),
        })
      }
    }
  }

  // 3. Medical visit today or ≤1 day
  if (dashData?.next_medical_visit) {
    const v = dashData.next_medical_visit
    const daysUntil = v.visit_date
      ? Math.ceil((new Date(v.visit_date).getTime() - now.getTime()) / 86400000)
      : null
    if (daysUntil !== null && daysUntil <= 1) {
      items.push({
        id: `visit_${v.id ?? 0}`,
        type: 'visit',
        title: `Визит: ${v.specialty}`,
        subtitle: `${v.doctor}${daysUntil === 0 ? ' · сегодня' : ' · завтра'}`,
        urgent: daysUntil === 0,
      })
    }
  }

  // 4. Birthdays today / ≤2 days
  for (const b of (dashData?.upcoming_birthdays ?? [])) {
    if (b.days_until <= 2) {
      items.push({
        id: `bday_${b.name}`,
        type: 'birthday',
        title: b.days_until === 0 ? `🎉 Сегодня ДР: ${b.name}` : `ДР через ${b.days_until} дн.: ${b.name}`,
        urgent: b.days_until === 0,
      })
    }
  }

  // Sort: urgent first, then by type
  const order = { medication: 0, visit: 1, reminder: 2, birthday: 3 }
  items.sort((a, b) => {
    if (a.urgent && !b.urgent) return -1
    if (!a.urgent && b.urgent) return 1
    return (order[a.type] ?? 9) - (order[b.type] ?? 9)
  })

  return items
}

// ─── Build recommendation cards ───────────────────────────────────────────────
function buildRecos(dashData: any, history: any[], briefing: any): RecoCard[] {
  const cards: RecoCard[] = []
  const morning = briefing?.find((b: any) => b.briefing_type === 'morning')
  const content = morning?.content ?? {}
  const readiness = dashData?.state?.readiness_score ?? null

  // Astro note
  if (content.day_quality?.astro_note) {
    cards.push({
      id: 'astro',
      icon: '🔮',
      color: 'blue',
      title: `Нумерология дня: ${content.day_quality.numerology_day ?? ''}`,
      action: content.day_quality.astro_note,
      detail: 'Учитывай астрологические ритмы при планировании переговоров и решений.',
    })
  }

  // Readiness: low
  if (readiness !== null && readiness < 65) {
    const trend = history.length >= 3
      ? history.slice(-3).every((d: any, i: number, arr: any[]) => i === 0 || (d.readiness_score ?? 100) <= (arr[i-1].readiness_score ?? 100))
      : false
    cards.push({
      id: 'low-readiness',
      icon: '⚠️',
      color: 'amber',
      title: trend ? 'Готовность снижается 3 дня подряд' : `Низкая готовность — ${readiness}%`,
      action: 'Предлагаю перенести тяжёлые встречи на завтра',
      detail: 'При низкой готовности когнитивные задачи и переговоры лучше отложить. Приоритет — восстановление: сон, лёгкая активность, без алкоголя.',
    })
  }

  // Readiness: high
  if (readiness !== null && readiness >= 80 && !cards.find(c => c.id === 'low-readiness')) {
    cards.push({
      id: 'high-readiness',
      icon: '🟢',
      color: 'green',
      title: `Хорошая готовность — ${readiness}%`,
      action: 'Сегодня подходящий день для переговоров',
      detail: 'Высокая готовность означает хорошую концентрацию и эмоциональную устойчивость. Используй день для важных решений и сложных разговоров.',
    })
  }

  // Upcoming birthday ≤ 2 days
  const nearBday = dashData?.upcoming_birthdays?.find((b: any) => b.days_until > 0 && b.days_until <= 2)
  if (nearBday) {
    cards.push({
      id: `bday-prep-${nearBday.name}`,
      icon: '🎁',
      color: 'pink',
      title: `ДР через ${nearBday.days_until} дн. — ${nearBday.name}`,
      action: 'Подготовь поздравление или подарок',
      detail: `Не забудь поздравить ${nearBday.name}. Посмотри историю подарков и интересы в разделе Контакты.`,
    })
  }

  return cards.slice(0, 3)
}

// ─── Главная Ани ──────────────────────────────────────────────────────────────
function AnyaHome({ data, history }: { data: any; history: any[] }) {
  const navigate = useNavigate()
  const [meds, setMeds] = useState<any[]>([])
  const [reminders, setReminders] = useState<any[]>([])
  const [briefing, setBriefing] = useState<any[]>([])
  const [feedReady, setFeedReady] = useState(false)
  const [showAdd, setShowAdd] = useState(false)
  const [fabOpen, setFabOpen] = useState(false)
  const [feedKey, setFeedKey] = useState(0)

  useEffect(() => {
    Promise.all([
      healthApi.getMedications().catch(() => []),
      remindersApi.getAll().catch(() => []),
      briefingApi.getToday().catch(() => []),
    ]).then(([m, r, b]) => {
      setMeds(m)
      setReminders(r)
      setBriefing(b)
    }).finally(() => setFeedReady(true))
  }, [feedKey])

  const feedItems = feedReady ? buildFeedItems(meds, reminders, data) : []
  const recos = feedReady ? buildRecos(data, history, briefing) : []

  const state = data?.state
  const readiness = state?.readiness_score ?? null
  const energy = state?.energy_subjective ?? null
  const sleep = state?.sleep_score ?? null

  return (
    <>
      {/* ⚡ Единая лента действий */}
      <GlassCard delay={0.05} className="p-4">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-7 h-7 rounded-xl bg-amber-100 flex items-center justify-center">
            <Zap size={14} className="text-amber-500" />
          </div>
          <span className="font-semibold text-gray-800 text-sm">Сейчас важно</span>
          {feedItems.length > 0 && (
            <span className="ml-auto text-xs text-gray-400">{feedItems.length} пункт{feedItems.length === 1 ? '' : feedItems.length < 5 ? 'а' : 'ов'}</span>
          )}
        </div>
        {!feedReady
          ? <div className="py-4"><LoadingSpinner /></div>
          : <ActionFeed items={feedItems} onCheck={() => {}} />
        }
      </GlassCard>

      {/* 💡 Рекомендации */}
      {recos.length > 0 && (
        <div className="space-y-2">
          {recos.map((card, i) => (
            <RecoCardItem key={card.id} card={card} delay={0.07 + i * 0.04} />
          ))}
        </div>
      )}

      {/* Витальные кольца */}
      <GlassCard delay={0.1} className="p-4" onClick={() => navigate('/state')}>
        <div className="flex items-center justify-between mb-3">
          <span className="font-semibold text-gray-800 text-sm">Состояние сегодня</span>
          <ChevronRight size={14} className="text-gray-300" />
        </div>
        <div className="flex justify-around">
          <RadialRing value={readiness} max={100} color="#5B9DB8" label="Готовность" sublabel="%" size={84} stroke={8} />
          <RadialRing value={energy} max={10} color="#34d399" label="Энергия" sublabel="/10" size={84} stroke={8} />
          <RadialRing value={sleep} max={100} color="#a78bfa" label="Сон" sublabel="%" size={84} stroke={8}>
            {sleep != null ? (
              <><Moon size={13} color="#a78bfa" /><span style={{ fontSize: 17, fontWeight: 800, color: '#1a1a2e', lineHeight: 1, marginTop: 2 }}>{sleep}</span></>
            ) : (
              <span style={{ fontSize: 18, fontWeight: 700, color: '#d1d5db' }}>—</span>
            )}
          </RadialRing>
        </div>
        <div className="flex gap-2 mt-4 justify-center">
          {[
            { label: 'Тренировка', done: state?.workout_done, icon: <Dumbbell size={11} /> },
            { label: 'Алкоголь', done: state?.alcohol ? false : null, icon: null },
          ].map((item, i) => (
            item.done !== undefined && item.done !== null ? (
              <div key={i} className={`flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold ${item.done ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-400'}`}>
                {item.icon}{item.label}
              </div>
            ) : null
          ))}
        </div>
      </GlassCard>

      {/* Динамика */}
      {history.length > 1 && (
        <GlassCard delay={0.13} className="p-4">
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

      {/* Финансы */}
      <GlassCard delay={0.15} className="p-4" onClick={() => navigate('/finances')}>
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-emerald-50 flex items-center justify-center flex-shrink-0">
            <Wallet size={18} className="text-emerald-500" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs text-gray-500">Расходы за месяц</p>
            <p className="text-base font-bold text-gray-900">
              {data?.month_expenses != null ? `${(data.month_expenses / 1000).toFixed(0)} тыс. ₽` : '—'}
            </p>
          </div>
          <ChevronRight size={16} className="text-gray-300 flex-shrink-0" />
        </div>
      </GlassCard>

      {/* FAB + Добавить */}
      <motion.button
        onClick={() => { haptic('medium'); setFabOpen(true) }}
        className="fixed z-40 flex items-center justify-center shadow-lg"
        style={{ bottom: 88, right: 20, width: 52, height: 52, borderRadius: '50%', background: 'linear-gradient(135deg, #5B9DB8, #4a8aa5)' }}
        whileTap={{ scale: 0.92 }}
        initial={{ scale: 0, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: 'spring', delay: 0.3 }}>
        <Plus size={24} color="white" strokeWidth={2.5} />
      </motion.button>

      <QuickAddSheet
        open={fabOpen}
        onClose={() => setFabOpen(false)}
        onDone={() => setFeedKey(k => k + 1)}
      />
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
    financesApi.getSummary().then(setFinances).catch(() => {})
  }, [])

  const state = data?.state
  const readiness = state?.readiness_score ?? null
  const energy = state?.energy_subjective ?? null

  return (
    <>
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

      <GlassCard delay={0.14} className="p-4" onClick={() => navigate('/finances')}>
        {(() => {
          const PRIV = new Set(['Здоровье'])
          const rawCats: any[] = finances?.by_category ?? []
          const safeCats = rawCats.filter((c: any) => !PRIV.has(c.category))
          const hiddenTotal = rawCats.filter((c: any) => PRIV.has(c.category)).reduce((s: number, c: any) => s + c.total, 0)
          const displayCats = hiddenTotal > 0 ? [...safeCats, { category: 'Личное', total: hiddenTotal }] : safeCats
          return (
            <div className="flex items-center gap-3">
              <div className="flex-shrink-0">
                {displayCats.length
                  ? <FinanceDonut byCategory={displayCats} />
                  : <div className="w-10 h-10 rounded-2xl bg-emerald-50 flex items-center justify-center"><Wallet size={18} className="text-emerald-500" /></div>
                }
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs text-gray-500">Расходы за месяц</p>
                <p className="text-base font-bold text-gray-900">
                  {finances?.month_expenses != null ? `${(finances.month_expenses / 1000).toFixed(0)} тыс. ₽` : '—'}
                </p>
              </div>
              <ChevronRight size={16} className="text-gray-300 flex-shrink-0" />
            </div>
          )
        })()}
      </GlassCard>

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

// ─── Root ─────────────────────────────────────────────────────────────────────
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
