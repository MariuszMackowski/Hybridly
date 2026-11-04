import { useNavigate } from 'react-router-dom'

/** Small "‹ Label" button returning to a parent page. */
export default function BackButton({ to, label }: { to: string; label: string }) {
  const navigate = useNavigate()
  return (
    <button className="btn-small" style={{ alignSelf: 'flex-start' }} onClick={() => navigate(to)}>
      ‹ {label}
    </button>
  )
}
