import { useEffect, useState } from 'react'
import { Plus, Mic, ChevronDown, ChevronUp, AlertTriangle, FileText, Users, Bookmark, Eye } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import GlassCard from '../components/GlassCard'
import PageHeader from '../components/PageHeader'
import LoadingSpinner from '../components/LoadingSpinner'
import { meetingsApi } from '../api'
import { useUser } from '../App'

function haptic(s: 'light' | 'medium' = 'light') {
  window.Telegram?.WebApp?.HapticFeedback?.impactOccurred(s)
}

const FORMATS = ['protocol', 'negotiations', 'tasks', 'letter', 'tldr', 'translation']
const FORMAT_LABELS: Record<string, string> = {
  protocol: 'Протокол', negotiations: 'Переговоры', tasks: 'Задачи',
  letter: 'Письмо', tldr: 'TL;DR', translation: 'Перевод'
}
const RISK_COLORS: Record<string, string> = {
  high: '#ef4444', medium: '#eab308', low: '#22c55e'
}

function showWip() {
  if (window.Telegram?.WebApp?.showAlert) {
    window.Telegram.WebApp.showAlert('⏳ В разработке')
  } else {
    const el = document.createElement('div')
    el.textContent = '⏳ В разработке'
    el.style.cssText = 'position:fixed;top:20px;left:50%;transform:translateX(-50%);background:#1c1c1e;color:#fff;padding:10px 20px;border-radius:12px;font-size:14px;z-index:9999;pointer-events:none;opacity:1;transition:opacity 0.4s'
    document.body.appendChild(el)
    setTimeout(() => { el.style.opacity = '0'; setTimeout(() => el.remove(), 400) }, 2000)
  }
}

export default function MeetingsPage() {
  const { role } = useUser()
  const isAnya = role === 'anya'

  const [allMeetings, setAllMeetings] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<number | null>(null)
  const [showAdd, setShowAdd] = useState(false)
  const [newMeeting, setNewMeeting] = useState({
    title: '', participants: '', summary: '', format: 'protocol', risk_flag: '', shareable: false
  })

  useEffect(() => {
    meetingsApi.getAll()
      .then(setAllMeetings)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  // Ден видит только shareable=1 и без high-risk
  const meetings = isAnya
    ? allMeetings
    : allMeetings.filter(m => m.shareable === 1 && m.risk_flag !== 'high')

  const handleAdd = async () => {
    await meetingsApi.add({ ...newMeeting, shareable: newMeeting.shareable ? 1 : 0 })
    const updated = await meetingsApi.getAll()
    setAllMeetings(updated)
    setShowAdd(false)
    setNewMeeting({ title: '', participants: '', summary: '', format: 'protocol', risk_flag: '', shareable: false })
    window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success')
  }

  if (loading) return <div className="px-4 pt-6"><LoadingSpinner /></div>

  return (
    <div className="page-scroll h-full overflow-y-auto">
      <div className="px-4 pt-6 pb-4 space-y-4">
        <PageHeader
          title="Встречи"
          subtitle={isAnya ? 'Разборы · Протоколы · Задачи' : 'Ключевые встречи'}
          action={isAnya ? (
            <button onClick={() => { haptic(); setShowAdd(true) }} className="accent-button w-9 h-9 flex items-center justify-center">
              <Plus size={18} />
            </button>
          ) : undefined}
        />

        {/* Подсказка для Дена */}
        {!isAnya && (
          <GlassCard delay={0.03} className="px-4 py-3">
            <div className="flex items-center gap-2">
              <Eye size={14} className="text-blue-400 flex-shrink-0" />
              <p className="text-xs text-gray-500">Показаны только встречи, отмеченные «Показать Дену»</p>
            </div>
          </GlassCard>
        )}

        {/* Форма добавления — только Аня */}
        {isAnya && showAdd && (
          <GlassCard className="p-4 space-y-3">
            <p className="font-semibold text-gray-800 text-sm">Новая встреча</p>
            <input
              className="w-full bg-gray-50 rounded-xl px-3 py-2.5 text-sm outline-none border border-gray-200 focus:border-accent"
              placeholder="Название встречи"
              value={newMeeting.title}
              onChange={e => setNewMeeting(p => ({...p, title: e.target.value}))}
            />
            <input
              className="w-full bg-gray-50 rounded-xl px-3 py-2.5 text-sm outline-none border border-gray-200 focus:border-accent"
              placeholder="Участники (через запятую)"
              value={newMeeting.participants}
              onChange={e => setNewMeeting(p => ({...p, participants: e.target.value}))}
            />
            <textarea
              className="w-full bg-gray-50 rounded-xl px-3 py-2.5 text-sm outline-none border border-gray-200 focus:border-accent resize-none"
              placeholder="Сводка / саммари"
              rows={3}
              value={newMeeting.summary}
              onChange={e => setNewMeeting(p => ({...p, summary: e.target.value}))}
            />
            <select
              className="w-full bg-gray-50 rounded-xl px-3 py-2.5 text-sm outline-none border border-gray-200"
              value={newMeeting.format}
              onChange={e => setNewMeeting(p => ({...p, format: e.target.value}))}
            >
              {FORMATS.map(f => <option key={f} value={f}>{FORMAT_LABELS[f]}</option>)}
            </select>
            <select
              className="w-full bg-gray-50 rounded-xl px-3 py-2.5 text-sm outline-none border border-gray-200"
              value={newMeeting.risk_flag}
              onChange={e => setNewMeeting(p => ({...p, risk_flag: e.target.value}))}
            >
              <option value="">Флаг риска (не установлен)</option>
              <option value="low">🟢 Низкий риск</option>
              <option value="medium">🟡 Средний риск</option>
              <option value="high">🔴 Высокий риск</option>
            </select>

            {/* Переключатель «Показать Дену» */}
            <button
              type="button"
              onClick={() => setNewMeeting(p => ({...p, shareable: !p.shareable}))}
              className={`w-full flex items-center justify-between p-3 rounded-2xl border transition-all ${
                newMeeting.shareable
                  ? 'bg-blue-50 border-blue-200'
                  : 'bg-gray-50 border-transparent'
              }`}
            >
              <div className="flex items-center gap-2">
                <Eye size={15} className={newMeeting.shareable ? 'text-blue-500' : 'text-gray-400'} />
                <span className={`text-sm font-medium ${newMeeting.shareable ? 'text-blue-600' : 'text-gray-600'}`}>
                  Показать Дену
                </span>
              </div>
              <div className={`w-5 h-5 rounded-full flex items-center justify-center transition-colors ${
                newMeeting.shareable ? 'bg-blue-500' : 'bg-gray-200'
              }`}>
                {newMeeting.shareable && (
                  <svg width="10" height="8" viewBox="0 0 10 8" fill="none">
                    <path d="M1 4L3.5 6.5L9 1" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                )}
              </div>
            </button>

            <div className="flex gap-2">
              <button onClick={() => setShowAdd(false)} className="flex-1 py-2.5 rounded-xl bg-gray-100 text-gray-600 text-sm font-medium">Отмена</button>
              <button onClick={handleAdd} className="flex-1 py-2.5 rounded-xl accent-button text-sm">Сохранить</button>
            </div>
          </GlassCard>
        )}

        {meetings.length === 0 && (
          <GlassCard className="p-8 text-center">
            <Mic size={32} className="mx-auto text-gray-200 mb-3" />
            <p className="text-gray-400 text-sm">
              {isAnya ? 'Нет разобранных встреч' : 'Нет доступных встреч'}
            </p>
            <p className="text-xs text-gray-300 mt-1">
              {isAnya ? 'Загрузите запись или добавьте вручную' : 'Аня поделится ключевыми встречами'}
            </p>
          </GlassCard>
        )}

        {meetings.map((m, i) => {
          const isExpanded = expanded === m.id
          const riskColor = m.risk_flag ? RISK_COLORS[m.risk_flag] : null

          return (
            <GlassCard key={m.id} delay={i * 0.05} className={`overflow-hidden ${m.risk_flag === 'high' ? 'border-red-200' : ''}`}>
              {m.risk_flag === 'high' && (
                <div className="bg-red-50 px-4 py-2 flex items-center gap-2">
                  <AlertTriangle size={14} className="text-red-500" />
                  <span className="text-xs font-semibold text-red-600">⚠️ Высокий риск</span>
                </div>
              )}

              <button
                className="w-full p-4 text-left"
                onClick={() => { haptic(); setExpanded(isExpanded ? null : m.id) }}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3 flex-1">
                    <div className={`w-10 h-10 rounded-2xl flex items-center justify-center flex-shrink-0 ${m.risk_flag === 'high' ? 'bg-red-50' : 'bg-blue-50'}`}>
                      <Mic size={16} className={m.risk_flag === 'high' ? 'text-red-400' : 'text-blue-400'} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <p className="font-semibold text-gray-800 text-sm truncate">{m.title || 'Без названия'}</p>
                        {isAnya && m.shareable === 1 && (
                          <span className="flex items-center gap-1 badge bg-blue-50 text-blue-500 text-[10px]">
                            <Eye size={9} /> Ден
                          </span>
                        )}
                      </div>
                      <div className="flex flex-wrap gap-2 mt-1">
                        {m.participants && (
                          <span className="flex items-center gap-1 text-xs text-gray-500">
                            <Users size={10} /> {m.participants}
                          </span>
                        )}
                        {m.meeting_date && <span className="text-xs text-gray-400">{m.meeting_date}</span>}
                        {m.format && <span className="badge bg-gray-100 text-gray-500 text-[10px]">{FORMAT_LABELS[m.format] || m.format}</span>}
                      </div>
                    </div>
                  </div>
                  {isExpanded ? <ChevronUp size={14} className="text-gray-400 flex-shrink-0 mt-1" /> : <ChevronDown size={14} className="text-gray-400 flex-shrink-0 mt-1" />}
                </div>
              </button>

              <AnimatePresence>
                {isExpanded && (
                  <motion.div
                    initial={{ height: 0 }}
                    animate={{ height: 'auto' }}
                    exit={{ height: 0 }}
                    className="overflow-hidden border-t border-white/60"
                  >
                    <div className="p-4 space-y-3">
                      {m.summary && (
                        <div>
                          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1.5">Сводка</p>
                          <p className="text-sm text-gray-700 leading-relaxed">{m.summary}</p>
                        </div>
                      )}

                      <div>
                        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1.5">Форматы</p>
                        <div className="flex flex-wrap gap-1.5">
                          {FORMATS.map(f => (
                            <button key={f}
                              onClick={() => { haptic(); showWip() }}
                              className={`px-3 py-1.5 rounded-xl text-xs font-medium transition-all active:scale-95 ${m.format === f ? 'bg-accent text-white' : 'bg-gray-100 text-gray-600'}`}>
                              {FORMAT_LABELS[f]}
                            </button>
                          ))}
                        </div>
                      </div>

                      <div className="flex gap-2 flex-wrap">
                        <button onClick={() => { haptic(); showWip() }}
                          className="glass-button px-3 py-2 text-xs flex items-center gap-1.5">
                          <Bookmark size={11} /> Дела → напоминания
                        </button>
                        <button onClick={() => { haptic(); showWip() }}
                          className="glass-button px-3 py-2 text-xs flex items-center gap-1.5">
                          <FileText size={11} /> Транскрипт
                        </button>
                      </div>

                      {m.risk_flag && (
                        <div className={`p-3 rounded-2xl border ${m.risk_flag === 'high' ? 'bg-red-50/80 border-red-100' : m.risk_flag === 'medium' ? 'bg-yellow-50/80 border-yellow-100' : 'bg-green-50/80 border-green-100'}`}>
                          <p className="text-xs font-semibold mb-1" style={{ color: riskColor || '#22c55e' }}>
                            🕵️ Разбор переговоров
                          </p>
                          <p className="text-xs text-gray-600">
                            {m.risk_flag === 'high' ? 'Обнаружены манипуляции или скрытые конфликты. Рекомендуется юридическая проверка.' :
                             m.risk_flag === 'medium' ? 'Есть отдельные точки напряжения. Требует внимания.' :
                             'Встреча прошла конструктивно. Рисков не обнаружено.'}
                          </p>
                        </div>
                      )}

                      {/* Аня может переключить shareable прямо из карточки */}
                      {isAnya && (
                        <button
                          type="button"
                          onClick={async () => {
                            haptic()
                            const updated = allMeetings.map(x =>
                              x.id === m.id ? { ...x, shareable: x.shareable ? 0 : 1 } : x
                            )
                            setAllMeetings(updated)
                            await fetch(`/api/meetings/${m.id}/shareable`, {
                              method: 'POST',
                              headers: { 'Content-Type': 'application/json' },
                              body: JSON.stringify({ shareable: m.shareable ? 0 : 1 })
                            }).catch(() => {})
                          }}
                          className={`w-full flex items-center justify-between p-3 rounded-2xl border transition-all ${
                            m.shareable ? 'bg-blue-50 border-blue-200' : 'bg-gray-50 border-transparent'
                          }`}
                        >
                          <div className="flex items-center gap-2">
                            <Eye size={14} className={m.shareable ? 'text-blue-500' : 'text-gray-400'} />
                            <span className={`text-xs font-medium ${m.shareable ? 'text-blue-600' : 'text-gray-500'}`}>
                              {m.shareable ? 'Показано Дену' : 'Показать Дену'}
                            </span>
                          </div>
                          <div className={`w-4 h-4 rounded-full ${m.shareable ? 'bg-blue-500' : 'bg-gray-200'}`} />
                        </button>
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </GlassCard>
          )
        })}

        <div className="h-4" />
      </div>
    </div>
  )
}
