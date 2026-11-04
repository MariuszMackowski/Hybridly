import { Navigate, NavLink, Route, Routes, useLocation } from 'react-router-dom'
import ExercisesPage from './features/exercises/ExercisesPage'
import HistoryPage from './features/history/HistoryPage'
import WorkoutDetailPage from './features/history/WorkoutDetailPage'
import LoggerPage from './features/logger/LoggerPage'
import RunDetailPage from './features/runs/RunDetailPage'
import SettingsPage from './features/settings/SettingsPage'
import TemplateEditor from './features/templates/TemplateEditor'
import TemplatesPage from './features/templates/TemplatesPage'
import TodayPage from './features/today/TodayPage'

const TABS = [
  { to: '/', label: 'Today' },
  { to: '/history', label: 'History' },
  { to: '/exercises', label: 'Exercises' },
  { to: '/templates', label: 'Templates' },
  { to: '/settings', label: 'Settings' },
]

/** Bottom navigation; hidden while logging a workout. */
function TabBar() {
  const { pathname } = useLocation()
  if (pathname.startsWith('/log')) return null
  return (
    <nav className="tabbar">
      {TABS.map((tab) => (
        <NavLink key={tab.to} to={tab.to} end={tab.to === '/'}>
          {tab.label}
        </NavLink>
      ))}
    </nav>
  )
}

export default function App() {
  return (
    <>
      <Routes>
        <Route path="/" element={<TodayPage />} />
        <Route path="/log" element={<LoggerPage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/history/:id" element={<WorkoutDetailPage />} />
        <Route path="/runs" element={<Navigate to="/history" replace />} />
        <Route path="/runs/:id" element={<RunDetailPage />} />
        <Route path="/exercises" element={<ExercisesPage />} />
        <Route path="/templates" element={<TemplatesPage />} />
        <Route path="/templates/:id" element={<TemplateEditor />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
      <TabBar />
    </>
  )
}
