import BackButton from '../../components/BackButton'
import { useTemplates } from '../../api/hooks'
import WeekEditor from './WeekEditor'

/** Weekday → strength template plan, on its own page under Settings. */
export default function WeekPage() {
  const templates = useTemplates().data ?? []
  return (
    <div className="page stack">
      <BackButton to="/settings" label="Settings" />
      <h1>Week plan</h1>
      <WeekEditor templates={templates} />
    </div>
  )
}
