import { useEffect, useState } from 'react'
import { RefreshCw, Send, Sun, Moon, Zap, ChevronDown, ChevronUp } from 'lucide-react'
import GlassCard from '../components/GlassCard'
import PageHeader from '../components/PageHeader'
import LoadingSpinner from '../components/LoadingSpinner'
import { briefingApi } from '../api'
import { useUser } from '../App'

function haptic(s: 'light' | 'medium' = 'light') {
  window.Telegram?.WebApp?.HapticFeedback?.impactOccurred(s)
}

function formatBriefingText(b: any): string {
  const c = b.content || {}
  const lines: string[] = [`📋 ${b.briefing_type === 'morning' ? 'Утренний брифинг' : 'Вечерний дайджест'} — ${b.briefing_date}`, '']
  if (c.state) lines.push(`⚡ Состояние: Общее ${c.state.energy}/10 · Сон ${c.state.sleep} ч · Готовность ${c.state.readiness}`)
  if (c.day_quality) lines.push(`✨ День: ${c.day_quality.astro_note || ''}`)
  if (c.schedule?.length) { lines.push(''); lines.push('📅 Расписание:'); c.schedule.forEach((s: string) => lines.push(`• ${s}`)) }
  if (c.important_dates?.length) { lines.push(''); lines.push('🎯 Важные даты:'); c.important_dates.forEach((d: string) => lines.push(`• ${d}`)) }
  if (c.finances) lines.push(`\n💰 Финансы: ${c.finances.balance_trend}`)
  if (c.priorities?.length) { lines.push(''); lines.push('🎯 Приоритеты:'); c.priorities.forEach((p: string) => lines.push(`• ${p}`)) }
  return lines.join('\n')
}

export default function BriefingPage() {
  const { role } = useUser()
  const [briefings, setBriefings] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<number | null>(null)
  const [refreshing, setRefreshing] = useState(false)

  const load = async () => {
    const data = await briefingApi.getToday()
    setBriefings(data)
  }

  useEffect(() => {
    load().catch(() => {}).finally(() => setLoading(false))
  }, [])

  const handleRefresh = async () => {
    setRefreshing(true)
    haptic('medium')
    await load().catch(() => {})
    setRefreshing(false)
    window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success')
  }

  const handleForward = (b: any) => {
    haptic('light')
    const text = formatBriefingText(b)
    if (window.Telegram?.WebApp) {
      // Copies to clipboard
      navigator.clipboard?.writeText(text).catch(() => {})
    }
  }

  if (loading) return <div className="px-4 pt-6"><LoadingSpinner /></div>

  return (
    <div className="page-scroll h-full overflow-y-auto">
      <div className="px-4 pt-6 pb-4 space-y-4">
        <PageHeader
          title="Сводка"
          subtitle="Брифинг и дайджест"
          action={
            <button
              onClick={handleRefresh}
              className="w-9 h-9 glass-button flex items-center justify-center"
            >
              <RefreshCw size={15} className={refreshing ? 'animate-spin' : ''} />
            </button>
          }
        />

        {briefings.length === 0 && (
          <GlassCard className="p-8 text-center">
            <div className="w-12 h-12 rounded-full bg-amber-50 flex items-center justify-center mx-auto mb-3">
              <Sun size={24} className="text-amber-400" />
            </div>
            <p className="text-gray-600 font-medium">Брифинг не готов</p>
            <p className="text-sm text-gray-400 mt-1">Бот генерирует брифинг в 07:00 и дайджест в 22:00</p>
          </GlassCard>
        )}

        {briefings.map((b, i) => {
          const isMorning = b.briefing_type === 'morning'
          const c = b.content || {}
          const isExpanded = expanded === b.id

          return (
            <GlassCard key={b.id} delay={i * 0.05} className="overflow-hidden">
              {/* Header */}
              <div className="p-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-2xl flex items-center justify-center ${isMorning ? 'bg-amber-50' : 'bg-indigo-50'}`}>
                      {isMorning ? <Sun size={18} className="text-amber-400" /> : <Moon size={18} className="text-indigo-400" />}
                    </div>
                    <div>
                      <p className="font-semibold text-gray-800 text-sm">
                        {isMorning ? 'Утренний брифинг' : 'Вечерний дайджест'}
                      </p>
                      <p className="text-xs text-gray-400">{b.briefing_date}</p>
                    </div>
                  </div>
                  <button
                    onClick={() => setExpanded(isExpanded ? null : b.id)}
                    className="w-8 h-8 flex items-center justify-center rounded-xl bg-gray-50"
                  >
                    {isExpanded ? <ChevronUp size={14} className="text-gray-400" /> : <ChevronDown size={14} className="text-gray-400" />}
                  </button>
                </div>

                {/* Urgent block */}
                {c.priorities?.length > 0 && (
                  <div className="mt-3 p-3 bg-amber-50/60 rounded-2xl">
                    <div className="flex items-center gap-1.5 mb-2">
                      <Zap size={12} className="text-amber-500" />
                      <span className="text-xs font-semibold text-amber-600">Сейчас важно</span>
                    </div>
                    {c.priorities.slice(0, 2).map((p: string, idx: number) => (
                      <p key={idx} className="text-xs text-gray-700">• {p}</p>
                    ))}
                  </div>
                )}

                {/* Quick stats */}
                {c.state && (
                  <div className="flex gap-2 mt-3">
                    <span className="badge bg-blue-50 text-blue-600 text-xs">🧠 Состояние {c.state.energy}/10</span>
                    <span className="badge bg-green-50 text-green-600 text-xs">😴 {c.state.sleep} ч</span>
                    <span className="badge bg-purple-50 text-purple-600 text-xs">💜 {c.state.readiness}</span>
                  </div>
                )}
              </div>

              {/* Expanded content */}
              {isExpanded && (
                <div className="px-4 pb-4 border-t border-white/60 pt-4 space-y-3">
                  {/* Если брифинг пришёл из мини-аппа или авто — показываем raw_text */}
                  {c.raw_text && (
                    <div>
                      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1.5">📋 Бриф</p>
                      <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">{c.raw_text}</p>
                    </div>
                  )}
                  {/* Структурированный контент (старый формат) */}
                  {!c.raw_text && c.day_quality && (
                    <div>
                      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1.5">✨ Качество дня</p>
                      {c.day_quality.numerology_day && <p className="text-sm text-gray-600">Нумерология: день {c.day_quality.numerology_day}</p>}
                      {c.day_quality.astro_note && <p className="text-sm text-gray-600">{c.day_quality.astro_note}</p>}
                    </div>
                  )}
                  {!c.raw_text && c.schedule?.length > 0 && (
                    <div>
                      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1.5">📅 Расписание</p>
                      {c.schedule.map((s: string, idx: number) => (
                        <p key={idx} className="text-sm text-gray-700">• {s}</p>
                      ))}
                    </div>
                  )}
                  {!c.raw_text && c.important_dates?.length > 0 && (
                    <div>
                      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1.5">🎯 Важные даты</p>
                      {c.important_dates.map((d: string, idx: number) => (
                        <p key={idx} className="text-sm text-gray-700">• {d}</p>
                      ))}
                    </div>
                  )}
                  {!c.raw_text && c.finances && (
                    <div>
                      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1.5">💰 Финансы</p>
                      <p className="text-sm text-gray-700">{c.finances.balance_trend}</p>
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex gap-2 mt-2">
                    <button
                      onClick={handleRefresh}
                      className="flex-1 glass-button py-2.5 flex items-center justify-center gap-1.5 text-xs font-medium"
                    >
                      <RefreshCw size={13} /> Обновить
                    </button>
                    <button
                      onClick={() => handleForward(b)}
                      className="flex-1 accent-button py-2.5 flex items-center justify-center gap-1.5 text-xs"
                    >
                      <Send size={13} /> Поделиться
                    </button>
                  </div>
                </div>
              )}
            </GlassCard>
          )
        })}

        <div className="h-4" />
      </div>
    </div>
  )
}
