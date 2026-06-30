import { useEffect, useState } from 'react'
import { Save, User, Clock, Star, Link, Shield, FlaskConical } from 'lucide-react'
import GlassCard from '../components/GlassCard'
import PageHeader from '../components/PageHeader'
import LoadingSpinner from '../components/LoadingSpinner'
import { settingsApi, briefingApi } from '../api'
import { useUser } from '../App'

function haptic(s: 'light' | 'medium' = 'light') {
  window.Telegram?.WebApp?.HapticFeedback?.impactOccurred(s)
}

export default function SettingsPage() {
  const { role, setRole, name } = useUser()
  const [settings, setSettings] = useState<any>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [testBriefing, setTestBriefing] = useState<'idle' | 'loading' | 'done' | 'error'>('idle')
  const [form, setForm] = useState({
    natal_date: '',
    natal_time: '',
    natal_city: '',
    briefing_morning_time: '07:00',
    briefing_evening_time: '22:00',
    readiness_threshold: '60',
    oura_token: '',
    gcal_ical_url: '',
  })

  useEffect(() => {
    settingsApi.get()
      .then(s => {
        setSettings(s)
        setForm(prev => ({ ...prev, ...s }))
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const handleSave = async () => {
    setSaving(true)
    haptic('medium')
    try {
      await settingsApi.update(form)
      setSaved(true)
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success')
      setTimeout(() => setSaved(false), 2000)
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div className="px-4 pt-6"><LoadingSpinner /></div>

  return (
    <div className="page-scroll h-full overflow-y-auto">
      <div className="px-4 pt-6 pb-4 space-y-4">
        <PageHeader
          title="Настройки"
          action={
            <button onClick={handleSave} disabled={saving} className="accent-button flex items-center gap-1.5 px-3 py-2 text-sm">
              {saved ? '✓ Сохранено' : saving ? 'Сохраняем...' : <><Save size={14} /> Сохранить</>}
            </button>
          }
        />

        {/* Role switcher */}
        <GlassCard delay={0.05} className="p-4">
          <div className="flex items-center gap-2 mb-3">
            <Shield size={15} className="text-accent" />
            <p className="font-semibold text-gray-800 text-sm">Роль</p>
          </div>
          <div className="glass-card-sm p-1 flex gap-1">
            <button
              onClick={() => { haptic(); setRole('anya') }}
              className={`flex-1 py-2.5 rounded-xl text-sm font-medium transition-all ${role === 'anya' ? 'bg-white shadow-sm text-accent' : 'text-gray-500'}`}
            >
              👩‍💼 Аня (ассистент)
            </button>
            <button
              onClick={() => { haptic(); setRole('den') }}
              className={`flex-1 py-2.5 rounded-xl text-sm font-medium transition-all ${role === 'den' ? 'bg-white shadow-sm text-accent' : 'text-gray-500'}`}
            >
              👨‍💻 Ден (босс)
            </button>
          </div>
          <p className="text-xs text-gray-400 mt-2">
            {role === 'anya' ? '✅ Видите все разделы, включая Здоровье' : '✅ Видите все разделы кроме Здоровья'}
          </p>
        </GlassCard>

        {/* Natal data */}
        <GlassCard delay={0.08} className="p-4 space-y-3">
          <div className="flex items-center gap-2">
            <Star size={15} className="text-amber-400" />
            <p className="font-semibold text-gray-800 text-sm">Натальные данные</p>
          </div>
          <input
            className="w-full bg-gray-50 rounded-xl px-3 py-2.5 text-sm outline-none border border-gray-200 focus:border-accent"
            placeholder="Дата рождения (YYYY-MM-DD)"
            type="date"
            value={form.natal_date}
            onChange={e => setForm(p => ({...p, natal_date: e.target.value}))}
          />
          <input
            className="w-full bg-gray-50 rounded-xl px-3 py-2.5 text-sm outline-none border border-gray-200 focus:border-accent"
            placeholder="Время рождения (HH:MM)"
            type="time"
            value={form.natal_time}
            onChange={e => setForm(p => ({...p, natal_time: e.target.value}))}
          />
          <input
            className="w-full bg-gray-50 rounded-xl px-3 py-2.5 text-sm outline-none border border-gray-200 focus:border-accent"
            placeholder="Город рождения"
            value={form.natal_city}
            onChange={e => setForm(p => ({...p, natal_city: e.target.value}))}
          />
        </GlassCard>

        {/* Briefing times */}
        <GlassCard delay={0.11} className="p-4 space-y-3">
          <div className="flex items-center gap-2">
            <Clock size={15} className="text-accent" />
            <p className="font-semibold text-gray-800 text-sm">Время брифингов</p>
          </div>
          <div className="flex gap-3">
            <div className="flex-1">
              <p className="text-xs text-gray-500 mb-1">Утренний</p>
              <input
                className="w-full bg-gray-50 rounded-xl px-3 py-2.5 text-sm outline-none border border-gray-200 focus:border-accent"
                type="time"
                value={form.briefing_morning_time}
                onChange={e => setForm(p => ({...p, briefing_morning_time: e.target.value}))}
              />
            </div>
            <div className="flex-1">
              <p className="text-xs text-gray-500 mb-1">Вечерний</p>
              <input
                className="w-full bg-gray-50 rounded-xl px-3 py-2.5 text-sm outline-none border border-gray-200 focus:border-accent"
                type="time"
                value={form.briefing_evening_time}
                onChange={e => setForm(p => ({...p, briefing_evening_time: e.target.value}))}
              />
            </div>
          </div>
          <div>
            <p className="text-xs text-gray-500 mb-1">Порог Readiness для алерта</p>
            <input
              className="w-full bg-gray-50 rounded-xl px-3 py-2.5 text-sm outline-none border border-gray-200 focus:border-accent"
              type="number"
              min={0} max={100}
              placeholder="60"
              value={form.readiness_threshold}
              onChange={e => setForm(p => ({...p, readiness_threshold: e.target.value}))}
            />
          </div>
        </GlassCard>

        {/* Integrations */}
        <GlassCard delay={0.14} className="p-4 space-y-3">
          <div className="flex items-center gap-2">
            <Link size={15} className="text-accent" />
            <p className="font-semibold text-gray-800 text-sm">Интеграции</p>
          </div>
          <div>
            <p className="text-xs text-gray-500 mb-1">Oura / Aura токен</p>
            <input
              className="w-full bg-gray-50 rounded-xl px-3 py-2.5 text-sm outline-none border border-gray-200 focus:border-accent"
              placeholder="Токен Oura Ring API"
              type="password"
              value={form.oura_token}
              onChange={e => setForm(p => ({...p, oura_token: e.target.value}))}
            />
          </div>
          <div>
            <p className="text-xs text-gray-500 mb-1">Google Calendar iCal ссылка</p>
            <input
              className="w-full bg-gray-50 rounded-xl px-3 py-2.5 text-sm outline-none border border-gray-200 focus:border-accent"
              placeholder="https://calendar.google.com/calendar/ical/..."
              value={form.gcal_ical_url}
              onChange={e => setForm(p => ({...p, gcal_ical_url: e.target.value}))}
            />
          </div>
        </GlassCard>

        {/* Domain access */}
        <GlassCard delay={0.17} className="p-4">
          <div className="flex items-center gap-2 mb-3">
            <User size={15} className="text-accent" />
            <p className="font-semibold text-gray-800 text-sm">Доступ по доменам</p>
          </div>
          <div className="space-y-2">
            {[
              { domain: 'Здоровье', anya: true, den: false },
              { domain: 'Состояние', anya: true, den: true },
              { domain: 'Сводка', anya: true, den: true },
              { domain: 'Календарь', anya: true, den: true },
              { domain: 'Финансы', anya: true, den: true },
              { domain: 'Контакты', anya: true, den: true },
              { domain: 'Качество дня', anya: true, den: true },
              { domain: 'Встречи', anya: true, den: true },
            ].map(item => (
              <div key={item.domain} className="flex items-center justify-between py-1.5 border-b border-gray-50 last:border-0">
                <span className="text-sm text-gray-700">{item.domain}</span>
                <div className="flex gap-3">
                  <span className={`text-xs font-medium ${item.anya ? 'text-green-500' : 'text-gray-300'}`}>Аня {item.anya ? '✓' : '✗'}</span>
                  <span className={`text-xs font-medium ${item.den ? 'text-blue-500' : 'text-gray-300'}`}>Ден {item.den ? '✓' : '✗'}</span>
                </div>
              </div>
            ))}
          </div>
        </GlassCard>

        {/* Dev / Test tools */}
        <GlassCard delay={0.20} className="p-4 space-y-3">
          <div className="flex items-center gap-2">
            <FlaskConical size={15} className="text-violet-400" />
            <p className="font-semibold text-gray-800 text-sm">Разработка</p>
          </div>
          <button
            onClick={async () => {
              haptic('medium')
              setTestBriefing('loading')
              try {
                await briefingApi.testTrigger()
                setTestBriefing('done')
                setTimeout(() => setTestBriefing('idle'), 3000)
                window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success')
              } catch {
                setTestBriefing('error')
                setTimeout(() => setTestBriefing('idle'), 3000)
              }
            }}
            disabled={testBriefing === 'loading'}
            className="w-full py-3 rounded-2xl text-sm font-semibold border border-violet-200 text-violet-600 bg-violet-50 flex items-center justify-center gap-2 disabled:opacity-50"
          >
            <FlaskConical size={14} />
            {testBriefing === 'idle' && 'Тест: запустить бриф сейчас'}
            {testBriefing === 'loading' && 'Генерирую…'}
            {testBriefing === 'done' && '✓ Бриф отправлен в Telegram'}
            {testBriefing === 'error' && '⚠️ Ошибка — попробуй ещё раз'}
          </button>
          <p className="text-xs text-gray-400">Генерирует брифинг по текущим данным и отправляет в Telegram. Только для проверки.</p>
        </GlassCard>

        <div className="h-4" />
      </div>
    </div>
  )
}

