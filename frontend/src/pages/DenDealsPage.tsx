import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Wallet, Users, Star, Mic } from 'lucide-react'
import GlassCard from '../components/GlassCard'
import PageHeader from '../components/PageHeader'

const ITEMS = [
  {
    path: '/finances',
    icon: Wallet,
    emoji: '💰',
    label: 'Финансы',
    desc: 'Расходы и баланс',
    color: 'bg-emerald-50',
    iconColor: 'text-emerald-500',
  },
  {
    path: '/contacts',
    icon: Users,
    emoji: '👥',
    label: 'Контакты',
    desc: 'Окружение и дни рождения',
    color: 'bg-blue-50',
    iconColor: 'text-blue-500',
  },
  {
    path: '/day-quality',
    icon: Star,
    emoji: '✨',
    label: 'Качество дня',
    desc: 'Нумерология и ритм',
    color: 'bg-amber-50',
    iconColor: 'text-amber-500',
  },
  {
    path: '/meetings',
    icon: Mic,
    emoji: '🎙',
    label: 'Встречи',
    desc: 'Записи и резюме',
    color: 'bg-purple-50',
    iconColor: 'text-purple-500',
  },
]

export default function DenDealsPage() {
  const navigate = useNavigate()

  return (
    <div className="page-scroll h-full overflow-y-auto">
      <div className="px-4 pt-6 pb-4 space-y-4">
        <PageHeader title="Дела" subtitle="Обзор ключевых разделов" />

        <div className="grid grid-cols-2 gap-3">
          {ITEMS.map((item, i) => {
            const Icon = item.icon
            return (
              <motion.div
                key={item.path}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.07, duration: 0.3 }}
              >
                <GlassCard
                  className="p-5 cursor-pointer active:scale-95 transition-transform"
                  onClick={() => navigate(item.path)}
                >
                  <div className={`w-12 h-12 rounded-2xl ${item.color} flex items-center justify-center mb-3`}>
                    <Icon size={22} className={item.iconColor} />
                  </div>
                  <p className="font-semibold text-gray-800 text-sm">{item.label}</p>
                  <p className="text-xs text-gray-400 mt-0.5">{item.desc}</p>
                </GlassCard>
              </motion.div>
            )
          })}
        </div>

        <div className="h-4" />
      </div>
    </div>
  )
}
