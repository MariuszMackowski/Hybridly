import { Link } from 'react-router-dom'
import { useTemplates } from '../../api/hooks'
import BackButton from '../../components/BackButton'

export default function TemplatesPage() {
  const templates = useTemplates()
  const list = templates.data ?? []
  return (
    <div className="page stack">
      <BackButton to="/settings" label="Settings" />
      <div className="row spread">
        <h1>Templates</h1>
        <Link to="/templates/new" className="btn btn-small btn-primary row">
          + New
        </Link>
      </div>
      {list.map((t) => (
        <Link key={t.id} to={`/templates/${t.id}`} className="card stack">
          <strong>{t.name}</strong>
          <span className="muted">{t.slots.map((s) => s.exercise_name).join(' · ') || 'No exercises'}</span>
        </Link>
      ))}
    </div>
  )
}
