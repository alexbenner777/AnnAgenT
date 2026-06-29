import { useEffect, useState } from 'react'
import { Plus, Check, SkipForward, Clock, Bell } from 'lucide-react'
import GlassCard from '../components/GlassCard'
import PageHeader from '../components/PageHeader'
import LoadingSpinner from '../components/LoadingSpinner'
import { remindersApi } from '../api'

function haptic(s: 'light' | 'medium' = 'light') {
  window.Telegram?.WebApp?.HapticFeedback?.impactOccurred(s)
}

export default function RemindersPage() {
  const [reminders, setReminders] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showAdd, setShowAdd] = useState(false)
  const [freeText, setFreeText] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    remindersApi.getAll()
      .then(setReminders)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const parseReminder = (text: string) => {
    // Simple parser: "напомни завтра в 9 позвонить юристу" → extract data
    const tomorrow = new Date(); tomorrow.setDate(tomorrow.getDate() + 1)
    const timeMatch = text.match(/в?\s*(\d{1,2})[:\.]?(\d{2})?/)
    const time = timeMatch ? `${timeMatch[1].padStart(2,'0')}:${(timeMatch[2] || '00')}` : '09:00'
    const title = text.replace(/напомни\s*/i, '').replace(/завтра\s*/i, '').replace(/в\s*\d+[:\.]?\d*\s*/i, '').trim()
    const due_at = `${tomorrow.toISOString().slice(0,10)} ${time}:00`
    return { title: title || text, due_at }
  }

  const handleAdd = async () => {
    if (!freeText.trim()) return
    setSaving(true)
    haptic('medium')
    try {
      const parsed = parseReminder(freeText)
      await remindersApi.add(parsed)
      const updated = await remindersApi.getAll()
      setReminders(updated)
      setFreeText('')
      setShowAdd(false)
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success')
    } finally {
      setSaving(false)
    }
  }

  const handleAction = async (id: number, status: string) => {
    haptic('medium')
    await remindersApi.action(id, { status })
    const updated = await remindersApi.getAll()
    setReminders(updated)
    window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success')
  }

  const recurring = reminders.filter(r => r.schedule_times)
  const oneTime = reminders.filter(r => !r.schedule_times && r.due_at)

  if (loading) return <div className="px-4 pt-6"><LoadingSpinner /></div>

  return (
    <div className="page-scroll h-full overflow-y-auto">
      <div className="px-4 pt-6 pb-4 space-y-4">
        <PageHeader
          title="Напоминания"
          subtitle="Разовые и повторяющиеся"
          action={
            <button onClick={() => { haptic(); setShowAdd(true) }} className="accent-button w-9 h-9 flex items-center justify-center">
              <Plus size={18} />
            </button>
          }
        />

        {showAdd && (
          <GlassCard className="p-4 space-y-3">
            <p className="font-semibold text-gray-800 text-sm">Добавить напоминание</p>
            <input
              className="w-full bg-gray-50 rounded-xl px-3 py-3 text-sm outline-none border border-gray-200 focus:border-accent"
              placeholder='Напр.: "напомни завтра в 9 позвонить юристу"'
              value={freeText}
              onChange={e => setFreeText(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleAdd()}
              autoFocus
            />
            <div className="flex gap-2">
              <button onClick={() => setShowAdd(false)} className="flex-1 py-2.5 rounded-xl bg-gray-100 text-gray-600 text-sm font-medium">Отмена</button>
              <button onClick={handleAdd} disabled={saving} className="flex-1 py-2.5 rounded-xl accent-button text-sm">
                {saving ? 'Сохраняем...' : 'Добавить'}
              </button>
            </div>
          </GlassCard>
        )}

        {reminders.length === 0 && (
          <GlassCard className="p-8 text-center">
            <Bell size={32} className="mx-auto text-gray-200 mb-3" />
            <p className="text-gray-400 text-sm">Нет напоминаний</p>
          </GlassCard>
        )}

        {oneTime.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider px-1">Разовые</p>
            {oneTime.map((r, i) => {
              const isPast = r.due_at && new Date(r.due_at) < new Date()
              return (
                <GlassCard key={r.id} delay={i * 0.04} className="p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3 flex-1">
                      <div className={`w-10 h-10 rounded-2xl flex items-center justify-center flex-shrink-0 ${isPast ? 'bg-red-50' : 'bg-purple-50'}`}>
                        <Bell size={16} className={isPast ? 'text-red-400' : 'text-purple-400'} />
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-gray-800">{r.title}</p>
                        {r.due_at && (
                          <p className={`text-xs mt-0.5 ${isPast ? 'text-red-400' : 'text-gray-500'}`}>
                            📅 {new Date(r.due_at).toLocaleString('ru-RU', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}
                          </p>
                        )}
                        {r.notes && <p className="text-xs text-gray-400 mt-0.5">{r.notes}</p>}
                      </div>
                    </div>
                    <div className="flex gap-1.5">
                      <button
                        onClick={() => handleAction(r.id, 'done')}
                        className="w-8 h-8 rounded-xl bg-green-50 flex items-center justify-center active:scale-90 transition-transform"
                      >
                        <Check size={14} className="text-green-500" />
                      </button>
                      <button
                        onClick={() => handleAction(r.id, 'skipped')}
                        className="w-8 h-8 rounded-xl bg-gray-100 flex items-center justify-center active:scale-90 transition-transform"
                      >
                        <SkipForward size={14} className="text-gray-400" />
                      </button>
                    </div>
                  </div>
                </GlassCard>
              )
            })}
          </div>
        )}

        {recurring.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider px-1">Повторяющиеся</p>
            {recurring.map((r, i) => {
              const times = r.schedule_times ? JSON.parse(r.schedule_times).join(', ') : ''
              return (
                <GlassCard key={r.id} delay={i * 0.04} className="p-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-2xl bg-blue-50 flex items-center justify-center flex-shrink-0">
                      <Clock size={16} className="text-blue-400" />
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-semibold text-gray-800">{r.title}</p>
                      {times && <p className="text-xs text-gray-500 mt-0.5">🔄 {times}</p>}
                    </div>
                    <div className="flex gap-1.5">
                      <button onClick={() => handleAction(r.id, 'done')} className="w-8 h-8 rounded-xl bg-green-50 flex items-center justify-center active:scale-90 transition-transform">
                        <Check size={14} className="text-green-500" />
                      </button>
                      <button onClick={() => handleAction(r.id, 'snoozed')} className="w-8 h-8 rounded-xl bg-amber-50 flex items-center justify-center active:scale-90 transition-transform">
                        <Clock size={14} className="text-amber-400" />
                      </button>
                    </div>
                  </div>
                </GlassCard>
              )
            })}
          </div>
        )}

        <div className="h-4" />
      </div>
    </div>
  )
}
