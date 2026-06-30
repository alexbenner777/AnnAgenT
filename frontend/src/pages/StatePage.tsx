import { useEffect, useState } from 'react'
import { Check, X, Save } from 'lucide-react'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
} from 'recharts'
import GlassCard from '../components/GlassCard'
import PageHeader from '../components/PageHeader'
import LoadingSpinner from '../components/LoadingSpinner'
import { stateApi } from '../api'
import { useUser } from '../App'

function haptic(s: 'light' | 'medium' = 'light') {
  window.Telegram?.WebApp?.HapticFeedback?.impactOccurred(s)
}

interface SliderProps {
  label: string; value: number; onChange: (v: number) => void; max?: number; color?: string
  readOnly?: boolean
}
function Slider({ label, value, onChange, max = 10, color = '#5B9DB8', readOnly }: SliderProps) {
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-700">{label}</span>
        <span className="text-2xl font-bold" style={{ color }}>{value}<span className="text-sm text-gray-400 font-normal">/{max}</span></span>
      </div>
      <div className="relative h-6 flex items-center">
        <div className="h-2 w-full bg-gray-100 rounded-full overflow-hidden">
          <div className="h-full rounded-full transition-all" style={{ width: `${(value / max) * 100}%`, background: `linear-gradient(90deg, ${color}80, ${color})` }} />
        </div>
        {!readOnly && (
          <input
            type="range" min={1} max={max} value={value}
            onChange={e => { haptic('light'); onChange(parseInt(e.target.value)) }}
            className="absolute inset-0 w-full opacity-0 cursor-pointer h-6"
          />
        )}
      </div>
    </div>
  )
}

interface ToggleProps { label: string; value: boolean; onChange: (v: boolean) => void; emoji?: string; readOnly?: boolean }
function Toggle({ label, value, onChange, emoji, readOnly }: ToggleProps) {
  return (
    <button
      onClick={() => { if (!readOnly) { haptic(); onChange(!value) } }}
      disabled={readOnly}
      className={`flex items-center justify-between p-3 rounded-2xl transition-all ${
        readOnly ? 'cursor-default' : 'active:scale-95'
      } ${value ? 'bg-accent/10 border border-accent/20' : 'bg-gray-50 border border-transparent'}`}
    >
      <div className="flex items-center gap-2">
        {emoji && <span className="text-base">{emoji}</span>}
        <span className={`text-sm font-medium ${value ? 'text-accent' : 'text-gray-600'}`}>{label}</span>
      </div>
      <div className={`w-5 h-5 rounded-full flex items-center justify-center ${value ? 'bg-accent' : 'bg-gray-200'}`}>
        {value ? <Check size={12} className="text-white" /> : <X size={12} className="text-gray-400" />}
      </div>
    </button>
  )
}

export default function StatePage() {
  const { role } = useUser()
  const isAnya = role === 'anya'

  const [history, setHistory] = useState<any[]>([])
  const [today, setToday] = useState<any>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  const [form, setForm] = useState({
    energy_subjective: 7,
    sleep_score: 70,
    workout_done: false,
    massage_done: false,
    alcohol: false,
  })

  useEffect(() => {
    Promise.all([stateApi.getHistory(7), stateApi.getToday()])
      .then(([hist, tod]) => {
        setHistory(hist)
        if (tod && tod.energy_subjective !== null) {
          setForm({
            energy_subjective: tod.energy_subjective || 7,
            sleep_score: tod.sleep_score || 70,
            workout_done: !!tod.workout_done,
            massage_done: !!tod.massage_done,
            alcohol: !!tod.alcohol,
          })
        }
        setToday(tod)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const handleSave = async () => {
    setSaving(true)
    haptic('medium')
    try {
      await stateApi.logState({
        ...form,
        workout_done: form.workout_done ? 1 : 0,
        massage_done: form.massage_done ? 1 : 0,
        alcohol: form.alcohol ? 1 : 0,
      })
      setSaved(true)
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success')
      setTimeout(() => setSaved(false), 2000)
    } finally {
      setSaving(false)
    }
  }

  const chartData = history.map(d => ({
    date: d.date?.slice(5),
    Энергия: d.energy_subjective,
    Сон: d.sleep_score,
    Готовность: d.readiness_score,
    HRV: d.hrv_avg ? Math.round(d.hrv_avg) : null,
  }))

  if (loading) return <div className="px-4 pt-6"><LoadingSpinner /></div>

  return (
    <div className="page-scroll h-full overflow-y-auto">
      <div className="px-4 pt-6 pb-4 space-y-4">
        <PageHeader
          title="Состояние"
          subtitle={isAnya ? 'Neuro & Bio · ввод данных' : 'Neuro & Bio · динамика'}
        />

        {/* Форма — только Аня вводит данные */}
        <GlassCard delay={0.05} className="p-5 space-y-5">
          <div className="flex items-center justify-between">
            <p className="font-semibold text-gray-800">Сегодня</p>
            {isAnya && saved && <span className="badge bg-green-50 text-green-600 text-xs">✓ Сохранено</span>}
            {!isAnya && <span className="badge bg-gray-100 text-gray-500 text-xs">Вводит Аня</span>}
          </div>

          <Slider
            label="Энергия"
            value={form.energy_subjective}
            onChange={v => setForm(p => ({...p, energy_subjective: v}))}
            color="#5B9DB8"
            readOnly={!isAnya}
          />
          <Slider
            label="Качество сна"
            value={form.sleep_score}
            onChange={v => setForm(p => ({...p, sleep_score: v}))}
            max={100}
            color="#86C1AD"
            readOnly={!isAnya}
          />

          <div className="space-y-2">
            <Toggle label="Тренировка" value={form.workout_done} onChange={v => setForm(p => ({...p, workout_done: v}))} emoji="🏃" readOnly={!isAnya} />
            <Toggle label="Массаж" value={form.massage_done} onChange={v => setForm(p => ({...p, massage_done: v}))} emoji="💆" readOnly={!isAnya} />
            <Toggle label="Алкоголь вчера" value={form.alcohol} onChange={v => setForm(p => ({...p, alcohol: v}))} emoji="🍷" readOnly={!isAnya} />
          </div>

          {isAnya && (
            <button
              onClick={handleSave}
              disabled={saving}
              className="w-full accent-button py-3 flex items-center justify-center gap-2"
            >
              <Save size={16} />
              {saving ? 'Сохраняем...' : 'Сохранить состояние'}
            </button>
          )}
        </GlassCard>

        {/* Oura-данные */}
        {(today?.readiness_score || today?.hrv_avg) && (
          <div className="grid grid-cols-2 gap-3">
            {today.readiness_score && (
              <GlassCard delay={0.1} className="p-4 text-center">
                <p className="text-xs text-gray-500 mb-1">Oura Readiness</p>
                <p className="text-4xl font-bold text-gray-900">{today.readiness_score}</p>
                <div className="mt-2 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                  <div className="h-full bg-purple-400 rounded-full" style={{ width: `${today.readiness_score}%` }} />
                </div>
              </GlassCard>
            )}
            {today.hrv_avg && (
              <GlassCard delay={0.12} className="p-4 text-center">
                <p className="text-xs text-gray-500 mb-1">HRV средний</p>
                <p className="text-4xl font-bold text-gray-900">{Math.round(today.hrv_avg)}</p>
                <p className="text-xs text-gray-400 mt-1">мс</p>
              </GlassCard>
            )}
            {today.sleep_hours && (
              <GlassCard delay={0.14} className="p-4 text-center">
                <p className="text-xs text-gray-500 mb-1">Часы сна</p>
                <p className="text-4xl font-bold text-gray-900">{today.sleep_hours.toFixed(1)}</p>
                <p className="text-xs text-gray-400 mt-1">ч</p>
              </GlassCard>
            )}
            {today.heart_rate_avg && (
              <GlassCard delay={0.16} className="p-4 text-center">
                <p className="text-xs text-gray-500 mb-1">ЧСС средняя</p>
                <p className="text-4xl font-bold text-gray-900">{today.heart_rate_avg}</p>
                <p className="text-xs text-gray-400 mt-1">уд/мин</p>
              </GlassCard>
            )}
          </div>
        )}

        {/* Графики за 7 дней */}
        {chartData.length > 0 && (
          <>
            <GlassCard delay={0.18} className="p-4">
              <p className="font-semibold text-gray-800 text-sm mb-3">Энергия — 7 дней <span className="text-xs text-gray-400 font-normal">(из 10)</span></p>
              <ResponsiveContainer width="100%" height={100}>
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="energyGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#5B9DB8" stopOpacity={0.25} />
                      <stop offset="100%" stopColor="#5B9DB8" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#9ca3af' }} axisLine={false} tickLine={false} />
                  <YAxis domain={[0, 10]} hide />
                  <Tooltip
                    contentStyle={{ background: 'rgba(255,255,255,0.95)', border: 'none', borderRadius: 12, fontSize: 11 }}
                    labelStyle={{ fontWeight: 600 }}
                  />
                  <Area type="monotone" dataKey="Энергия" stroke="#5B9DB8" strokeWidth={2} fill="url(#energyGrad)" dot={false} />
                </AreaChart>
              </ResponsiveContainer>
            </GlassCard>

            <GlassCard delay={0.2} className="p-4">
              <p className="font-semibold text-gray-800 text-sm mb-3">Готовность и Сон — 7 дней <span className="text-xs text-gray-400 font-normal">(из 100)</span></p>
              <ResponsiveContainer width="100%" height={120}>
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="readGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#B8A0D4" stopOpacity={0.25} />
                      <stop offset="100%" stopColor="#B8A0D4" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="sleepGrad2" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#86C1AD" stopOpacity={0.25} />
                      <stop offset="100%" stopColor="#86C1AD" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#9ca3af' }} axisLine={false} tickLine={false} />
                  <YAxis domain={[0, 100]} hide />
                  <Tooltip
                    contentStyle={{ background: 'rgba(255,255,255,0.95)', border: 'none', borderRadius: 12, fontSize: 11 }}
                  />
                  <Area type="monotone" dataKey="Готовность" stroke="#B8A0D4" strokeWidth={2} fill="url(#readGrad)" dot={false} />
                  <Area type="monotone" dataKey="Сон" stroke="#86C1AD" strokeWidth={2} fill="url(#sleepGrad2)" dot={false} />
                </AreaChart>
              </ResponsiveContainer>
            </GlassCard>
          </>
        )}

        <div className="h-4" />
      </div>
    </div>
  )
}
