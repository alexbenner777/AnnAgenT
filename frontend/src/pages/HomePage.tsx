import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Zap, Heart, Calendar, Wallet, Activity, BookOpen,
  Users, Star, Mic, Bell, ChevronRight,
  Pill, Stethoscope, Gift, TrendingUp, ClipboardList
} from 'lucide-react'
import GlassCard from '../components/GlassCard'
import LoadingSpinner from '../components/LoadingSpinner'
import { dashboardApi } from '../api'
import { useUser } from '../App'

function getGreeting() {
  const h = new Date().getHours()
  if (h < 5) return 'Ночью'
  if (h < 12) return 'Доброе утро'
  if (h < 17) return 'Добрый день'
  if (h < 22) return 'Добрый вечер'
  return 'Поздний вечер'
}

function formatDate() {
  return new Date().toLocaleDateString('ru-RU', { weekday: 'long', day: 'numeric', month: 'long' })
}

export default function HomePage() {
  const { role, name } = useUser()
  const navigate = useNavigate()
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    dashboardApi.get()
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  // Urgent items — role-aware
  // Аня видит: незаполненное состояние, таблетки, ДР, напоминания, мед. визит
  // Ден видит: ДР и напоминания (общие), но не задачи по вводу данных
  const urgentItems: { text: string; onClick?: () => void }[] = []
  if (data) {
    if (role === 'anya') {
      if (!data.state_logged) urgentItems.push({ text: 'Внести состояние сегодня', onClick: () => navigate('/state') })
      if (data.medications_pending > 0) urgentItems.push({
        text: `Таблетки: ${data.medications_pending} ${data.medications_pending === 1 ? 'не принята' : 'не приняты'}`,
        onClick: () => navigate('/health')
      })
    }
    data.upcoming_birthdays?.forEach((b: any) => {
      if (b.days_until === 0) urgentItems.push({ text: `🎂 Сегодня ДР: ${b.name}`, onClick: () => navigate('/contacts') })
      else if (b.days_until <= 2) urgentItems.push({ text: `🎂 Через ${b.days_until} дн. ДР: ${b.name}`, onClick: () => navigate('/contacts') })
    })
    data.active_reminders?.forEach((r: any) => {
      urgentItems.push({ text: `⏰ ${r.title}`, onClick: () => navigate('/reminders') })
    })
    if (role === 'anya' && data.next_medical_visit) {
      urgentItems.push({
        text: `🏥 Ближайший визит: ${data.next_medical_visit.specialty} · ${data.next_medical_visit.visit_date}`,
        onClick: () => navigate('/health')
      })
    }
  }

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

        {/* Метрики — Готовность + Энергия (оба видят) */}
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
                <div
                  className="h-full rounded-full bg-gradient-to-r from-accent to-accent-light"
                  style={{ width: `${data.state.readiness_score}%` }}
                />
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
                <div
                  className="h-full rounded-full bg-gradient-to-r from-emerald-400 to-emerald-500"
                  style={{ width: `${(data.state.energy_subjective / 10) * 100}%` }}
                />
              </div>
            )}
          </GlassCard>
        </button>

        {/* Quick cards — роль-зависимые */}
        <div className="grid grid-cols-1 gap-3">

          {/* Для Дена: карточка-ссылка на сводку */}
          {role === 'den' && (
            <GlassCard delay={0.12} className="p-4" onClick={() => navigate('/briefing')}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-2xl bg-amber-50 flex items-center justify-center">
                    <BookOpen size={18} className="text-amber-500" />
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Брифинг и дайджест</p>
                    <p className="text-sm font-semibold text-gray-800">Открыть сводку дня</p>
                  </div>
                </div>
                <ChevronRight size={16} className="text-gray-300" />
              </div>
            </GlassCard>
          )}

          {/* Ближайший визит (только Аня) */}
          {role === 'anya' && data?.next_medical_visit && (
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
          {role === 'anya' && data?.medications_pending > 0 && (
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

          {/* Расходы за месяц (оба видят) */}
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

          {/* Именинники (оба видят) */}
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
        </div>

        <div className="h-4" />
      </div>
    </div>
  )
}
