import { useRef } from 'react'
import { useUploadFit } from '../../api/hooks'

/** "Upload FIT" button with per-file results. */
export default function UploadFit() {
  const input = useRef<HTMLInputElement>(null)
  const upload = useUploadFit()
  return (
    <div className="stack">
      <input
        ref={input}
        type="file"
        accept=".fit,.FIT"
        multiple
        hidden
        onChange={(e) => {
          const files = Array.from(e.target.files ?? [])
          if (files.length) upload.mutate(files)
          e.target.value = ''
        }}
      />
      <button className="btn-small" disabled={upload.isPending} onClick={() => input.current?.click()}>
        {upload.isPending ? 'Uploading…' : 'Upload FIT'}
      </button>
      {upload.isError && <div className="banner">{upload.error.message}</div>}
      {upload.data && (
        <div className="card stack upload-results">
          {upload.data.map((r) => (
            <div key={r.filename} className="row spread">
              <span>{r.filename}</span>
              <span className={r.status === 'error' ? 'bad' : r.status === 'created' ? 'good' : 'muted'}>
                {r.status}
                {r.detail ? ` — ${r.detail}` : ''}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
