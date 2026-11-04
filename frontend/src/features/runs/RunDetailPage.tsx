import { useNavigate, useParams } from 'react-router-dom'
import { useActivity, useDeleteActivity } from '../../api/hooks'
import { dateTime, formatDistance, formatDuration, formatPace, speedLabel } from '../../lib/format'
import PlanLink from './PlanLink'
import RunCharts from './RunCharts'
import RunMap from './RunMap'

/** One labelled number. */
function Tile(props: { label: string; value: string | number | null }) {
  if (props.value === null || props.value === '–') return null
  return (
    <div className="tile">
      <span className="muted">{props.label}</span>
      <strong>{props.value}</strong>
    </div>
  )
}

export default function RunDetailPage() {
  const id = Number(useParams().id)
  const query = useActivity(id)
  const remove = useDeleteActivity()
  const navigate = useNavigate()
  const a = query.data
  if (query.isError) return <div className="page banner">{query.error.message}</div>
  if (!a) return <div className="page muted">Loading…</div>
  const isRun = a.sport === 'run'

  return (
    <div className="page stack">
      <button className="btn-small" style={{ alignSelf: 'flex-start' }} onClick={() => navigate('/history')}>
        ‹ History
      </button>
      <div>
        <h1>{a.name ?? a.sport}</h1>
        <div className="muted">
          {dateTime(a.started_at)} · {a.source === 'coros' ? 'COROS' : 'uploaded FIT'}
        </div>
      </div>
      <div className="tiles">
        <Tile label="Distance" value={formatDistance(a.distance_m)} />
        <Tile label="Time" value={formatDuration(a.duration_s)} />
        <Tile label={isRun ? 'Pace' : 'Speed'} value={speedLabel(a)} />
        <Tile label="Avg HR" value={a.avg_hr} />
        <Tile label="Max HR" value={a.max_hr} />
        <Tile label="Cadence" value={a.avg_cadence_spm} />
        <Tile label="Stride" value={a.avg_stride_m !== null ? `${a.avg_stride_m.toFixed(2)} m` : null} />
        <Tile label="Power" value={a.avg_power_w !== null ? `${a.avg_power_w} W` : null} />
        <Tile label="GCT" value={a.avg_gct_ms !== null ? `${Math.round(a.avg_gct_ms)} ms` : null} />
        <Tile label="Vert. osc." value={a.avg_vo_cm !== null ? `${a.avg_vo_cm.toFixed(1)} cm` : null} />
        <Tile label="Vert. ratio" value={a.avg_vr_pct !== null ? `${a.avg_vr_pct.toFixed(1)} %` : null} />
        <Tile label="Ascent" value={a.ascent_m !== null ? `${Math.round(a.ascent_m)} m` : null} />
        <Tile label="Training load" value={a.training_load} />
        <Tile label="Aerobic TE" value={a.aerobic_te} />
        <Tile label="Calories" value={a.calories} />
      </div>
      <PlanLink activity={a} />
      <RunCharts streams={a.streams} isRun={isRun} />
      <RunMap streams={a.streams} />
      {a.laps.length > 0 && (
        <div className="card">
          <strong>Laps</strong>
          <table className="sets">
            <thead>
              <tr>
                <th>#</th>
                <th>km</th>
                <th>Time</th>
                <th>{isRun ? 'Pace' : 'km/h'}</th>
                <th>HR</th>
                <th>W</th>
                <th>Stride</th>
              </tr>
            </thead>
            <tbody>
              {a.laps.map((lap) => (
                <tr key={lap.index}>
                  <td>{lap.index + 1}</td>
                  <td>{lap.distance_m !== null ? (lap.distance_m / 1000).toFixed(2) : '–'}</td>
                  <td>{formatDuration(lap.duration_s)}</td>
                  <td>
                    {isRun
                      ? formatPace(lap.distance_m ? lap.duration_s / (lap.distance_m / 1000) : null)
                      : lap.avg_speed !== null
                        ? (lap.avg_speed * 3.6).toFixed(1)
                        : '–'}
                  </td>
                  <td>{lap.avg_hr ?? '–'}</td>
                  <td>{lap.avg_power_w ?? '–'}</td>
                  <td>{lap.avg_stride_m?.toFixed(2) ?? '–'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <button
        className="btn-danger btn-block"
        disabled={remove.isPending}
        onClick={() =>
          window.confirm('Delete this activity?') &&
          remove.mutate(a.id, { onSuccess: () => navigate('/history', { replace: true }) })
        }
      >
        Delete activity
      </button>
    </div>
  )
}
