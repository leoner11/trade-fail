import { useState } from 'react'
import { glueApi } from '../../api/glue'
import type { GatesSummary } from '../../api/glue'
import { spine } from '../../api/spine'
import { Button } from '../../components/ui/Button'
import { ConfirmDialog } from '../../components/ui/ConfirmDialog'
import { GateBanner } from '../../components/ui/GateBanner'
import { SectionPanel } from '../../components/ui/SectionPanel'
import { SkeletonRows } from '../../components/ui/Skeleton'
import { StatusBadge } from '../../components/ui/StatusBadge'
import type { Tone } from '../../lib/domain'
import { formatDateTime } from '../../lib/format'
import { useAsync } from '../../lib/useAsync'
import { usePoll } from '../../lib/usePoll'

const MANUAL_ITEMS = [
  'Staff briefed on the chatwoot escalation inbox',
  'Phone drills done — formal PDF lands in chat + QR re-scan under 5 min',
  'Boss has seen and approved the pricing rules',
]

interface Check {
  key: string
  label: string
  detail?: string
  state: 'pass' | 'fail' | 'pending'
}

export function GoLivePage() {
  const summary = usePoll<GatesSummary>(() => glueApi.gatesSummary(), 10000)
  const catalog = useAsync(() => spine.listCatalog(), [])
  const kb = usePoll(() => glueApi.kbDocs().then((r) => r.items.length), 20000)
  const [manual, setManual] = useState<string[]>([])
  const [confirming, setConfirming] = useState(false)
  const [blockers, setBlockers] = useState<string[] | null>(null)
  const [busy, setBusy] = useState(false)

  const s = summary.data

  function toggle(label: string) {
    setManual((m) => (m.includes(label) ? m.filter((x) => x !== label) : [...m, label]))
  }

  if (!s) {
    return (
      <div className="mx-auto max-w-3xl">
        <SkeletonRows rows={6} />
      </div>
    )
  }

  const o2ok = !!(s.o2.found && s.o2.gate_pass)
  const o3ok = !!(s.o3.found && s.o3.gate_pass && s.o3.mode === 'REAL')
  const checks: Check[] = [
    {
      key: 'wa',
      label: 'WhatsApp session connected',
      state: s.whatsapp.state === 'open' ? 'pass' : s.whatsapp.state === undefined ? 'fail' : 'fail',
      detail: s.whatsapp.state ?? 'evo unreachable',
    },
    {
      key: 'catalog',
      label: 'Catalog ingested (S1)',
      state: (catalog.data?.items.length ?? 0) > 0 ? 'pass' : 'fail',
      detail: `${catalog.data?.items.length ?? 0} SKUs`,
    },
    {
      key: 'kb',
      label: 'Knowledge base populated',
      state: (kb.data ?? 0) > 0 ? 'pass' : 'fail',
      detail: `${kb.data ?? 0} documents`,
    },
    {
      key: 'o2',
      label: 'O2 verification quiz passed',
      state: o2ok ? 'pass' : 'fail',
      detail: s.o2.found ? `${s.o2.passed}/${s.o2.total}, ${s.o2.fabricated} fabrications` : 'not run',
    },
    {
      key: 'o3',
      label: 'O3 backtest passed on REAL history',
      state: o3ok ? 'pass' : 'fail',
      detail: s.o3.found ? `${s.o3.passed}/${s.o3.total}${s.o3.mode ? ` · ${s.o3.mode}` : ''}` : 'not run',
    },
    {
      key: 'postiz',
      label: 'Social module connected (optional add-on)',
      state: 'pending',
      detail: s.postiz_key_set ? 'postiz API key present' : 'not connected — approvals still skip+log',
    },
  ]

  const autoOk = checks.filter((c) => c.key !== 'postiz').every((c) => c.state === 'pass')
  const manualOk = manual.length === MANUAL_ITEMS.length
  const canGoLive = autoOk && manualOk
  const isLive = !!(s.go_live.found && s.go_live.go_live)

  async function go() {
    setBusy(true)
    try {
      const res = await glueApi.goLive(manual)
      if (res.ok) {
        setBlockers(null)
        summary.refresh()
      } else {
        setBlockers(res.blockers ?? ['unknown refusal'])
      }
    } finally {
      setBusy(false)
      setConfirming(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      {isLive && (
        <GateBanner
          tone="success"
          title="APPLIANCE IS LIVE"
          meta={`go-live recorded ${formatDateTime(s.go_live.ts)} · steady state = two touchpoints: chatwoot escalations + WhatsApp approvals`}
        />
      )}
      {!isLive && (
        <GateBanner
          tone="attention"
          title="No partial go-lives"
          meta="every gate below must be green before buyers see the agent (flowchart O5-1)"
        />
      )}

      <SectionPanel title="Gates" bodyClassName="p-0">
        <table className="w-full border-collapse">
          <tbody>
            {checks.map((c) => (
              <tr key={c.key} className="border-b border-line last:border-b-0">
                <td className="w-28 px-4 py-2.5">
                  <CheckTag state={c.state} />
                </td>
                <td className="px-2 py-2.5 text-body text-text-primary">{c.label}</td>
                <td className="px-4 py-2.5 text-right text-caption text-text-muted">{c.detail}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </SectionPanel>

      <SectionPanel title="Human sign-off" bodyClassName="p-0">
        {MANUAL_ITEMS.map((label) => (
          <label
            key={label}
            className="flex cursor-pointer items-center gap-3 border-b border-line px-4 py-3 last:border-b-0 hover:bg-surface-subtle"
          >
            <input
              type="checkbox"
              checked={manual.includes(label)}
              onChange={() => toggle(label)}
              className="h-4 w-4 accent-[#4F46E5]"
            />
            <span className="text-body text-text-primary">{label}</span>
          </label>
        ))}
      </SectionPanel>

      {blockers && (
        <GateBanner tone="danger" title="Go-live refused" meta={blockers.join(' · ')} />
      )}

      {!isLive && (
        <>
          <Button variant="primary" size="lg" disabled={!canGoLive} onClick={() => setConfirming(true)}>
            GO LIVE
          </Button>
          {!canGoLive && (
            <p className="text-caption text-text-muted">
              All gates green and all three confirmations checked enable the switch.
            </p>
          )}
        </>
      )}
      <ConfirmDialog
        open={confirming}
        busy={busy}
        title="Record go-live?"
        body={
          <>
            Buyers start talking to the agent on{' '}
            <span className="mono text-[13px]">{s.whatsapp.state === 'open' ? 'the live WhatsApp number' : '???'}</span>.
            This decision is written to the audit log.
          </>
        }
        confirmLabel="We are live"
        onCancel={() => setConfirming(false)}
        onConfirm={go}
      />
    </div>
  )
}

function CheckTag({ state }: { state: Check['state'] }) {
  const map: Record<Check['state'], Tone> = { pass: 'success', fail: 'danger', pending: 'neutral' }
  return <StatusBadge tone={map[state]} label={state === 'pass' ? 'ready' : state === 'fail' ? 'open' : 'info'} />
}
