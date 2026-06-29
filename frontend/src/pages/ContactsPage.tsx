import { useEffect, useState } from 'react'
import { Plus, Gift, Phone, ChevronRight, Search, Users } from 'lucide-react'
import GlassCard from '../components/GlassCard'
import PageHeader from '../components/PageHeader'
import LoadingSpinner from '../components/LoadingSpinner'
import { contactsApi } from '../api'

const CIRCLES = [
  { key: 'all', label: 'Все' },
  { key: 'core', label: '🔴 Ядро' },
  { key: 'close', label: '🟡 Близкий' },
  { key: 'work', label: '🟢 Рабочий' },
  { key: 'extended', label: '⚪ Расширенный' },
]

const CIRCLE_COLORS: Record<string, string> = {
  core: '#ef4444', close: '#eab308', work: '#22c55e', extended: '#9ca3af'
}

function haptic(s: 'light' | 'medium' = 'light') {
  window.Telegram?.WebApp?.HapticFeedback?.impactOccurred(s)
}

const ADD_STEPS = ['name', 'relation', 'circle', 'birthday', 'interests', 'city', 'done'] as const

export default function ContactsPage() {
  const [contacts, setContacts] = useState<any[]>([])
  const [birthdays, setBirthdays] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')
  const [search, setSearch] = useState('')
  const [showAdd, setShowAdd] = useState(false)
  const [addStep, setAddStep] = useState<typeof ADD_STEPS[number]>('name')
  const [newContact, setNewContact] = useState<any>({})
  const [stepInput, setStepInput] = useState('')

  useEffect(() => {
    Promise.all([
      contactsApi.getAll(),
      contactsApi.getBirthdays(7)
    ]).then(([c, b]) => { setContacts(c); setBirthdays(b) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const displayed = contacts
    .filter(c => filter === 'all' || c.circle === filter)
    .filter(c => !search || c.name.toLowerCase().includes(search.toLowerCase()))

  const handleAddStep = async () => {
    haptic()
    const fieldMap: Record<string, string> = {
      name: 'name', relation: 'relation', circle: 'circle',
      birthday: 'birthday', interests: 'interests', city: 'city'
    }
    if (addStep !== 'done') {
      const field = fieldMap[addStep]
      if (field && stepInput) {
        setNewContact((p: any) => ({...p, [field]: stepInput}))
      }
      const idx = ADD_STEPS.indexOf(addStep)
      const next = ADD_STEPS[idx + 1]
      setAddStep(next || 'done')
      setStepInput('')
    }
    if (addStep === 'city' || (addStep === ADD_STEPS[ADD_STEPS.length - 2])) {
      // Save
      const finalContact = {...newContact, city: stepInput || newContact.city}
      await contactsApi.add(finalContact)
      const updated = await contactsApi.getAll()
      setContacts(updated)
      setShowAdd(false)
      setAddStep('name')
      setNewContact({})
      setStepInput('')
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success')
    }
  }

  const STEP_PROMPTS: Record<string, string> = {
    name: 'Как зовут человека?',
    relation: 'Кто он/она? (партнёр, друг, клиент, семья...)',
    circle: 'Круг общения? (core/close/work/extended)',
    birthday: 'Дата рождения? (YYYY-MM-DD или пропустить)',
    interests: 'Интересы? (кратко через запятую)',
    city: 'Город? (или пропустить)',
  }

  if (loading) return <div className="px-4 pt-6"><LoadingSpinner /></div>

  return (
    <div className="page-scroll h-full overflow-y-auto">
      <div className="px-4 pt-6 pb-4 space-y-4">
        <PageHeader
          title="Контакты"
          subtitle="Сеть · Дни рождения · Подарки"
          action={
            <button onClick={() => { haptic(); setShowAdd(true) }} className="accent-button w-9 h-9 flex items-center justify-center">
              <Plus size={18} />
            </button>
          }
        />

        {/* Upcoming birthdays */}
        {birthdays.length > 0 && (
          <GlassCard delay={0.05} className="p-4">
            <div className="flex items-center gap-2 mb-3">
              <Gift size={15} className="text-pink-400" />
              <span className="font-semibold text-gray-800 text-sm">Скоро дни рождения</span>
            </div>
            {birthdays.map((b, i) => (
              <div key={b.id} className="flex items-center justify-between py-1.5 border-b border-gray-50 last:border-0">
                <div>
                  <span className="text-sm font-medium text-gray-800">{b.name}</span>
                  {b.days_until === 0 && <span className="ml-2 badge bg-pink-50 text-pink-500 text-xs">🎂 Сегодня!</span>}
                </div>
                <span className="text-xs text-gray-500">
                  {b.days_until === 0 ? '🎉' : `через ${b.days_until} дн.`}
                </span>
              </div>
            ))}
          </GlassCard>
        )}

        {/* Smart add form */}
        {showAdd && (
          <GlassCard className="p-4 space-y-3">
            <div className="flex items-center justify-between">
              <p className="font-semibold text-gray-800 text-sm">Новый контакт</p>
              <span className="text-xs text-gray-400">{ADD_STEPS.indexOf(addStep) + 1}/{ADD_STEPS.length - 1}</span>
            </div>
            {addStep !== 'done' && (
              <>
                <p className="text-sm text-gray-600">{STEP_PROMPTS[addStep]}</p>
                {Object.keys(newContact).length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {Object.entries(newContact).map(([k, v]: any) => (
                      <span key={k} className="badge bg-gray-100 text-gray-600 text-[10px]">{v as string}</span>
                    ))}
                  </div>
                )}
                <input
                  className="w-full bg-gray-50 rounded-xl px-3 py-2.5 text-sm outline-none border border-gray-200 focus:border-accent"
                  placeholder={addStep === 'birthday' ? '1985-03-15' : addStep === 'circle' ? 'core / close / work / extended' : 'Введите...'}
                  value={stepInput}
                  onChange={e => setStepInput(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleAddStep()}
                  autoFocus
                />
                <div className="flex gap-2">
                  <button onClick={() => { setShowAdd(false); setAddStep('name'); setNewContact({}) }} className="flex-1 py-2.5 rounded-xl bg-gray-100 text-gray-600 text-sm font-medium">Отмена</button>
                  <button onClick={handleAddStep} className="flex-1 py-2.5 rounded-xl accent-button text-sm">
                    {ADD_STEPS.indexOf(addStep) >= ADD_STEPS.length - 2 ? 'Сохранить' : 'Далее →'}
                  </button>
                </div>
              </>
            )}
          </GlassCard>
        )}

        {/* Search */}
        <div className="relative">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            className="w-full bg-white/60 backdrop-blur-sm rounded-2xl pl-9 pr-3 py-2.5 text-sm outline-none border border-white/60 placeholder-gray-400"
            placeholder="Поиск..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>

        {/* Circle filters */}
        <div className="flex gap-2 overflow-x-auto no-scrollbar">
          {CIRCLES.map(c => (
            <button
              key={c.key}
              onClick={() => { haptic(); setFilter(c.key) }}
              className={`flex-shrink-0 px-3 py-1.5 rounded-xl text-xs font-medium transition-all ${
                filter === c.key ? 'bg-accent text-white shadow-sm' : 'bg-white/60 text-gray-600'
              }`}
            >
              {c.label}
            </button>
          ))}
        </div>

        {/* Contacts list */}
        {displayed.length === 0 && (
          <GlassCard className="p-8 text-center">
            <Users size={28} className="mx-auto text-gray-200 mb-2" />
            <p className="text-gray-400 text-sm">Нет контактов</p>
          </GlassCard>
        )}

        <div className="space-y-2">
          {displayed.map((c, i) => (
            <GlassCard key={c.id} delay={i * 0.03} small className="px-4 py-3">
              <div className="flex items-center gap-3">
                <div
                  className="w-10 h-10 rounded-full flex items-center justify-center text-white text-sm font-bold flex-shrink-0"
                  style={{ background: `linear-gradient(135deg, ${CIRCLE_COLORS[c.circle] || '#9ca3af'}, ${CIRCLE_COLORS[c.circle] || '#9ca3af'}80)` }}
                >
                  {c.name[0]}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-semibold text-gray-800 truncate">{c.name}</p>
                    {c.days_until !== undefined && c.days_until <= 7 && (
                      <span className="badge bg-pink-50 text-pink-500 text-[10px]">🎂 {c.days_until === 0 ? 'сегодня' : `${c.days_until}д`}</span>
                    )}
                  </div>
                  <p className="text-xs text-gray-500 truncate">{c.relation}{c.city ? ` · ${c.city}` : ''}</p>
                  {c.interests && <p className="text-xs text-gray-400 truncate">{c.interests}</p>}
                </div>
                <ChevronRight size={14} className="text-gray-300 flex-shrink-0" />
              </div>
            </GlassCard>
          ))}
        </div>

        <div className="h-4" />
      </div>
    </div>
  )
}
