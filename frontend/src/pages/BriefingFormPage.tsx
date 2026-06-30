import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle2, ChevronRight } from 'lucide-react'
import { briefingApi } from '../api'

function haptic(s: 'light' | 'medium' | 'heavy' = 'light') {
  window.Telegram?.WebApp?.HapticFeedback?.impactOccurred(s)
}

function ScaleRow({ label, value, onChange }: { label: string; value: number; onChange: (v: number) => void }) {
  return (
    <div className="space-y-2">
      <div className="flex justify-between items-center">
        <span className="text-sm font-medium text-gray-700">{label}</span>
        <span className="text-lg font-bold text-accent">{value}</span>
      </div>
      <div className="flex gap-1.5">
        {Array.from({ length: 10 }, (_, i) => i + 1).map(n => (
          <button
            key={n}
            onClick={() => { haptic('light'); onChange(n) }}
            className={`flex-1 h-9 rounded-xl text-xs font-semibold transition-all ${
              value === n
                ? 'bg-accent text-white shadow-md scale-110'
                : n <= value
                ? 'bg-accent/20 text-accent'
                : 'bg-gray-100 text-gray-400'
            }`}
          >
            {n}
          </button>
        ))}
      </div>
    </div>
  )
}

function YesNoRow({ label, value, onChange }: { label: string; value: boolean | null; onChange: (v: boolean) => void }) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-gray-100 last:border-0">
      <span className="text-sm font-medium text-gray-700">{label}</span>
      <div className="flex gap-2">
        <button
          onClick={() => { haptic('light'); onChange(true) }}
          className={`px-4 py-1.5 rounded-xl text-sm font-semibold transition-all ${
            value === true ? 'bg-emerald-500 text-white shadow-sm' : 'bg-gray-100 text-gray-400'
          }`}
        >Да</button>
        <button
          onClick={() => { haptic('light'); onChange(false) }}
          className={`px-4 py-1.5 rounded-xl text-sm font-semibold transition-all ${
            value === false ? 'bg-red-400 text-white shadow-sm' : 'bg-gray-100 text-gray-400'
          }`}
        >Нет</button>
      </div>
    </div>
  )
}

type Step = 'scale' | 'binary' | 'loading' | 'done'

export default function BriefingFormPage() {
  const [step, setStep] = useState<Step>('scale')
  const [energy, setEnergy] = useState(7)
  const [sleep, setSleep] = useState(7)
  const [workout, setWorkout] = useState<boolean | null>(null)
  const [massage, setMassage] = useState<boolean | null>(null)
  const [alcohol, setAlcohol] = useState<boolean | null>(null)
  const [result, setResult] = useState<string>('')
  const [error, setError] = useState<string>('')

  const canProceedBinary = workout !== null && massage !== null && alcohol !== null

  const handleSubmit = async () => {
    haptic('medium')
    setStep('loading')
    try {
      const res = await briefingApi.generate({
        energy_subjective: energy,
        sleep_score: sleep,
        workout_done: workout ? 1 : 0,
        massage_done: massage ? 1 : 0,
        alcohol: alcohol ? 1 : 0,
      })
      setResult(res.text || 'Брифинг готов!')
      setStep('done')
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success')
    } catch (e: any) {
      setError(e?.message || 'Что-то пошло не так')
      setStep('done')
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('error')
    }
  }

  return (
    <div
      className="min-h-dvh flex flex-col"
      style={{ background: 'linear-gradient(135deg, #f0f4ff 0%, #faf0ff 50%, #f0fff4 100%)' }}
    >
      {/* Header */}
      <div className="px-5 pt-8 pb-4">
        <p className="text-xs font-semibold text-accent/60 uppercase tracking-widest mb-1">Утренний бриф</p>
        <h1 className="text-2xl font-bold text-gray-900">
          {step === 'scale' && '1 / 2 · Как ты сегодня?'}
          {step === 'binary' && '2 / 2 · Вчера и сегодня'}
          {step === 'loading' && 'Генерирую бриф…'}
          {step === 'done' && (error ? 'Ошибка' : 'Готово!')}
        </h1>
      </div>

      {/* Content */}
      <div className="flex-1 px-5 pb-6">
        <AnimatePresence mode="wait">

          {step === 'scale' && (
            <motion.div key="scale"
              initial={{ opacity: 0, x: 40 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -40 }}
              className="space-y-6"
            >
              <div className="bg-white/80 backdrop-blur rounded-3xl p-5 shadow-sm space-y-6">
                <ScaleRow label="⚡ Общее состояние (1–10)" value={energy} onChange={setEnergy} />
                <ScaleRow label="😴 Качество сна (1–10)" value={sleep} onChange={setSleep} />
              </div>
              <button
                onClick={() => { haptic('medium'); setStep('binary') }}
                className="w-full py-4 rounded-2xl text-white font-semibold text-base flex items-center justify-center gap-2"
                style={{ background: 'linear-gradient(135deg, #5B9DB8, #7c6dbf)' }}
              >
                Далее <ChevronRight size={18} />
              </button>
            </motion.div>
          )}

          {step === 'binary' && (
            <motion.div key="binary"
              initial={{ opacity: 0, x: 40 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -40 }}
              className="space-y-4"
            >
              <div className="bg-white/80 backdrop-blur rounded-3xl p-5 shadow-sm">
                <YesNoRow label="🏋️ Тренировка сегодня" value={workout} onChange={setWorkout} />
                <YesNoRow label="💆 Массаж" value={massage} onChange={setMassage} />
                <YesNoRow label="🍷 Алкоголь вчера" value={alcohol} onChange={setAlcohol} />
              </div>
              {!canProceedBinary && (
                <p className="text-center text-xs text-gray-400">Ответь на все вопросы</p>
              )}
              <button
                onClick={canProceedBinary ? handleSubmit : undefined}
                disabled={!canProceedBinary}
                className="w-full py-4 rounded-2xl text-white font-semibold text-base flex items-center justify-center gap-2 transition-all disabled:opacity-40"
                style={{ background: canProceedBinary ? 'linear-gradient(135deg, #5B9DB8, #7c6dbf)' : '#ccc' }}
              >
                Сгенерировать бриф ✨
              </button>
              <button
                onClick={() => { haptic('light'); setStep('scale') }}
                className="w-full py-2 text-sm text-gray-400"
              >
                ← Назад
              </button>
            </motion.div>
          )}

          {step === 'loading' && (
            <motion.div key="loading"
              initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
              className="flex flex-col items-center justify-center pt-16 gap-5"
            >
              <div className="w-16 h-16 rounded-full bg-white/80 shadow-md flex items-center justify-center">
                <div className="w-8 h-8 border-3 border-accent/30 border-t-accent rounded-full animate-spin" style={{ borderWidth: 3 }} />
              </div>
              <p className="text-gray-500 text-sm">Анализирую данные и готовлю рекомендации…</p>
            </motion.div>
          )}

          {step === 'done' && (
            <motion.div key="done"
              initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
              className="space-y-4"
            >
              {error ? (
                <div className="bg-red-50 rounded-3xl p-5 text-red-600 text-sm">{error}</div>
              ) : (
                <>
                  <div className="flex items-center gap-3 bg-emerald-50 rounded-2xl px-4 py-3">
                    <CheckCircle2 size={20} className="text-emerald-500 flex-shrink-0" />
                    <p className="text-sm font-medium text-emerald-700">Бриф готов и отправлен в чат</p>
                  </div>
                  <div className="bg-white/80 backdrop-blur rounded-3xl p-5 shadow-sm">
                    <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Твой брифинг на сегодня</p>
                    <div className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">{result}</div>
                  </div>
                </>
              )}
              <button
                onClick={() => window.Telegram?.WebApp?.close()}
                className="w-full py-4 rounded-2xl text-white font-semibold text-base"
                style={{ background: 'linear-gradient(135deg, #5B9DB8, #7c6dbf)' }}
              >
                Закрыть
              </button>
            </motion.div>
          )}

        </AnimatePresence>
      </div>
    </div>
  )
}
