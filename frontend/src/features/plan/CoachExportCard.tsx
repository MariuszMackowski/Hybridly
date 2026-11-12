import { useState } from 'react'
import { apiGet } from '../../api/client'
import type { CoachExport } from '../../api/types'
import CopyBox from '../../components/CopyBox'
import { shift } from '../history/weeks'

const DEFAULT_DAYS = 28

/** Date range picker that builds a training summary to paste to the AI coach. */
export default function CoachExportCard({ today }: { today: string }) {
  const [start, setStart] = useState(() => shift(today, -(DEFAULT_DAYS - 1)))
  const [end, setEnd] = useState(today)
  const [text, setText] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  /** Fetch the summary for the chosen range. */
  async function generate() {
    setLoading(true)
    setError(null)
    try {
      setText((await apiGet<CoachExport>(`/export/coach?start=${start}&end=${end}`)).text)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <details className="card">
      <summary>
        <strong>Training summary for your AI coach</strong>
      </summary>
      <div className="stack">
        <span className="muted">Gym sets, runs vs plan, recovery and bodyweight — paste it to the coach.</span>
        <div className="row">
          <input type="date" value={start} max={end} onChange={(e) => setStart(e.target.value)} />
          <span className="muted">–</span>
          <input type="date" value={end} min={start} onChange={(e) => setEnd(e.target.value)} />
        </div>
        {error && <div className="banner">{error}</div>}
        <button className="btn-primary" disabled={loading || !start || !end} onClick={generate}>
          {loading ? 'Generating…' : 'Generate'}
        </button>
        {text !== null && <CopyBox text={text} />}
      </div>
    </details>
  )
}
