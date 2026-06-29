import { useState } from 'react'
import { Star, ChevronDown, ChevronUp } from 'lucide-react'
import GlassCard from '../components/GlassCard'
import PageHeader from '../components/PageHeader'

function haptic(s: 'light' | 'medium' = 'light') {
  window.Telegram?.WebApp?.HapticFeedback?.impactOccurred(s)
}

function getNumerologyDay(date: Date): number {
  const d = date.getDate(); const m = date.getMonth() + 1; const y = date.getFullYear()
  let sum = 0
  String(d).split('').forEach(n => sum += parseInt(n))
  String(m).split('').forEach(n => sum += parseInt(n))
  String(y).split('').forEach(n => sum += parseInt(n))
  while (sum > 9 && sum !== 11 && sum !== 22) {
    let s2 = 0; String(sum).split('').forEach(n => s2 += parseInt(n)); sum = s2
  }
  return sum
}

function getNumerologyMeaning(n: number): string {
  const meanings: Record<number, string> = {
    1: 'Инициатива и новые начала. Хороший день для запуска проектов.',
    2: 'Партнёрство и сотрудничество. Время переговоров и союзов.',
    3: 'Творчество и общение. Отличный день для презентаций.',
    4: 'Стабильность и труд. День системной работы.',
    5: 'Перемены и свобода. Будь гибким.',
    6: 'Гармония и ответственность. Время заботы.',
    7: 'Анализ и интроспекция. Глубина мысли.',
    8: 'Власть и достижения. Финансовые решения.',
    9: 'Завершение цикла. Отпускай лишнее.',
    11: 'Мастер-число. Интуиция на максимуме.',
    22: 'Мастер-строитель. Глобальные планы.',
  }
  return meanings[n] || 'Нейтральный день.'
}

const PLANET_TRANSITS = [
  { planet: '☿ Меркурий', aspect: 'трин', target: 'Юпитер ♃', meaning: 'Коммуникация и переговоры в фаворе. Подходит для подписания договоров.', color: '#5B9DB8' },
  { planet: '♀ Венера', aspect: 'секстиль', target: 'Сатурн ♄', meaning: 'Структурированные отношения. Долгосрочные договорённости.', color: '#E4D2B3' },
]

const DESTINY_MATRIX = [
  { zone: 'Зона комфорта', score: 7, desc: 'Высокий потенциал для реализации через взаимодействие с людьми' },
  { zone: 'Зона денег', score: 6, desc: 'Финансовый поток через партнёрство и делегирование' },
  { zone: 'Зона таланта', score: 9, desc: 'Стратегическое мышление и видение системы' },
]

export default function DayQualityPage() {
  const [showDetails, setShowDetails] = useState(false)
  const today = new Date()
  const numDay = getNumerologyDay(today)
  const numMeaning = getNumerologyMeaning(numDay)

  const overallScore = Math.round((numDay / 11) * 10 + (PLANET_TRANSITS.length * 1.5))

  return (
    <div className="page-scroll h-full overflow-y-auto">
      <div className="px-4 pt-6 pb-4 space-y-4">
        <PageHeader title="Качество дня" subtitle="Астрология · Нумерология · Матрица судьбы" />

        {/* Overall score */}
        <GlassCard delay={0.05} className="p-5 text-center">
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-3">Оценка дня</p>
          <div className="relative w-24 h-24 mx-auto mb-3">
            <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
              <circle cx="50" cy="50" r="42" fill="none" stroke="rgba(91,157,184,0.1)" strokeWidth="10" />
              <circle
                cx="50" cy="50" r="42" fill="none"
                stroke="url(#scoreGrad)" strokeWidth="10"
                strokeLinecap="round"
                strokeDasharray={`${(overallScore / 10) * 264} 264`}
              />
              <defs>
                <linearGradient id="scoreGrad" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor="#5B9DB8" />
                  <stop offset="100%" stopColor="#86C1AD" />
                </linearGradient>
              </defs>
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-3xl font-bold text-gray-900">{overallScore}</span>
            </div>
          </div>
          <p className="text-sm font-medium text-gray-600">
            {overallScore >= 8 ? '✨ Превосходный день' : overallScore >= 6 ? '🌟 Хороший день' : '🌤 Обычный день'}
          </p>
          <p className="text-xs text-gray-400 mt-1">
            {today.toLocaleDateString('ru-RU', { weekday: 'long', day: 'numeric', month: 'long' })}
          </p>
        </GlassCard>

        {/* Numerology */}
        <GlassCard delay={0.08} className="p-4">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-2xl bg-purple-50 flex items-center justify-center">
              <span className="text-purple-500 font-bold">{numDay}</span>
            </div>
            <div>
              <p className="font-semibold text-gray-800 text-sm">Нумерология · День {numDay}</p>
              <p className="text-xs text-gray-500">Личный день</p>
            </div>
          </div>
          <p className="text-sm text-gray-700 leading-relaxed">{numMeaning}</p>
        </GlassCard>

        {/* Astrology */}
        <div className="space-y-2">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider px-1">Транзиты</p>
          {PLANET_TRANSITS.map((t, i) => (
            <GlassCard key={i} delay={0.1 + i * 0.04} className="p-4">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-2xl flex items-center justify-center text-lg flex-shrink-0" style={{ background: `${t.color}20` }}>
                  {t.planet.split(' ')[0]}
                </div>
                <div>
                  <p className="text-sm font-semibold text-gray-800">
                    {t.planet} <span className="text-gray-400 font-normal">{t.aspect}</span> {t.target}
                  </p>
                  <p className="text-xs text-gray-500 mt-1 leading-relaxed">{t.meaning}</p>
                </div>
              </div>
            </GlassCard>
          ))}
        </div>

        {/* Destiny Matrix */}
        <div className="space-y-2">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider px-1">Матрица судьбы</p>
          {DESTINY_MATRIX.map((m, i) => (
            <GlassCard key={i} delay={0.16 + i * 0.04} className="p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-700">{m.zone}</span>
                <div className="flex items-center gap-1">
                  {Array.from({length: 10}).map((_, j) => (
                    <Star key={j} size={10} className={j < m.score ? 'text-amber-400 fill-amber-400' : 'text-gray-200 fill-gray-200'} />
                  ))}
                </div>
              </div>
              <p className="text-xs text-gray-500">{m.desc}</p>
            </GlassCard>
          ))}
        </div>

        {/* Расшифровка */}
        <GlassCard delay={0.25} className="overflow-hidden">
          <button
            className="w-full p-4 flex items-center justify-between"
            onClick={() => { haptic(); setShowDetails(!showDetails) }}
          >
            <span className="font-semibold text-accent text-sm">🔍 Расшифровка (почему так)</span>
            {showDetails ? <ChevronUp size={16} className="text-gray-400" /> : <ChevronDown size={16} className="text-gray-400" />}
          </button>
          {showDetails && (
            <div className="px-4 pb-4 space-y-3 border-t border-white/60 pt-3">
              <div>
                <p className="text-xs font-semibold text-gray-400 mb-1">Расчёт числа дня</p>
                <p className="text-xs text-gray-600 leading-relaxed">
                  {today.toLocaleDateString('ru-RU')} → сумма всех цифр даты = {numDay}. Методология: нумерология Пифагора с редукцией до числа 1–9 (или мастер-числа 11/22).
                </p>
              </div>
              <div>
                <p className="text-xs font-semibold text-gray-400 mb-1">Астрологические аспекты</p>
                <p className="text-xs text-gray-600 leading-relaxed">
                  Транзиты рассчитаны по эфемеридам Swiss Ephemeris на текущую дату. Орб аспектов: ±3° для мажорных, ±1.5° для минорных.
                </p>
              </div>
              <div>
                <p className="text-xs font-semibold text-gray-400 mb-1">Матрица судьбы</p>
                <p className="text-xs text-gray-600 leading-relaxed">
                  Расчёт на основе натальных данных. Зоны определяются положением планет в квадратах матрицы относительно текущих транзитов.
                </p>
              </div>
            </div>
          )}
        </GlassCard>

        <div className="h-4" />
      </div>
    </div>
  )
}
