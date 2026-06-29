import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Plus, Check, SkipForward, Clock, Stethoscope, Pill, FlaskConical, ChevronDown, ChevronRight } from 'lucide-react'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer
} from 'recharts'
import GlassCard from '../components/GlassCard'
import PageHeader from '../components/PageHeader'
import LoadingSpinner from '../components/LoadingSpinner'
import { healthApi } from '../api'

type Tab = 'calendar' | 'meds' | 'labs'

const LOAD_COLOR: Record<string, string> = {
  high: '#ef4444', medium: '#eab308', low: '#22c55e', family: '#9ca3af', protected: '#9ca3af'
}

function haptic(s: 'light' | 'medium' = 'light') {
  window.Telegram?.WebApp?.HapticFeedback?.impactOccurred(s)
}

export default function HealthPage() {
  const [tab, setTab] = useState<Tab>('meds')
  const [visits, setVisits] = useState<any[]>([])
  const [meds, setMeds] = useState<any[]>([])
  const [labs, setLabs] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedLab, setExpandedLab] = useState<number | null>(null)
  const [showAddVisit, setShowAddVisit] = useState(false)
  const [showAddMed, setShowAddMed] = useState(false)
  const [newVisit, setNewVisit] = useState({ visit_date: '', doctor: '', specialty: '', reason: '' })
  const [newMed, setNewMed] = useState({ name: '', dosage: '', schedule_times: '' })

  useEffect(() => {
    Promise.all([healthApi.getVisits(), healthApi.getMedications(), healthApi.getLabs()])
      .then(([v, m, l]) => { setVisits(v); setMeds(m); setLabs(l) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const handleIntake = async (medId: number, scheduledAt: string, status: string) => {
    haptic('medium')
    await healthApi.logIntake(medId, { scheduled_at: scheduledAt, status })
    const updated = await healthApi.getMedications()
    setMeds(updated)
    window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success')
  }

  const handleAddVisit = async () => {
    await healthApi.addVisit(newVisit)
    setShowAddVisit(false)
    setNewVisit({ visit_date: '', doctor: '', specialty: '', reason: '' })
    const v = await healthApi.getVisits()
    setVisits(v)
  }

  const handleAddMed = async () => {
    await healthApi.addMedication({
      ...newMed,
      schedule_times: JSON.stringify(newMed.schedule_times.split(',').map(s => s.trim()))
    })
    setShowAddMed(false)
    setNewMed({ name: '', dosage: '', schedule_times: '' })
    const m = await healthApi.getMedications()
    setMeds(m)
  }

  const planned = visits.filter(v => v.status === 'planned')
  const done = visits.filter(v => v.status === 'done')

  return (
    <div className="page-scroll h-full overflow-y-auto">
      <div className="px-4 pt-6 pb-4 space-y-4">
        <PageHeader
          title="Здоровье"
          subtitle="Медкалендарь · Препараты · Анализы"
          action={
            <button
              onClick={() => tab === 'calendar' ? setShowAddVisit(true) : tab === 'meds' ? setShowAddMed(true) : undefined}
              className="accent-button w-9 h-9 flex items-center justify-center"
            >
              <Plus size={18} />
            </button>
          }
        />

        {/* Tabs */}
        <div className="glass-card-sm p-1 flex gap-1">
          {[
            { key: 'meds', label: '💊 Препараты' },
            { key: 'calendar', label: '🏥 Визиты' },
            { key: 'labs', label: '🔬 Анализы' },
          ].map(t => (
            <button
              key={t.key}
              onClick={() => setTab(t.key as Tab)}
              className={`flex-1 py-2.5 px-2 rounded-xl text-xs font-semibold transition-all ${
                tab === t.key
                  ? 'bg-white shadow-sm text-accent'
                  : 'text-gray-500'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {loading && <LoadingSpinner />}

        {/* MEDICATIONS */}
        {!loading && tab === 'meds' && (
          <div className="space-y-3">
            {meds.length === 0 && (
              <GlassCard className="p-6 text-center">
                <p className="text-gray-400 text-sm">Нет активных препаратов</p>
              </GlassCard>
            )}
            {meds.map((med, i) => {
              const pending = med.today_log?.filter((l: any) => l.status === 'pending') || []
              const taken = med.today_log?.filter((l: any) => l.status === 'taken') || []
              return (
                <GlassCard key={med.id} delay={i * 0.05} className="p-4">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-base font-semibold text-gray-800">{med.name}</span>
                        {med.is_critical ? <span className="badge bg-red-50 text-red-500">❗</span> : null}
                      </div>
                      <p className="text-xs text-gray-500 mt-0.5">{med.dosage} · {med.with_food === 'with' ? 'во время еды' : med.with_food === 'before' ? 'до еды' : 'после еды'}</p>
                    </div>
                    <div className="flex gap-1">
                      {taken.length > 0 && <span className="badge bg-green-50 text-green-600">✓ {taken.length}</span>}
                      {pending.length > 0 && <span className="badge bg-amber-50 text-amber-600">⏳ {pending.length}</span>}
                    </div>
                  </div>
                  {pending.length > 0 && (
                    <div className="space-y-2">
                      {pending.map((log: any) => (
                        <div key={log.scheduled_at} className="bg-gray-50/80 rounded-2xl p-3">
                          <p className="text-xs text-gray-500 mb-2">
                            {new Date(log.scheduled_at).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}
                          </p>
                          <div className="flex gap-2">
                            <button
                              onClick={() => handleIntake(med.id, log.scheduled_at, 'taken')}
                              className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl bg-green-50 text-green-600 text-xs font-semibold active:scale-95 transition-transform"
                            >
                              <Check size={13} /> Принял
                            </button>
                            <button
                              onClick={() => handleIntake(med.id, log.scheduled_at, 'skipped')}
                              className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl bg-gray-100 text-gray-500 text-xs font-semibold active:scale-95 transition-transform"
                            >
                              <SkipForward size={13} /> Пропустить
                            </button>
                            <button
                              onClick={() => handleIntake(med.id, log.scheduled_at, 'snoozed')}
                              className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl bg-amber-50 text-amber-600 text-xs font-semibold active:scale-95 transition-transform"
                            >
                              <Clock size={13} /> +15м
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                  {med.supply_units && (
                    <p className="text-xs text-gray-400 mt-2">Запас: {med.supply_units} шт.</p>
                  )}
                </GlassCard>
              )
            })}

            {showAddMed && (
              <GlassCard className="p-4 space-y-3">
                <p className="font-semibold text-gray-800 text-sm">Добавить препарат</p>
                <input className="w-full bg-gray-50 rounded-xl px-3 py-2.5 text-sm outline-none border border-gray-200 focus:border-accent"
                  placeholder="Название препарата" value={newMed.name} onChange={e => setNewMed(p => ({...p, name: e.target.value}))} />
                <input className="w-full bg-gray-50 rounded-xl px-3 py-2.5 text-sm outline-none border border-gray-200 focus:border-accent"
                  placeholder="Дозировка (напр. 400 мг)" value={newMed.dosage} onChange={e => setNewMed(p => ({...p, dosage: e.target.value}))} />
                <input className="w-full bg-gray-50 rounded-xl px-3 py-2.5 text-sm outline-none border border-gray-200 focus:border-accent"
                  placeholder="Время приёма через запятую (09:00, 21:00)" value={newMed.schedule_times} onChange={e => setNewMed(p => ({...p, schedule_times: e.target.value}))} />
                <div className="flex gap-2">
                  <button onClick={() => setShowAddMed(false)} className="flex-1 py-2.5 rounded-xl bg-gray-100 text-gray-600 text-sm font-medium">Отмена</button>
                  <button onClick={handleAddMed} className="flex-1 py-2.5 rounded-xl accent-button text-sm">Добавить</button>
                </div>
              </GlassCard>
            )}
          </div>
        )}

        {/* MEDICAL CALENDAR */}
        {!loading && tab === 'calendar' && (
          <div className="space-y-3">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider px-1">Предстоящие</p>
            {planned.map((v, i) => (
              <GlassCard key={v.id} delay={i * 0.05} className="p-4">
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 rounded-2xl bg-blue-50 flex items-center justify-center flex-shrink-0">
                    <Stethoscope size={18} className="text-blue-400" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <p className="font-semibold text-gray-800 text-sm">{v.specialty}</p>
                      <span className="badge bg-blue-50 text-blue-600 text-[10px]">Запланировано</span>
                    </div>
                    <p className="text-xs text-gray-600 mt-0.5">{v.doctor}</p>
                    {v.visit_date && <p className="text-xs text-gray-500 mt-0.5">📅 {v.visit_date}</p>}
                    {v.schedule_pattern && <p className="text-xs text-gray-500 mt-0.5">🔄 {v.schedule_pattern}</p>}
                    {v.reason && <p className="text-xs text-gray-400 mt-1">{v.reason}</p>}
                  </div>
                </div>
              </GlassCard>
            ))}

            {done.length > 0 && (
              <>
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider px-1 mt-2">Прошедшие</p>
                {done.map((v, i) => (
                  <GlassCard key={v.id} delay={i * 0.05} className="p-4 opacity-75">
                    <div className="flex items-start gap-3">
                      <div className="w-10 h-10 rounded-2xl bg-gray-100 flex items-center justify-center flex-shrink-0">
                        <Stethoscope size={18} className="text-gray-400" />
                      </div>
                      <div>
                        <p className="font-semibold text-gray-700 text-sm">{v.specialty}</p>
                        <p className="text-xs text-gray-500">{v.doctor} · {v.visit_date}</p>
                        {v.outcome && <p className="text-xs text-gray-500 mt-1">{v.outcome}</p>}
                      </div>
                    </div>
                  </GlassCard>
                ))}
              </>
            )}

            {showAddVisit && (
              <GlassCard className="p-4 space-y-3">
                <p className="font-semibold text-gray-800 text-sm">Добавить визит</p>
                <input className="w-full bg-gray-50 rounded-xl px-3 py-2.5 text-sm outline-none border border-gray-200 focus:border-accent"
                  placeholder="Специальность (кардиолог, стоматолог...)" value={newVisit.specialty} onChange={e => setNewVisit(p => ({...p, specialty: e.target.value}))} />
                <input className="w-full bg-gray-50 rounded-xl px-3 py-2.5 text-sm outline-none border border-gray-200 focus:border-accent"
                  placeholder="ФИО врача" value={newVisit.doctor} onChange={e => setNewVisit(p => ({...p, doctor: e.target.value}))} />
                <input className="w-full bg-gray-50 rounded-xl px-3 py-2.5 text-sm outline-none border border-gray-200 focus:border-accent"
                  type="date" value={newVisit.visit_date} onChange={e => setNewVisit(p => ({...p, visit_date: e.target.value}))} />
                <input className="w-full bg-gray-50 rounded-xl px-3 py-2.5 text-sm outline-none border border-gray-200 focus:border-accent"
                  placeholder="Повод / причина" value={newVisit.reason} onChange={e => setNewVisit(p => ({...p, reason: e.target.value}))} />
                <div className="flex gap-2">
                  <button onClick={() => setShowAddVisit(false)} className="flex-1 py-2.5 rounded-xl bg-gray-100 text-gray-600 text-sm font-medium">Отмена</button>
                  <button onClick={handleAddVisit} className="flex-1 py-2.5 rounded-xl accent-button text-sm">Добавить</button>
                </div>
              </GlassCard>
            )}
          </div>
        )}

        {/* LABS */}
        {!loading && tab === 'labs' && (
          <div className="space-y-3">
            {labs.map((panel, i) => (
              <GlassCard key={panel.id} delay={i * 0.05} className="p-4">
                <button
                  className="w-full flex items-center justify-between"
                  onClick={() => setExpandedLab(expandedLab === panel.id ? null : panel.id)}
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-2xl bg-purple-50 flex items-center justify-center">
                      <FlaskConical size={18} className="text-purple-400" />
                    </div>
                    <div className="text-left">
                      <p className="font-semibold text-gray-800 text-sm">{panel.lab_name || 'Лаборатория'}</p>
                      <p className="text-xs text-gray-500">{panel.taken_on}</p>
                    </div>
                  </div>
                  {expandedLab === panel.id ? <ChevronDown size={16} className="text-gray-400" /> : <ChevronRight size={16} className="text-gray-400" />}
                </button>

                {expandedLab === panel.id && panel.results && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    className="mt-3 space-y-2 overflow-hidden"
                  >
                    {panel.results.map((r: any) => (
                      <div key={r.id} className="flex items-center justify-between py-2 border-t border-gray-100">
                        <div>
                          <p className="text-sm text-gray-700">{r.marker}</p>
                          <p className="text-xs text-gray-400">{r.ref_low}–{r.ref_high} {r.unit}</p>
                        </div>
                        <div className="text-right">
                          <p className={`text-sm font-bold ${r.flag === 'low' ? 'text-blue-500' : r.flag === 'high' ? 'text-red-500' : 'text-green-600'}`}>
                            {r.value_text || r.value} {r.unit}
                          </p>
                          {r.flag && r.flag !== 'normal' && (
                            <span className={`badge text-[10px] ${r.flag === 'low' ? 'bg-blue-50 text-blue-500' : 'bg-red-50 text-red-500'}`}>
                              {r.flag === 'low' ? '↓ Низко' : '↑ Высоко'}
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </motion.div>
                )}
              </GlassCard>
            ))}
            {labs.length === 0 && (
              <GlassCard className="p-6 text-center">
                <p className="text-gray-400 text-sm">Нет загруженных анализов</p>
                <p className="text-xs text-gray-300 mt-1">Загрузите фото или PDF бланка</p>
              </GlassCard>
            )}
          </div>
        )}

        <div className="h-4" />
      </div>
    </div>
  )
}
