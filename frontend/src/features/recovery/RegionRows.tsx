import type { RecoveryState } from '../../api/types'
import { fatigueColor } from '../../lib/muscles'

const LABEL: Record<string, string> = { upper: 'Upper body + core', lower: 'Lower body' }

/** Upper / lower recovery % with hours until each region is ready. */
export default function RegionRows({ regions }: { regions: RecoveryState['regions'] }) {
  return (
    <div className="stack" style={{ gap: 4 }}>
      {regions.map((r) => (
        <div key={r.region} className="row spread">
          <span>{LABEL[r.region] ?? r.region}</span>
          <span>
            <strong style={{ color: fatigueColor(1 - r.recovery_pct / 100) }}>{r.recovery_pct}%</strong>
            <span className="muted"> · {r.hours_to_ready ? `ready in ${r.hours_to_ready} h` : 'ready'}</span>
          </span>
        </div>
      ))}
    </div>
  )
}
