import { useMemo, useState } from 'react'
import { spine } from '../../api/spine'
import type { EventRow, PostRow, QuoteRow } from '../../api/spine'
import { DataTable } from '../../components/ui/DataTable'
import { KpiTile } from '../../components/ui/KpiTile'
import { SectionPanel } from '../../components/ui/SectionPanel'
import { SkeletonRows } from '../../components/ui/Skeleton'
import { hoursAgo } from '../../lib/format'
import { useAsync } from '../../lib/useAsync'

type Period = '30d' | 'month'

const PERIODS: { key: Period; label: string; days: number | 'calendar' }[] = [
  { key: '30d', label: 'Last 30 days', days: 30 },
  { key: 'month', label: 'This month', days: 'calendar' },
]

function inPeriod(ts: string, period: Period): boolean {
  if (!ts) return false
  const d = new Date(ts.includes('T') || ts.includes('+') ? ts : ts.replace(' ', 'T') + 'Z')
  if (period === 'month') {
    const now = new Date()
    return d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth()
  }
  return hoursAgo(ts) <= 30 * 24
}

interface Freq {
  name: string
  count: number
}

export function ReportsPage() {
  const [period, setPeriod] = useState<Period>('30d')
  const quotes = useAsync(() => spine.listQuotes({ limit: 500 }), [])
  const events = useAsync(() => spine.listEvents('', 500), [])
  const posts = useAsync(() => spine.listPosts('', 200), [])

  const agg = useMemo(() => {
    const q: QuoteRow[] = quotes.data?.items ?? []
    const e: EventRow[] = events.data?.items ?? []
    const p: PostRow[] = posts.data?.items ?? []
    const qs = q.filter((r) => inPeriod(r.created_at, period))
    const es = e.filter((r) => inPeriod(r.ts, period))
    const ps = p.filter((r) => inPeriod(r.updated_at, period))

    const byStatus = new Map<string, number>()
    for (const r of qs) byStatus.set(r.status, (byStatus.get(r.status) ?? 0) + 1)
    const accepted = byStatus.get('accepted') ?? 0
    const rejected = byStatus.get('rejected') ?? 0
    const closed = accepted + rejected

    const productFreq = new Map<string, number>()
    for (const r of qs) {
      try {
        const req = JSON.parse((r as unknown as { request_json?: string }).request_json ?? '{}')
        if (!Array.isArray(req.lines)) continue
        for (const line of req.lines) {
          const m = String(line.material ?? '?')
          productFreq.set(m, (productFreq.get(m) ?? 0) + Number(line.qty ?? 1))
        }
      } catch {
        /* malformed/spike rows are simply not counted */
      }
    }

    const reasonFreq = new Map<string, number>()
    for (const ev of es) {
      if (ev.kind !== 'escalation') continue
      let intent = 'unknown'
      try {
        intent = String(JSON.parse(ev.detail_json || '{}').intent ?? 'unknown')
      } catch {
        /* keep unknown */
      }
      reasonFreq.set(intent, (reasonFreq.get(intent) ?? 0) + 1)
    }

    const toRows = (m: Map<string, number>): Freq[] =>
      [...m.entries()].map(([name, count]) => ({ name, count })).sort((a, b) => b.count - a.count)

    return {
      quotesInPeriod: qs,
      sentCount: qs.length,
      accepted,
      winRate: closed ? Math.round((accepted / closed) * 100) : null,
      valueSent: qs.reduce((s, r) => s + (r.total ?? 0), 0),
      escalations: es.filter((x) => x.kind === 'escalation').length,
      beacons: es.filter((x) => x.kind === 'sla_beacon').length,
      posted: ps.filter((x) => x.status === 'posted' || x.status === 'scheduled').length,
      pendingApproval: ps.filter((x) => x.status === 'pending').length,
      topProducts: toRows(productFreq).slice(0, 8),
      reasons: toRows(reasonFreq),
    }
  }, [quotes.data, events.data, posts.data, period])

  if (quotes.loading || events.loading || posts.loading) {
    return (
      <div className="mx-auto max-w-5xl space-y-4">
        <SkeletonRows rows={3} height={92} />
        <SkeletonRows rows={6} />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-5xl space-y-4">
      <div className="flex gap-2">
        {PERIODS.map((p) => (
          <button
            key={p.key}
            onClick={() => setPeriod(p.key)}
            aria-pressed={period === p.key}
            className={`h-7 rounded-md border px-2.5 text-caption font-medium transition-colors ${
              period === p.key
                ? 'border-brand bg-brand-wash text-brand'
                : 'border-line bg-surface-card text-text-secondary hover:bg-surface-subtle'
            }`}
          >
            {p.label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
        <KpiTile label={`Quotes sent · ${PERIODS.find((p) => p.key === period)?.label}`} value={String(agg.sentCount)} />
        <KpiTile
          label="Win rate (accepted / closed)"
          value={agg.winRate == null ? '—' : `${agg.winRate}%`}
        />
        <KpiTile label="Escalations → humans" value={String(agg.escalations)} />
        <KpiTile label="Posts published/scheduled" value={String(agg.posted)} />
      </div>

      <SectionPanel title="Money" bodyClassName="p-4">
        <p className="text-body text-text-primary tabular">
          Total quoted in period:{' '}
          <span className="font-semibold">{Math.round(agg.valueSent).toLocaleString('en-US')}</span>{' '}
          <span className="text-text-muted">(sum across currencies as-is — single-currency clients only)</span>
        </p>
      </SectionPanel>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <SectionPanel title="Top asked products" bodyClassName="p-0">
          <DataTable
            columns={[
              { key: 'name', header: 'Product', mono: true },
              { key: 'count', header: 'Units asked', align: 'right' },
            ]}
            rows={agg.topProducts}
            rowKey={(r) => r.name}
            emptyMessage="No quote activity in this period."
          />
        </SectionPanel>

        <SectionPanel title="Why the AI handed off" bodyClassName="p-0">
          <DataTable
            columns={[
              { key: 'name', header: 'Escalation intent', mono: true },
              { key: 'count', header: 'Count', align: 'right' },
            ]}
            rows={agg.reasons}
            rowKey={(r) => r.name}
            emptyMessage="Zero escalations — the machine handled everything."
          />
          <p className="border-t px-4 py-2 text-caption text-text-muted">
            Every human quote is a pricing-rules improvement opportunity (B5).
          </p>
        </SectionPanel>
      </div>

      <SectionPanel title="Social" bodyClassName="p-4">
        <p className="text-body text-text-secondary">
          {agg.posted} published/scheduled ·{' '}
          {agg.pendingApproval} waiting for boss approval ·{' '}
          {agg.beacons} SLA beacons fired
        </p>
      </SectionPanel>
    </div>
  )
}
