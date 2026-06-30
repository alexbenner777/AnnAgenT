import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Home, Heart, Calendar, Wallet, MoreHorizontal,
  Activity, BookOpen, Users, Star, Mic, Bell, Settings, X,
  LayoutGrid, MessageCircle
} from 'lucide-react'
import { useUser } from '../App'

function haptic(style: 'light' | 'medium' | 'heavy' = 'light') {
  window.Telegram?.WebApp?.HapticFeedback?.impactOccurred(style)
}

export default function Layout() {
  const location = useLocation()
  const navigate = useNavigate()
  const { role } = useUser()
  const [showMore, setShowMore] = useState(false)

  const currentPath = location.pathname
  const isActive = (path: string) => {
    if (path === '/') return currentPath === '/'
    return currentPath.startsWith(path)
  }

  // Аня: Главная | Здоровье | Сводка | Календарь | Ещё
  // Ден: Сегодня | Состояние | Дела | Спросить  (без Ещё, без Здоровья)
  const TAB_ITEMS = role === 'anya'
    ? [
        { path: '/',          icon: Home,           label: 'Главная'   },
        { path: '/health',    icon: Heart,          label: 'Здоровье'  },
        { path: '/briefing',  icon: BookOpen,       label: 'Сводка'    },
        { path: '/calendar',  icon: Calendar,       label: 'Календарь' },
        { path: '/more',      icon: MoreHorizontal, label: 'Ещё'       },
      ]
    : [
        { path: '/',           icon: Home,           label: 'Сегодня'   },
        { path: '/state',      icon: Activity,       label: 'Состояние' },
        { path: '/den-deals',  icon: LayoutGrid,     label: 'Дела'      },
        { path: '/ask',        icon: MessageCircle,  label: 'Спросить'  },
      ]

  // Ещё — только для Ани
  const MORE_ITEMS = [
    { path: '/state',       icon: Activity,    label: 'Состояние',    emoji: '🧠' },
    { path: '/finances',    icon: Wallet,      label: 'Финансы',      emoji: '💰' },
    { path: '/contacts',    icon: Users,       label: 'Контакты',     emoji: '👥' },
    { path: '/day-quality', icon: Star,        label: 'Качество дня', emoji: '✨' },
    { path: '/meetings',    icon: Mic,         label: 'Встречи',      emoji: '🎙' },
    { path: '/reminders',   icon: Bell,        label: 'Напоминания',  emoji: '🔔' },
    { path: '/settings',    icon: Settings,    label: 'Настройки',    emoji: '⚙️' },
  ]

  const handleTabClick = (path: string) => {
    haptic('light')
    if (path === '/more') {
      setShowMore(true)
      return
    }
    navigate(path)
    setShowMore(false)
  }

  const handleMoreItem = (path: string) => {
    haptic('light')
    navigate(path)
    setShowMore(false)
  }

  const isMoreActive = MORE_ITEMS.some(m => currentPath.startsWith(m.path))

  return (
    <div className="relative flex flex-col min-h-dvh" style={{ position: 'relative', zIndex: 1 }}>
      {/* Main content */}
      <main className="flex-1 overflow-hidden pb-28">
        <AnimatePresence mode="wait">
          <motion.div
            key={currentPath}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.22, ease: [0.4, 0, 0.2, 1] }}
            className="h-full"
          >
            <Outlet />
          </motion.div>
        </AnimatePresence>
      </main>

      {/* Floating Tab Bar */}
      <div className="fixed bottom-0 left-0 right-0 z-30 flex justify-center px-4 pb-4"
           style={{ maxWidth: 430, margin: '0 auto', left: 0, right: 0 }}>
        <div
          className="glass-tab-bar px-2 py-2 flex items-center justify-around w-full"
          style={{ paddingBottom: `max(8px, env(safe-area-inset-bottom, 8px))` }}
        >
          {TAB_ITEMS.map((tab) => {
            const Icon = tab.icon
            const active = tab.path === '/more' ? isMoreActive || showMore : isActive(tab.path)
            return (
              <button
                key={tab.path}
                onClick={() => handleTabClick(tab.path)}
                className={`flex flex-col items-center gap-1 px-3 py-2 rounded-2xl transition-all duration-200 min-w-0 flex-1 ${
                  active
                    ? 'bg-accent-muted'
                    : 'hover:bg-black/5 active:bg-black/5'
                }`}
              >
                <Icon
                  size={22}
                  strokeWidth={active ? 2.2 : 1.6}
                  className={active ? 'text-accent' : 'text-gray-400'}
                />
                <span className={`text-[10px] font-medium leading-none truncate ${active ? 'text-accent' : 'text-gray-400'}`}>
                  {tab.label}
                </span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Bottom Sheet — "Ещё" */}
      <AnimatePresence>
        {showMore && (
          <>
            <motion.div
              className="bottom-sheet-overlay"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowMore(false)}
            />
            <motion.div
              className="bottom-sheet"
              initial={{ y: '100%' }}
              animate={{ y: 0 }}
              exit={{ y: '100%' }}
              transition={{ type: 'spring', damping: 30, stiffness: 300 }}
            >
              {/* Handle */}
              <div className="flex justify-center pt-3 pb-1">
                <div className="w-10 h-1 bg-gray-200 rounded-full" />
              </div>

              <div className="flex items-center justify-between px-5 pt-2 pb-3">
                <span className="text-base font-semibold text-gray-800">Ещё</span>
                <button
                  onClick={() => setShowMore(false)}
                  className="w-8 h-8 flex items-center justify-center rounded-full bg-gray-100"
                >
                  <X size={16} className="text-gray-500" />
                </button>
              </div>

              <div className="grid grid-cols-4 gap-1 px-4 pb-6"
                   style={{ paddingBottom: `max(24px, calc(env(safe-area-inset-bottom, 0px) + 16px))` }}>
                {MORE_ITEMS.map((item) => {
                  const active = currentPath.startsWith(item.path)
                  return (
                    <button
                      key={item.path}
                      onClick={() => handleMoreItem(item.path)}
                      className={`flex flex-col items-center gap-2 p-3 rounded-2xl transition-all active:scale-95 ${
                        active ? 'bg-accent-muted' : 'hover:bg-gray-50 active:bg-gray-50'
                      }`}
                    >
                      <div className={`w-12 h-12 rounded-2xl flex items-center justify-center text-xl ${
                        active ? 'bg-accent/20' : 'bg-gray-100'
                      }`}>
                        {item.emoji}
                      </div>
                      <span className={`text-[11px] font-medium text-center leading-tight ${
                        active ? 'text-accent' : 'text-gray-600'
                      }`}>
                        {item.label}
                      </span>
                    </button>
                  )
                })}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  )
}
