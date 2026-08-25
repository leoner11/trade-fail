import { useEffect, useRef, useState } from 'react'

export function usePoll<T>(fn: () => Promise<T>, ms: number, active = true) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(active)
  const fnRef = useRef(fn)
  useEffect(() => {
    fnRef.current = fn
  })

  useEffect(() => {
    if (!active) {
      setLoading(false)
      return
    }
    let alive = true
    let first = true
    const tick = () => {
      fnRef.current()
        .then((d) => {
          if (!alive) return
          setData(d)
          setError(null)
          if (first) setLoading(false)
          first = false
        })
        .catch((e: unknown) => {
          if (!alive) return
          if (data === null) setData(null)
          setError(e instanceof Error ? e.message : String(e))
          if (first) setLoading(false)
          first = false
        })
    }
    tick()
    const id = setInterval(tick, ms)
    return () => {
      alive = false
      clearInterval(id)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, ms])

  const refresh = () => fnRef.current().then((d) => { setData(d); return d }).catch(() => undefined)
  return { data, error, loading, refresh }
}
