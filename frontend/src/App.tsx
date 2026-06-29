import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useState, createContext, useContext } from 'react'
import type { UserRole } from './types'

// Pages
import HomePage from './pages/HomePage'
import HealthPage from './pages/HealthPage'
import CalendarPage from './pages/CalendarPage'
import FinancesPage from './pages/FinancesPage'
import StatePage from './pages/StatePage'
import BriefingPage from './pages/BriefingPage'
import ContactsPage from './pages/ContactsPage'
import DayQualityPage from './pages/DayQualityPage'
import MeetingsPage from './pages/MeetingsPage'
import TasksPage from './pages/TasksPage'
import RemindersPage from './pages/RemindersPage'
import SettingsPage from './pages/SettingsPage'

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
  // Try to get user from Telegram WebApp
  const tgUser = window.Telegram?.WebApp?.initDataUnsafe?.user
  const defaultRole: UserRole = 'anya' // default to anya for demo

  const [role, setRole] = useState<UserRole>(defaultRole)
  const name = role === 'anya' ? 'Аня' : 'Ден'

  return (
    <UserContext.Provider value={{ role, name, setRole }}>
      <BrowserRouter>
        <BackgroundBlobs />
        <Routes>
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
            <Route path="/tasks" element={<TasksPage />} />
            <Route path="/reminders" element={<RemindersPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </UserContext.Provider>
  )
}
