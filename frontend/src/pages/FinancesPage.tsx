import { useEffect, useState } from 'react'
import { Plus, TrendingDown, TrendingUp, AlertCircle, Send } from 'lucide-react'
import { useUser } from '../App'
import {
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip,
  AreaChart, Area, XAxis, YAxis
} from 'recharts'
import GlassCard from '../components/GlassCard'
import PageHeader from '../components/PageHeader'
import LoadingSpinner from '../components/LoadingSpinner'
import { financesApi } from '../api'

const COLORS = ['#5B9DB8', '#86C1AD', '#E4D2B3', '#B8A0D4', '#F0A0A0', '#A0C4F0', '#A0D4A0']

const CATEGORIES = ['Еда', 'Транспорт', 'Рестораны', 'Здоровье', 'Развлечения', 'Образование', 'Другое']

function haptic(s: 'light' | 'medium' = 'light') {
  window.Telegram?.WebApp?.HapticFeedback?.impactOccurred(s)
}

export default function FinancesPage() {
  const { role } = useUser()
  const isAnya = role === 'anya'
  const [summary, setSummary] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [showAddExpense, setShowAddExpense] = useState(false)
  const [newExp, setNewExp] = useState({ amount: '', category: '', description: '' })
  const [freeText, setFreeText] = useState('')
  const [addMode, setAddMode] = useState<'quick' | 'form'>('quick')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    financesApi.getSummary()
      .then(setSummary)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const parseQuickExpense = (text: string) => {
    const match = text.match(/(\d+(?:\.\d+)?)\s*,?\s*(.+)?/)
    if (match) {
      return { amount: match[1], description: match[2]?.trim() || '', category: '' }
    }
    return null
  }

  const handleQuickAdd = async () => {
    const parsed = parseQuickExpense(freeText)
    if (!parsed) return
    setSaving(true)
    haptic('medium')
    try {
      await financesApi.addExpense({ ...parsed, amount: parseFloat(parsed.amount) })
      const s = await financesApi.getSummary()
      setSummary(s)
      setFreeText('')
      setShowAddExpense(false)
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success')
    } finally {
      setSaving(false)
    }
  }

  const handleFormAdd = async () => {
    if (!newExp.amount) return
    setSaving(true)
    haptic('medium')
    try {
      await financesApi.addExpense({ ...newExp, amount: parseFloat(newExp.amount) })
      const s = await financesApi.getSummary()
      setSummary(s)
      setNewExp({ amount: '', category: '', description: '' })
      setShowAddExpense(false)
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success')
    } finally {
      setSaving(false)
    }
  }

  const formatMoney = (n: number) => new Intl.NumberFormat('ru-RU').format(Math.round(n)) + ' ₽'

  const getLimitStatus = (category: string) => {
    const cat = summary?.by_category?.find((c: any) => c.category === category)
    const lim = summary?.limits?.find((l: any) => l.category === category)
    if (!cat || !lim) return null
    const pct = (cat.total / lim.monthly_limit) * 100
    return { spent: cat.total, limit: lim.monthly_limit, pct, over: pct > 100 }
  }

  if (loading) return <div className="px-4 pt-6"><LoadingSpinner /></div>

  return (
    <div className="page-scroll h-full overflow-y-auto">
      <div className="px-4 pt-6 pb-4 space-y-4">
        <PageHeader
          title="Финансы"
          subtitle={new Date().toLocaleDateString('ru-RU', { month: 'long', year: 'numeric' })}
          action={isAnya ? (
            <button
              onClick={() => { haptic(); setShowAddExpense(true) }}
              className="accent-button flex items-center gap-1.5 px-3 py-2 text-sm"
            >
              <Plus size={15} /> Расход
            </button>
          ) : undefined}
        />

        {/* Quick add floating — только Аня */}
        {isAnya && showAddExpense && (
          <GlassCard className="p-4 space-y-3">
            <div className="flex items-center justify-between">
              <p className="font-semibold text-gray-800 text-sm">Внести расход</p>
              <div className="flex gap-1 glass-card-sm p-0.5">
                <button
                  onClick={() => setAddMode('quick')}
                  className={`px-3 py-1.5 rounded-xl text-xs font-medium transition-all ${addMode === 'quick' ? 'bg-white text-accent shadow-sm' : 'text-gray-500'}`}
                >
                  Быстро
                </button>
                <button
                  onClick={() => setAddMode('form')}
                  className={`px-3 py-1.5 rounded-xl text-xs font-medium transition-all ${addMode === 'form' ? 'bg-white text-accent shadow-sm' : 'text-gray-500'}`}
                >
                  Детально
                </button>
              </div>
            </div>

            {addMode === 'quick' ? (
              <>
                <input
                  className="w-full bg-gray-50 rounded-xl px-3 py-3 text-sm outline-none border border-gray-200 focus:border-accent"
                  placeholder='Например: "5000, садик" или "3200, такси"'
                  value={freeText}
                  onChange={e => setFreeText(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleQuickAdd()}
                  autoFocus
                />
                <div className="flex gap-2">
                  <button onClick={() => setShowAddExpense(false)} className="flex-1 py-2.5 rounded-xl bg-gray-100 text-gray-600 text-sm font-medium">Отмена</button>
                  <button onClick={handleQuickAdd} disabled={saving} className="flex-1 py-2.5 rounded-xl accent-button text-sm flex items-center justify-center gap-1.5">
                    <Send size={14} /> {saving ? 'Сохраняем...' : 'Внести'}
                  </button>
                </div>
              </>
            ) : (
              <>
                <input
                  className="w-full bg-gray-50 rounded-xl px-3 py-2.5 text-sm outline-none border border-gray-200 focus:border-accent"
                  placeholder="Сумма, ₽"
                  type="number"
                  value={newExp.amount}
                  onChange={e => setNewExp(p => ({...p, amount: e.target.value}))}
                />
                <select
                  className="w-full bg-gray-50 rounded-xl px-3 py-2.5 text-sm outline-none border border-gray-200 focus:border-accent"
                  value={newExp.category}
                  onChange={e => setNewExp(p => ({...p, category: e.target.value}))}
                >
                  <option value="">Категория</option>
                  {CATEGORIES.map(c => <option key={c}>{c}</option>)}
                </select>
                <input
                  className="w-full bg-gray-50 rounded-xl px-3 py-2.5 text-sm outline-none border border-gray-200 focus:border-accent"
                  placeholder="Описание"
                  value={newExp.description}
                  onChange={e => setNewExp(p => ({...p, description: e.target.value}))}
                />
                <div className="flex gap-2">
                  <button onClick={() => setShowAddExpense(false)} className="flex-1 py-2.5 rounded-xl bg-gray-100 text-gray-600 text-sm font-medium">Отмена</button>
                  <button onClick={handleFormAdd} disabled={saving} className="flex-1 py-2.5 rounded-xl accent-button text-sm">
                    {saving ? 'Сохраняем...' : 'Добавить'}
                  </button>
                </div>
              </>
            )}
          </GlassCard>
        )}

        {/* Summary tiles */}
        <div className="grid grid-cols-3 gap-2">
          <GlassCard delay={0.05} className="p-3 text-center">
            <TrendingUp size={14} className="mx-auto text-green-500 mb-1" />
            <p className="text-lg font-bold text-gray-900">{summary ? (summary.month_income/1000).toFixed(0) : '—'}<span className="text-xs text-gray-400">к</span></p>
            <p className="text-[10px] text-gray-500">Доход</p>
          </GlassCard>
          <GlassCard delay={0.07} className="p-3 text-center">
            <TrendingDown size={14} className="mx-auto text-red-400 mb-1" />
            <p className="text-lg font-bold text-gray-900">{summary ? (summary.month_expenses/1000).toFixed(0) : '—'}<span className="text-xs text-gray-400">к</span></p>
            <p className="text-[10px] text-gray-500">Расходы</p>
          </GlassCard>
          <GlassCard delay={0.09} className="p-3 text-center">
            <div className={`w-3 h-3 rounded-full mx-auto mb-1 ${summary?.balance >= 0 ? 'bg-green-400' : 'bg-red-400'}`} />
            <p className={`text-lg font-bold ${summary?.balance >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {summary ? (summary.balance/1000).toFixed(0) : '—'}<span className="text-xs text-gray-400">к</span>
            </p>
            <p className="text-[10px] text-gray-500">Баланс</p>
          </GlassCard>
        </div>

        {/* Donut chart */}
        {summary?.by_category?.length > 0 && (
          <GlassCard delay={0.12} className="p-4">
            <p className="font-semibold text-gray-800 text-sm mb-3">Расходы по категориям</p>
            <div className="flex items-center gap-4">
              <ResponsiveContainer width={120} height={120}>
                <PieChart>
                  <Pie
                    data={summary.by_category}
                    cx="50%" cy="50%"
                    innerRadius={35} outerRadius={55}
                    dataKey="total"
                    nameKey="category"
                  >
                    {summary.by_category.map((_: any, index: number) => (
                      <Cell key={index} fill={COLORS[index % COLORS.length]} opacity={0.85} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(v: number) => [formatMoney(v), '']}
                    contentStyle={{ background: 'rgba(255,255,255,0.9)', border: 'none', borderRadius: 12, fontSize: 11 }}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex-1 space-y-1.5">
                {summary.by_category.slice(0, 7).map((cat: any, i: number) => (
                  <div key={cat.category} className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5">
                      <div className="w-2 h-2 rounded-full" style={{ background: COLORS[i % COLORS.length] }} />
                      <span className="text-[11px] text-gray-600">{cat.category}</span>
                    </div>
                    <span className="text-[11px] font-medium text-gray-800">{(cat.total/1000).toFixed(1)}к</span>
                  </div>
                ))}
              </div>
            </div>
          </GlassCard>
        )}

        {/* Limits */}
        {summary?.limits?.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider px-1">Лимиты</p>
            {summary.limits.map((lim: any, i: number) => {
              const status = getLimitStatus(lim.category)
              if (!status) return null
              return (
                <GlassCard key={lim.id} delay={0.15 + i * 0.03} className="p-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-gray-700">{lim.category}</span>
                    <div className="flex items-center gap-1.5">
                      {status.over && <AlertCircle size={13} className="text-red-400" />}
                      <span className={`text-xs font-semibold ${status.over ? 'text-red-500' : 'text-gray-600'}`}>
                        {formatMoney(status.spent)} / {formatMoney(status.limit)}
                      </span>
                    </div>
                  </div>
                  <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${status.over ? 'bg-red-400' : 'bg-accent'}`}
                      style={{ width: `${Math.min(status.pct, 100)}%` }}
                    />
                  </div>
                </GlassCard>
              )
            })}
          </div>
        )}

        {/* Recent */}
        {summary?.recent_expenses?.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider px-1">Последние расходы</p>
            {summary.recent_expenses.map((exp: any, i: number) => (
              <GlassCard key={exp.id} delay={0.2 + i * 0.02} small className="px-4 py-3">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-800">{exp.description || exp.category}</p>
                    <p className="text-xs text-gray-400">{exp.category} · {exp.expense_date}</p>
                  </div>
                  <span className="text-sm font-bold text-gray-800">{formatMoney(exp.amount)}</span>
                </div>
              </GlassCard>
            ))}
          </div>
        )}

        <div className="h-4" />
      </div>
    </div>
  )
}
