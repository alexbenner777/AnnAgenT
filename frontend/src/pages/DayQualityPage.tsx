import GlassCard from '../components/GlassCard'
import PageHeader from '../components/PageHeader'

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

export default function DayQualityPage() {
  const today = new Date()
  const numDay = getNumerologyDay(today)
  const numMeaning = getNumerologyMeaning(numDay)

  return (
    <div className="page-scroll h-full overflow-y-auto">
      <div className="px-4 pt-6 pb-4 space-y-4">
        <PageHeader title="Качество дня" subtitle="Нумерология · Астрология · Матрица судьбы" />

        {/* Numerology — считается по дате, реальный расчёт */}
        <GlassCard delay={0.05} className="p-4">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-2xl bg-purple-50 flex items-center justify-center">
              <span className="text-purple-500 font-bold text-lg">{numDay}</span>
            </div>
            <div>
              <p className="font-semibold text-gray-800 text-sm">Нумерология · День {numDay}</p>
              <p className="text-xs text-gray-500">
                {today.toLocaleDateString('ru-RU', { weekday: 'long', day: 'numeric', month: 'long' })}
              </p>
            </div>
          </div>
          <p className="text-sm text-gray-700 leading-relaxed">{numMeaning}</p>
          <p className="text-xs text-gray-400 mt-2">
            Расчёт: сумма цифр даты {today.toLocaleDateString('ru-RU')} → {numDay} (нумерология Пифагора)
          </p>
        </GlassCard>

        {/* Астрология и матрица — честная заглушка */}
        <GlassCard delay={0.1} className="p-5 text-center">
          <p className="text-4xl mb-3">🔮</p>
          <p className="font-semibold text-gray-800 text-sm mb-2">Астрология и Матрица судьбы</p>
          <p className="text-sm text-gray-500 leading-relaxed">
            Расчёт транзитов и матрицы судьбы выполняется в боте.
          </p>
          <p className="text-sm text-accent font-medium mt-2">Напиши в Telegram: /day</p>
        </GlassCard>

        <div className="h-4" />
      </div>
    </div>
  )
}
