import { useEffect, useRef, useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { glueApi } from '../../api/glue'

/**
 * OAuth callback landing (trap #45): providers redirect here instead of
 * postiz's own frontend. Relays the query params to glue, which completes
 * the connect against postiz's dashboard API headlessly.
 */
export function SocialCallbackPage() {
  const { provider } = useParams<{ provider: string }>()
  const [searchParams] = useSearchParams()
  const [state, setState] = useState<'working' | 'ok' | 'err'>('working')
  const [detail, setDetail] = useState('')
  const ran = useRef(false)

  useEffect(() => {
    if (ran.current) return
    ran.current = true
    if (!provider) {
      setState('err')
      setDetail('missing provider in path')
      return
    }
    glueApi
      .socialFinish(provider, Object.fromEntries(searchParams.entries()))
      .then(() => {
        setState('ok')
        setTimeout(() => window.close(), 1500)
      })
      .catch((e: unknown) => {
        setState('err')
        setDetail(e instanceof Error ? e.message : String(e))
      })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="flex min-h-screen items-center justify-center bg-surface-subtle">
      <div className="w-80 rounded-xl border border-line bg-surface-card p-6 text-center">
        <p className="text-heading-sm text-text-primary">
          {provider ?? 'channel'} connect
        </p>
        <p className="mt-3 text-body text-text-secondary">
          {state === 'working' && 'Finishing the connection…'}
          {state === 'ok' && 'Connected. This window closes itself.'}
          {state === 'err' && `Failed: ${detail}`}
        </p>
        <button
          onClick={() => window.close()}
          className="mt-4 rounded-md border border-line px-3 py-1.5 text-caption text-text-secondary hover:bg-surface-subtle"
        >
          Close window
        </button>
      </div>
    </div>
  )
}
