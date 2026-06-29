import { useEffect, useState } from 'react'
import { CheckSquare, Zap, Pill, Bell, Stethoscope } from 'lucide-react'
import GlassCard from '../components/GlassCard'
import PageHeader from '../components/PageHeader'
import LoadingSpinner from '../components/LoadingSpinner'
import { dashboardApi, healthApi, remindersApi } from '../api'

function haptic(s: 'light' | 'medium' = 'light') {
  window.Telegram?.WebApp?.HapticFeedback?.impactOccurred(s)
}

interface Task {
  id: string
  type: 'state' | 'medication' | 'reminder' | 'visit'
  title: string
  subtitle?: string
  urgent?: boolean
}

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [done, setDone] = useState<Set<string>>(new Set())

  const loadTasks = async () => {
    const [dash, meds, reminders] = await Promise.all([
      dashboardApi.get(),
      healthApi.getMedications(),
      remindersApi.getAll()
    ])

    const list: Task[] = []

    if (!dash.state_logged) {
      list.push({ id: 'state', type: 'state', title: 'Внести состояние сегодня', subtitle: 'Энергия, сон, активность', urgent: true })
    }

    meds.forEach((med: any) => {
      const pending = med.today_log?.filter((l: any) => l.status === 'pending') || []
      pending.forEach((log: any, i: number) => {
        const time = new Date(log.scheduled_at).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
        list.push({
          id: `med_${med.id}_${i}`,
          type: 'medication',
          title: `${med.name} — ${med.dosage}`,
          subtitle: `Приём в ${time}`,
          urgent: med.is_critical
        })
      })
    })

    if (dash.next_medical_visit) {
      const v = dash.next_medical_visit
      const daysUntil = v.visit_date ? Math.ceil((new Date(v.visit_date).getTime() - Date.now()) / 86400000) : null
      if (daysUntil !== null && daysUntil <= 3) {
        list.push({
          id: `visit_${v.id}`,
          type: 'visit',
          title: `Визит: ${v.specialty}`,
          subtitle: `${v.doctor} · через ${daysUntil} дн.`,
          urgent: daysUntil <= 1
        })
      }
    }

    reminders.forEach((r: any) => {
      if (r.due_at) {
        const due = new Date(r.due_at)
        const now = new Date()
        if (due <= new Date(now.getTime() + 24 * 60 * 60 * 1000)) {
          list.push({
            id: `rem_${r.id}`,
            type: 'reminder',
            title: r.title,
            subtitle: r.notes,
            urgent: due <= now
          })
        }
      }
    })

    setTasks(list)
  }

  useEffect(() => {
    loadTasks().catch(() => {}).finally(() => setLoading(false))
  }, [])

  const handleDone = (id: string) => {
    haptic('medium')
    setDone(prev => new Set([...prev, id]))
    window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success')
  }

  const ICONS: Record<string, any> = {
    state: Zap, medication: Pill, visit: Stethoscope, reminder: Bell
  }

  const ICON_STYLES: Record<string, string> = {
    state: 'bg-amber-50 text-amber-500',
    medication: 'bg-blue-50 text-blue-400',
    visit: 'bg-red-50 text-red-400',
    reminder: 'bg-purple-50 text-purple-400',
  }

  const activeTasks = tasks.filter(t => !done.has(t.id))

  if (loading) return <div className="px-4 pt-6"><LoadingSpinner /></div>

  return (
    <div className="page-scroll h-full overflow-y-auto">
      <div className="px-4 pt-6 pb-4 space-y-4">
        <PageHeader title="Задачи" subtitle="Сейчас важно" />

        {activeTasks.length === 0 && (
          <GlassCard className="p-8 text-center">
            <div className="w-14 h-14 rounded-full bg-green-50 flex items-center justify-center mx-auto mb-3">
              <CheckSquare size={24} className="text-green-500" />
            </div>
            <p className="text-gray-600 font-semibold">Всё сделано!</p>
            <p className="text-sm text-gray-400 mt-1">Нет активных задач</p>
          </GlassCard>
        )}

        {activeTasks.length > 0 && (
          <div className="flex items-center justify-between px-1">
            <p className="text-xs text-gray-500">{activeTasks.length} задач{activeTasks.length === 1 ? 'а' : activeTasks.length < 5 ? 'и' : ''}</p>
            {tasks.filter(t => t.urgent && !done.has(t.id)).length > 0 && (
              <span className="badge bg-red-50 text-red-500 text-xs">⚡ {tasks.filter(t => t.urgent && !done.has(t.id)).length} срочных</span>
            )}
          </div>
        )}

        <div className="space-y-2">
          {activeTasks.map((task, i) => {
            const Icon = ICONS[task.type] || Bell
            const iconStyle = ICON_STYLES[task.type]
            return (
              <GlassCard key={task.id} delay={i * 0.04} className={`p-4 ${task.urgent ? 'border-amber-200/60' : ''}`}>
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-2xl flex items-center justify-center flex-shrink-0 ${iconStyle}`}>
                    <Icon size={16} />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-semibold text-gray-800">{task.title}</p>
                      {task.urgent && <span className="badge bg-amber-50 text-amber-500 text-[10px]">⚡</span>}
                    </div>
                    {task.subtitle && <p className="text-xs text-gray-500 mt-0.5">{task.subtitle}</p>}
                  </div>
                  <button
                    onClick={() => handleDone(task.id)}
                    className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center flex-shrink-0 active:scale-90 transition-transform"
                  >
                    <CheckSquare size={15} className="text-gray-400" />
                  </button>
                </div>
              </GlassCard>
            )
          })}
        </div>

        {done.size > 0 && (
          <div className="space-y-2">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider px-1">Выполнено</p>
            {tasks.filter(t => done.has(t.id)).map((task) => (
              <div key={task.id} className="glass-card-sm px-4 py-3 opacity-50 flex items-center gap-3">
                <div className="w-5 h-5 rounded-full bg-green-100 flex items-center justify-center">
                  <CheckSquare size={11} className="text-green-500" />
                </div>
                <p className="text-sm text-gray-500 line-through">{task.title}</p>
              </div>
            ))}
          </div>
        )}

        <div className="h-4" />
      </div>
    </div>
  )
}
