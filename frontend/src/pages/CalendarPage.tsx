import { useEffect, useState } from 'react'
import { Calendar, Clock, MapPin } from 'lucide-react'
import GlassCard from '../components/GlassCard'
import PageHeader from '../components/PageHeader'
import LoadingSpinner from '../components/LoadingSpinner'
import { calendarApi } from '../api'
import { useUser } from '../App'

const LOAD_COLORS: Record<string, { bg: string; text: string; label: string; dot: string }> = {
  high:     { bg: 'bg-red-50',    text: 'text-red-500',    label: '🔴 Высокая', dot: '#ef4444' },
  medium:   { bg: 'bg-yellow-50', text: 'text-yellow-600', label: '🟡 Средняя', dot: '#eab308' },
  low:      { bg: 'bg-green-50',  text: 'text-green-600',  label: '🟢 Низкая',  dot: '#22c55e' },
  personal: { bg: 'bg-purple-50', text: 'text-purple-500', label: '⚪ Личное',  dot: '#a855f7' },
  family:   { bg: 'bg-pink-50',   text: 'text-pink-500',   label: '⚪ Семья',   dot: '#ec4899' },
  health:   { bg: 'bg-blue-50',   text: 'text-blue-500',   label: '💊 Здоровье',dot: '#3b82f6' },
}

// Категории событий, которые относятся к медицине
const HEALTH_TYPES = new Set(['health', 'medical', 'doctor', 'clinic'])

function isMedicalEvent(ev: any): boolean {
  return (
    HEALTH_TYPES.has(ev.meeting_type) ||
    HEALTH_TYPES.has(ev.cognitive_load) ||
    HEALTH_TYPES.has(ev.category)
  )
}

function maskForDen(ev: any): any {
  if (!isMedicalEvent(ev)) return ev
  return {
    ...ev,
    title: 'Личное / Занят',
    description: undefined,
    location: undefined,
    meeting_type: 'personal',
    cognitive_load: 'personal',
  }
}

function groupByDate(events: any[]) {
  const groups: Record<string, any[]> = {}
  events.forEach(e => {
    const d = e.event_date
    if (!groups[d]) groups[d] = []
    groups[d].push(e)
  })
  return groups
}

function formatDateLabel(dateStr: string) {
  const d = new Date(dateStr + 'T00:00:00')
  const today = new Date()
  const tomorrow = new Date(today); tomorrow.setDate(today.getDate() + 1)
  if (d.toDateString() === today.toDateString()) return 'Сегодня'
  if (d.toDateString() === tomorrow.toDateString()) return 'Завтра'
  return d.toLocaleDateString('ru-RU', { weekday: 'short', day: 'numeric', month: 'long' })
}

function getTotalLoad(events: any[]) {
  const highs = events.filter(e => e.cognitive_load === 'high').length
  const total = events.length
  if (highs >= 2 || total >= 5) return 'Перегрузка'
  if (highs >= 1 || total >= 3) return 'Насыщенно'
  return 'Комфортно'
}

export default function CalendarPage() {
  const { role } = useUser()
  const [events, setEvents] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [days, setDays] = useState(7)

  useEffect(() => {
    calendarApi.getEvents(days)
      .then(raw => {
        // Маскируем медицинские события для Дена
        const processed = role === 'den' ? raw.map(maskForDen) : raw
        setEvents(processed)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [days, role])

  const grouped = groupByDate(events)
  const sortedDates = Object.keys(grouped).sort()

  return (
    <div className="page-scroll h-full overflow-y-auto">
      <div className="px-4 pt-6 pb-4 space-y-4">
        <PageHeader title="Календарь" subtitle="Расписание и встречи" />

        {/* Period selector */}
        <div className="glass-card-sm p-1 flex gap-1">
          {[
            { label: 'Сегодня', val: 1 },
            { label: '7 дней',  val: 7 },
            { label: '14 дней', val: 14 },
          ].map(opt => (
            <button
              key={opt.val}
              onClick={() => setDays(opt.val)}
              className={`flex-1 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                days === opt.val ? 'bg-white shadow-sm text-accent' : 'text-gray-500'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>

        {loading && <LoadingSpinner />}

        {!loading && sortedDates.length === 0 && (
          <GlassCard className="p-8 text-center">
            <Calendar size={32} className="mx-auto text-gray-200 mb-3" />
            <p className="text-gray-400 text-sm">Нет событий</p>
          </GlassCard>
        )}

        {!loading && sortedDates.map((dateStr, di) => {
          const dayEvents = grouped[dateStr]
          const loadStatus = getTotalLoad(dayEvents)
          return (
            <div key={dateStr} className="space-y-2">
              <div className="flex items-center justify-between px-1">
                <p className="text-sm font-semibold text-gray-700 capitalize">{formatDateLabel(dateStr)}</p>
                <span className={`badge text-[10px] ${
                  loadStatus === 'Перегрузка' ? 'bg-red-50 text-red-500' :
                  loadStatus === 'Насыщенно'  ? 'bg-yellow-50 text-yellow-600' :
                                                 'bg-green-50 text-green-600'
                }`}>
                  {loadStatus}
                </span>
              </div>
              {dayEvents.map((ev, i) => {
                const load = LOAD_COLORS[ev.cognitive_load || ev.meeting_type] || LOAD_COLORS.low
                return (
                  <GlassCard key={ev.id} delay={di * 0.05 + i * 0.03} className="p-4">
                    <div className="flex items-start gap-3">
                      <div className="flex flex-col items-center pt-0.5">
                        <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: load.dot }} />
                        {i < dayEvents.length - 1 && <div className="w-0.5 h-full bg-gray-100 mt-1" />}
                      </div>
                      <div className="flex-1">
                        <p className="font-semibold text-gray-800 text-sm">{ev.title}</p>
                        <div className="flex flex-wrap gap-3 mt-1.5">
                          {ev.start_time && (
                            <span className="flex items-center gap-1 text-xs text-gray-500">
                              <Clock size={11} /> {ev.start_time}{ev.end_time ? `–${ev.end_time}` : ''}
                            </span>
                          )}
                          {ev.location && (
                            <span className="flex items-center gap-1 text-xs text-gray-500">
                              <MapPin size={11} /> {ev.location}
                            </span>
                          )}
                        </div>
                        {ev.description && (
                          <p className="text-xs text-gray-400 mt-1">{ev.description}</p>
                        )}
                        <div className="flex items-center gap-2 mt-2">
                          <span className={`badge text-[10px] ${load.bg} ${load.text}`}>{load.label}</span>
                        </div>
                      </div>
                    </div>
                  </GlassCard>
                )
              })}
            </div>
          )
        })}

        <div className="h-4" />
      </div>
    </div>
  )
}
