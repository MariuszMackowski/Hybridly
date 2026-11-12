import { useRef, useState } from 'react'

/** Read-only text with a Copy button (falls back to select + execCommand on plain http). */
export default function CopyBox({ text }: { text: string }) {
  const area = useRef<HTMLTextAreaElement>(null)
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text)
    } catch {
      area.current?.select()
      document.execCommand('copy')
    }
    setCopied(true)
  }
  return (
    <>
      <textarea ref={area} className="mono" readOnly value={text} onFocus={(e) => e.target.select()} />
      <button onClick={copy}>{copied ? 'Copied ✓' : 'Copy'}</button>
    </>
  )
}
