import { useState } from 'react'
import {
  useStravaComplete,
  useStravaConnect,
  useStravaCredentials,
  useStravaDisconnect,
  useStravaStatus,
} from '../../api/hooks'

/** Step 1: register a personal Strava API app and paste its keys. */
function CredentialsForm({ callbackDomain, onSaved }: { callbackDomain: string; onSaved?: () => void }) {
  const save = useStravaCredentials()
  const [clientId, setClientId] = useState('')
  const [secret, setSecret] = useState('')
  return (
    <div className="stack">
      <ol className="muted steps">
        <li>
          Open{' '}
          <a href="https://www.strava.com/settings/api" target="_blank" rel="noopener">
            strava.com/settings/api
          </a>{' '}
          (logged in to your Strava account) and create an app.
        </li>
        <li>Name: Hybridly · Category: Training · Website: anything, e.g. http://localhost.</li>
        <li>
          Authorization Callback Domain: <strong>{callbackDomain}</strong>
        </li>
        <li>Copy the Client ID and Client Secret here.</li>
      </ol>
      {save.isError && <div className="banner">{save.error.message}</div>}
      <input inputMode="numeric" placeholder="Client ID" value={clientId} onChange={(e) => setClientId(e.target.value)} />
      <input placeholder="Client Secret" value={secret} onChange={(e) => setSecret(e.target.value)} />
      <button
        className="btn-primary"
        disabled={!clientId.trim() || !secret.trim() || save.isPending}
        onClick={() => save.mutate({ client_id: clientId.trim(), client_secret: secret.trim() }, { onSuccess: onSaved })}
      >
        Save keys
      </button>
    </div>
  )
}

/** Step 2: log in to Strava; without PUBLIC_URL the redirect address is pasted back. */
function ConnectStep({ callbackDomain }: { callbackDomain: string }) {
  const connect = useStravaConnect()
  const complete = useStravaComplete()
  const [authUrl, setAuthUrl] = useState<string | null>(null)
  const [pasted, setPasted] = useState('')
  /** Get the login URL and open it in a new tab. */
  const start = () =>
    connect.mutate(undefined, {
      onSuccess: ({ authorize_url }) => {
        setAuthUrl(authorize_url)
        window.open(authorize_url, '_blank', 'noopener')
      },
    })
  return (
    <div className="stack">
      {[connect, complete].map((m, i) => (m.isError ? <div key={i} className="banner">{m.error.message}</div> : null))}
      <button className="btn-primary" disabled={connect.isPending} onClick={start}>
        Connect Strava
      </button>
      {authUrl && (
        <a href={authUrl} target="_blank" rel="noopener">
          Nothing opened? Tap here to log in to Strava ›
        </a>
      )}
      {authUrl && callbackDomain === 'localhost' && (
        <>
          <span className="muted">
            Tap <em>Authorize</em> on the page that opened. It then ends on an error page whose address starts with
            http://localhost — copy that whole address and paste it here:
          </span>
          <input placeholder="http://localhost/api/strava/callback?…code=…" value={pasted} onChange={(e) => setPasted(e.target.value)} />
          <button
            disabled={!pasted.includes('code=') || complete.isPending}
            onClick={() => complete.mutate(pasted.trim(), { onSuccess: () => setPasted('') })}
          >
            Finish connecting
          </button>
        </>
      )}
    </div>
  )
}

/** Strava connection: own API app keys, login, and disconnect. */
export default function StravaCard({ error }: { error?: string | null }) {
  const status = useStravaStatus().data
  const disconnect = useStravaDisconnect()
  const [editKeys, setEditKeys] = useState(false)
  if (!status) return null
  return (
    <div className="card stack">
      <div className="row spread">
        <strong>Strava</strong>
        <span className={status.connected ? 'good' : 'muted'}>
          {status.connected ? `connected${status.athlete_name ? ` · ${status.athlete_name}` : ''}` : 'disconnected'}
        </span>
      </div>
      {error && <div className="banner">Strava: {error}</div>}
      <span className="muted">Send strength workouts to Strava: the watch activity gets your sets as its description, or a new Weight Training activity is created.</span>
      {!status.has_credentials || editKeys ? (
        <CredentialsForm callbackDomain={status.callback_domain} onSaved={() => setEditKeys(false)} />
      ) : status.connected ? (
        <div className="row">
          <button className="btn-small" onClick={() => window.confirm('Disconnect Strava?') && disconnect.mutate()}>
            Disconnect
          </button>
        </div>
      ) : (
        <>
          <ConnectStep callbackDomain={status.callback_domain} />
          <button className="btn-small" style={{ alignSelf: 'flex-start' }} onClick={() => setEditKeys(true)}>
            Change API keys
          </button>
        </>
      )}
    </div>
  )
}
