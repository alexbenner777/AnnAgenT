import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useState, createContext, useContext, useEffect } from 'react'
import type { UserRole } from './types'
import { authApi } from './api'

// Pages
import BriefingFormPage from './pages/BriefingFormPage'
import HomePage from './pages/HomePage'
import HealthPage from './pages/HealthPage'
import CalendarPage from './pages/CalendarPage'
import FinancesPage from './pages/FinancesPage'
import StatePage from './pages/StatePage'
import BriefingPage from './pages/BriefingPage'
import ContactsPage from './pages/ContactsPage'
import DayQualityPage from './pages/DayQualityPage'
import MeetingsPage from './pages/MeetingsPage'
import RemindersPage from './pages/RemindersPage'
import SettingsPage from './pages/SettingsPage'
import DenDealsPage from './pages/DenDealsPage'
import AskPage from './pages/AskPage'

// Layout
import Layout from './components/Layout'
import BackgroundBlobs from './components/BackgroundBlobs'

// User context
interface UserCtx {
  role: UserRole
  name: string
  setRole: (r: UserRole) => void
}
export const UserContext = createContext<UserCtx>({
  role: 'anya',
  name: 'Аня',
  setRole: () => {},
})
export const useUser = () => useContext(UserContext)

export default function App() {
  const [role, setRoleState] = useState<UserRole>('anya')
  const [ready, setReady] = useState(false)
  const name = role === 'anya' ? 'Аня' : 'Ден'

  useEffect(() => {
    const tgInitData = window.Telegram?.WebApp?.initData

    if (tgInitData) {
      // В Telegram — валидируем initData на сервере, роль назначает сервер
      authApi.telegram(tgInitData)
        .then(res => {
          setRoleState(res.role as UserRole)
        })
        .catch(() => {
          // fallback: просто спросим у сервера текущую роль
          authApi.getRole().then(res => setRoleState(res.role as UserRole)).catch(() => {})
        })
        .finally(() => setReady(true))
    } else {
      // В браузере — читаем роль из серверной сессии (кука переживает F5)
      authApi.getRole()
        .then(res => setRoleState(res.role as UserRole))
        .catch(() => {})
        .finally(() => setReady(true))
    }
  }, [])

  const setRole = (r: UserRole) => {
    // Пишем роль в серверную сессию
    authApi.setRole(r).then(res => setRoleState(res.role as UserRole)).catch(() => setRoleState(r))
  }

  if (!ready) {
    return (
      <div className="flex items-center justify-center min-h-dvh bg-gray-50">
        <div className="w-8 h-8 border-2 border-gray-200 border-t-indigo-500 rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <UserContext.Provider value={{ role, name, setRole }}>
      <BrowserRouter>
        <BackgroundBlobs />
        <Routes>
          {/* Fullscreen route — без нижней навигации (открывается из Telegram WebApp) */}
          <Route path="/briefing-form" element={<BriefingFormPage />} />
          <Route element={<Layout />}>
            <Route index element={<HomePage />} />
            <Route path="/health" element={
              role === 'anya' ? <HealthPage /> : <Navigate to="/" replace />
            } />
            <Route path="/calendar" element={<CalendarPage />} />
            <Route path="/finances" element={<FinancesPage />} />
            <Route path="/state" element={<StatePage />} />
            <Route path="/briefing" element={<BriefingPage />} />
            <Route path="/contacts" element={<ContactsPage />} />
            <Route path="/day-quality" element={<DayQualityPage />} />
            <Route path="/meetings" element={<MeetingsPage />} />
            <Route path="/reminders" element={<RemindersPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/den-deals" element={
              role === 'den' ? <DenDealsPage /> : <Navigate to="/" replace />
            } />
            <Route path="/ask" element={
              role === 'den' ? <AskPage /> : <Navigate to="/" replace />
            } />
          </Route>
        </Routes>
      </BrowserRouter>
    </UserContext.Provider>
  )
}
