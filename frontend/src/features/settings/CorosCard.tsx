import { useState } from 'react'
import { useCorosComplete, useCorosConnect, useCorosStatus, useCorosSync } from '../../api/hooks'
import { dateTime } from '../../lib/format'

/** COROS connection: connect (or paste the redirect URL), sync now, last result. */
export default function CorosCard() {
  const status = useCorosStatus()
  const connect = useCorosConnect()
  const complete = useCorosComplete()
  const sync = useCorosSync()
  const [pasted, setPasted] = useState('')
  const [authUrl, setAuthUrl] = useState<string | null>(null)
  const s = status.data
  const last = s?.last_sync_status
  const connected = s?.status === 'connected'

  /** Get the login URL and open it in a new tab. */
  const startConnect = () =>
    connect.mutate(undefined, {
      onSuccess: ({ authorize_url }) => {
        setAuthUrl(authorize_url)
        window.open(authorize_url, '_blank', 'noopener')
      },
    })

  return (
    <div className="card stack">
      <div className="row spread">
        <strong>COROS</strong>
        <span className={connected ? 'good' : s?.status === 'needs_reconnect' ? 'bad' : 'muted'}>
          {s?.status === 'needs_reconnect' ? 'reconnect needed' : (s?.status ?? '…')}
        </span>
      </div>
      {[connect, complete, sync].map((m, i) =>
        m.isError ? (
          <div key={i} className="banner">
            {m.error.message}
          </div>
        ) : null,
      )}

      {connected ? (
        <>
          <button className="btn-primary" disabled={s.syncing || sync.isPending} onClick={() => sync.mutate()}>
            {s.syncing ? 'Syncing…' : 'Sync now'}
          </button>
          {s.last_sync_at && (
            <span className="muted">
              Last sync {dateTime(s.last_sync_at)}
              {last?.imported !== undefined && ` · ${last.imported} new`}
              {last?.deferred ? ` · ${last.deferred} waiting (daily limit)` : ''}
              {last?.unparsable ? ` · ${last.unparsable} unreadable records` : ''}
            </span>
          )}
          {(last?.errors ?? []).map((e) => (
            <span key={e} className="bad">
              {e}
            </span>
          ))}
        </>
      ) : (
        <>
          <button className="btn-primary" disabled={connect.isPending} onClick={startConnect}>
            {s?.status === 'needs_reconnect' ? 'Reconnect COROS' : 'Connect COROS'}
          </button>
          {authUrl && (
            <div className="stack">
              <span className="muted">
                Log in on the page that opened. If it ends on an error page (address starting with{' '}
                {s?.redirect_uri}), copy that whole address and paste it here:
              </span>
              <input placeholder="http://localhost:8765/callback?code=…" value={pasted} onChange={(e) => setPasted(e.target.value)} />
              <button
                disabled={!pasted.includes('code=') || complete.isPending}
                onClick={() => complete.mutate(pasted.trim(), { onSuccess: () => setPasted('') })}
              >
                Finish connecting
              </button>
              <a className="muted" href={authUrl} target="_blank" rel="noopener">
                Open login page again
              </a>
            </div>
          )}
        </>
      )}
    </div>
  )
}
