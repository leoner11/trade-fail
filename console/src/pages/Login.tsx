import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { Button } from '../components/ui/Button'

export function Login() {
  const { signIn } = useAuth()
  const navigate = useNavigate()
  const [token, setToken] = useState('')
  const [error, setError] = useState('')

  function submit(e: FormEvent) {
    e.preventDefault()
    if (!token.trim()) {
      setError('Paste the console token to continue.')
      return
    }
    signIn(token.trim())
    navigate('/', { replace: true })
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-surface-base p-6">
      <form
        onSubmit={submit}
        className="w-full max-w-sm rounded-lg border border-line bg-surface-card p-6"
      >
        <div className="mb-5 flex items-center gap-2">
          <span className="flex h-9 w-9 items-center justify-center rounded-md bg-brand text-caption font-bold text-white">
            MX
          </span>
          <div>
            <p className="text-section font-semibold leading-5">Appliance Console</p>
            <p className="text-caption text-text-muted">MJCX trade-agent stack</p>
          </div>
        </div>

        <label
          htmlFor="token"
          className="mb-1 block text-micro font-medium uppercase tracking-wide text-text-secondary"
        >
          Console token
        </label>
        <input
          id="token"
          type="password"
          value={token}
          onChange={(e) => {
            setToken(e.target.value)
            setError('')
          }}
          placeholder="CONSOLE_TOKEN from .env"
          autoFocus
          className={`h-9 w-full rounded-md border px-3 text-body outline-none transition-colors focus:border-brand focus:ring-2 focus:ring-brand/20 ${
            error ? 'border-[#EF4444]' : 'border-line'
          }`}
        />
        {error ? (
          <p className="mt-1.5 text-micro text-[#B91C1C]">{error}</p>
        ) : (
          <p className="mt-1.5 text-caption text-text-muted">
            Single shared secret for this appliance — ask MJCX or read the box's .env.
          </p>
        )}

        <Button type="submit" variant="primary" size="lg" className="mt-5 w-full">
          Unlock console
        </Button>
      </form>
    </div>
  )
}
