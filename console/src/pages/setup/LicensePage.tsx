import type { ReactNode } from 'react'
import { KeyRound, Route } from 'lucide-react'
import { agentsApi, licenseApi, type AgentRow, type LicenseState } from '../../api/glue'
import { usePoll } from '../../lib/usePoll'

const MODE_CHIP: Record<LicenseState['mode'], { label: string; cls: string }> = {
  licensed: { label: 'Licensed', cls: 'bg-brand-wash text-brand' },
  grace: { label: 'Grace period', cls: 'bg-brand-wash text-brand' },
  expired: { label: 'Expired', cls: 'bg-surface-subtle text-text-secondary' },
  open: { label: 'Not licensed (everything on)', cls: 'bg-surface-subtle text-text-secondary' },
}

const MODE_NOTE: Record<LicenseState['mode'], string> = {
  licensed: 'All licensed agent surfaces are active. Base platform always on.',
  grace: 'License expired — grace window active. Renew to avoid agent shutdown.',
  expired: 'License expired beyond grace. Licensed agent surfaces are off; your data is untouched. Contact MJCX to renew.',
  open: 'No license file found — running with everything on (back-compat). Drop a license.json issued by MJCX to switch to plan mode.',
}

function Row({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex items-center justify-between border-b border-line py-2 last:border-none">
      <span className="text-caption uppercase tracking-wide text-text-secondary">{label}</span>
      <span className="text-body text-text-primary">{value}</span>
    </div>
  )
}

function AgentCard({ a }: { a: AgentRow }) {
  return (
    <div className="rounded-md border border-line p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="text-body font-medium text-text-primary">{a.name_en}</span>
          <span className="text-caption text-text-secondary">{a.name_zh}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded-full border border-line px-2 py-0.5 text-micro uppercase tracking-wide text-text-secondary">
            {a.tier}
          </span>
          {a.status === 'available' ? (
            <span
              className={`rounded-full px-2 py-0.5 text-micro font-semibold ${
                a.licensed === null
                  ? 'bg-surface-subtle text-text-secondary'
                  : a.licensed
                    ? 'bg-brand-wash text-brand'
                    : 'bg-surface-subtle text-text-secondary'
              }`}
            >
              {a.licensed === null ? 'on (no plan)' : a.licensed ? 'licensed' : 'not in plan'}
            </span>
          ) : (
            <span className="rounded-full bg-surface-subtle px-2 py-0.5 text-micro text-text-secondary">
              roadmap — not sellable yet
            </span>
          )}
        </div>
      </div>
      {a.status === 'available' && a.onboard.length > 0 && (
        <ul className="mt-2 list-disc space-y-0.5 pl-5 text-caption text-text-secondary">
          {a.onboard.map((step) => (
            <li key={step}>{step}</li>
          ))}
        </ul>
      )}
    </div>
  )
}

export function LicensePage() {
  const { data, error } = usePoll(() => licenseApi.state(), 30_000)
  const agents = usePoll(() => agentsApi.list(), 60_000)

  if (error) {
    return (
      <div className="rounded-lg border border-line bg-surface-card p-6 text-body text-text-secondary">
        License endpoint unavailable — is the glue organ up? ({String(error).slice(0, 120)})
      </div>
    )
  }
  if (!data) return <div className="text-body text-text-secondary">Loading license…</div>

  const chip = MODE_CHIP[data.mode]

  return (
    <div className="max-w-2xl space-y-4">
      <div className="rounded-lg border border-line bg-surface-card p-6">
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <KeyRound size={18} className="text-text-secondary" />
            <h2 className="text-page font-semibold text-text-primary">License &amp; Plan</h2>
          </div>
          <span className={`rounded-full px-3 py-1 text-caption font-semibold ${chip.cls}`}>
            {chip.label}
          </span>
        </div>
        <Row label="Client" value={data.client ?? '—'} />
        <Row label="Appliance" value={data.appliance_id ?? '—'} />
        <Row label="Expires" value={data.expires_at ? new Date(data.expires_at).toLocaleString() : '—'} />
        <Row label="Grace until" value={data.grace_until ? new Date(data.grace_until).toLocaleString() : '—'} />
        <Row label="Trial" value={data.trial ? 'Yes' : 'No'} />
        <div className="pt-3">
          <span className="text-caption uppercase tracking-wide text-text-secondary">Agents on</span>
          <div className="mt-2 flex flex-wrap gap-2">
            {data.agents.length === 0 && (
              <span className="text-body text-text-secondary">—</span>
            )}
            {data.agents.map((a) => (
              <span key={a}
                className="rounded-full border border-line px-3 py-1 text-caption text-text-primary">
                {a}
              </span>
            ))}
          </div>
        </div>
        <p className="mt-4 border-t border-line pt-3 text-caption text-text-secondary">
          {data.detail || MODE_NOTE[data.mode]}
        </p>
      </div>

      <div className="rounded-lg border border-line bg-surface-card p-6">
        <div className="mb-4 flex items-center gap-2">
          <Route size={18} className="text-text-secondary" />
          <h2 className="text-page font-semibold text-text-primary">Agents</h2>
        </div>
        <div className="space-y-3">
          {(agents.data?.agents ?? []).map((a) => (
            <AgentCard key={a.id} a={a} />
          ))}
          {!agents.data && !agents.error && (
            <p className="text-caption text-text-secondary">Loading agents…</p>
          )}
          {agents.error && (
            <p className="text-caption text-text-secondary">
              Agent catalog unavailable ({String(agents.error).slice(0, 120)})
            </p>
          )}
        </div>
      </div>

      <p className="text-caption text-text-secondary">
        Execution is gated, data never: disabling an agent never touches your
        records. Renewals and plan changes are re-issued by MJCX as a signed
        license file.
      </p>
    </div>
  )
}
