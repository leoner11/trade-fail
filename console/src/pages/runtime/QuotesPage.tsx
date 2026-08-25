import { Check } from 'lucide-react'
import { useSearchParams } from 'react-router-dom'
import { glueApi } from '../../api/glue'
import { spine } from '../../api/spine'
import type { QuoteDetail, QuoteRow } from '../../api/spine'
import { internalMaterials } from '../../lib/domain'
import { KeyValue, SectionPanel } from '../../components/ui/SectionPanel'
import { SkeletonRows } from '../../components/ui/Skeleton'
import { StatusBadge } from '../../components/ui/StatusBadge'
import { QUOTE_TONE } from '../../lib/domain'
import type { QuoteStatus } from '../../lib/domain'
import { formatDateTime, formatMoney } from '../../lib/format'
import { useAsync } from '../../lib/useAsync'
import { DataTable } from '../../components/ui/DataTable'
import type { Column } from '../../components/ui/DataTable'

const RAIL: QuoteStatus[] = ['draft', 'sent', 'viewed', 'accepted']
const BRANCHES: QuoteStatus[] = ['negotiating', 'rejected']

function StageRail({ status }: { status: QuoteStatus }) {
  const idx = RAIL.indexOf(status)
  return (
    <div className="flex items-center gap-1">
      {RAIL.map((s, i) => {
        const done = idx >= 0 && i < idx
        const current = s === status
        return (
          <div key={s} className="flex items-center gap-1">
            {i > 0 && <span className={`h-px w-5 ${done ? 'bg-[#22C55E]' : 'bg-line'}`} aria-hidden />}
            <span
              className={`flex h-4 w-4 items-center justify-center rounded-full text-[9px] ${
                done
                  ? 'bg-[#22C55E] text-white'
                  : current
                    ? 'bg-brand text-white'
                    : 'border-[1.5px] border-line bg-surface-card text-transparent'
              }`}
            >
              {done && <Check size={10} strokeWidth={3} />}
              {current && '●'}
            </span>
          </div>
        )
      })}
      <span className="ml-2 text-caption uppercase tracking-wide text-text-muted">
        {status}
      </span>
    </div>
  )
}

const LIST_COLUMNS: Column<QuoteRow>[] = [
  { key: 'quote_id', header: 'Quote', mono: true, width: 110 },
  {
    key: 'total',
    header: 'Total',
    align: 'right',
    width: 130,
    render: (r) => formatMoney(r.total, r.currency),
  },
  {
    key: 'status',
    header: 'Status',
    width: 120,
    render: (r) => <StatusBadge tone={QUOTE_TONE[r.status as QuoteStatus] ?? 'neutral'} label={r.status} />,
  },
]

function quoteMaterials(r: QuoteRow): string[] {
  // spine returns request_json as a JSON string; spike rows may carry "lines": 1
  try {
    const req = typeof r.request_json === 'string'
      ? JSON.parse(r.request_json)
      : r.request_json
    const lines = (req as { lines?: unknown })?.lines
    if (!Array.isArray(lines)) return []
    return lines
      .map((l) => String((l as { material?: string })?.material ?? ''))
      .filter(Boolean)
  } catch {
    return []
  }
}

export function QuotesPage() {
  const list = useAsync(() => spine.listQuotes({ limit: 200 }), [])
  const rules = useAsync(() => glueApi.pricingRules(), [])
  const [params, setParams] = useSearchParams()

  if (list.loading) {
    return (
      <div className="mx-auto max-w-6xl">
        <SkeletonRows rows={8} />
      </div>
    )
  }
  if (list.error) {
    return (
      <div className="mx-auto max-w-6xl">
        <p className="text-body text-[#B91C1C]">Failed to load quotes — is spine on :8101? ({list.error})</p>
      </div>
    )
  }

  const hidden = internalMaterials(rules.data?.rules)
  const rows = (list.data?.items ?? []).map((r) => ({
    ...r,
    _internal: quoteMaterials(r).some((m) => hidden.has(m)),
  }))
  const activeId = params.get('q') ?? ''
  const selected: (QuoteRow & { _internal?: boolean }) | undefined = rows.find(
    (r) => r.quote_id === activeId,
  )

  return (
    <QuotesList
      rows={rows}
      selected={selected}
      onSelect={(row) => setParams(row ? { q: row.quote_id } : {})}
    />
  )
}

function QuotesList({
  rows,
  selected,
  onSelect,
}: {
  rows: (QuoteRow & { _internal?: boolean })[]
  selected?: QuoteRow & { _internal?: boolean }
  onSelect: (row?: QuoteRow) => void
}) {
  return (
    <div className="mx-auto grid h-full max-w-7xl grid-cols-1 items-start gap-4 lg:grid-cols-[45%_1fr]">
      <DataTable
        columns={[
          ...LIST_COLUMNS.map((c) =>
            c.key === 'total'
              ? {
                  ...c,
                  render: (r: QuoteRow & { _internal?: boolean }) =>
                    r._internal ? (
                      <span className="text-text-muted" title="contains internal-only items">—</span>
                    ) : (
                      formatMoney(r.total, r.currency)
                    ),
                }
              : c,
          ),
          {
            key: 'visibility',
            header: '',
            width: 90,
            render: (r: QuoteRow & { _internal?: boolean }) =>
              r._internal ? (
                <StatusBadge tone="special" label="internal" />
              ) : null,
          },
        ]}
        rows={rows}
        rowKey={(r) => r.quote_id}
        activeKey={selected?.quote_id}
        onRowClick={(r) => onSelect(selected?.quote_id === r.quote_id ? undefined : r)}
        emptyMessage="No quotes yet — buyers asking prices will create them."
      />
      {selected ? (
        <QuoteDetailPanel quoteId={selected.quote_id} internal={selected._internal} />
      ) : (
        <div className="hidden items-center justify-center rounded-lg border border-dashed border-line lg:flex lg:min-h-[300px]">
          <p className="text-body text-text-muted">Select a quote to see details.</p>
        </div>
      )}
    </div>
  )
}

function QuoteDetailPanel({ quoteId, internal }: { quoteId: string; internal?: boolean }) {
  const detail = useAsync(() => spine.getQuote(quoteId), [quoteId])

  if (detail.loading || !detail.data) {
    return (
      <SectionPanel title={quoteId}>
        <SkeletonRows rows={4} height={36} />
      </SectionPanel>
    )
  }

  const q: QuoteDetail = detail.data
  const status = q.status as QuoteStatus

  return (
    <div className="space-y-4">
      <SectionPanel
        title={q.quote_id}
        action={
          <div className="flex items-center gap-2">
            {internal && (
              <StatusBadge tone="special" label="internal — totals hidden from buyer views" />
            )}
            <StageRail status={status} />
          </div>
        }
        bodyClassName="p-4 space-y-4"
      >
        <KeyValue
          rows={[
            ['Customer', <span key="c" className="mono text-[13px]">{q.customer_id}</span>],
            ['Total', <span key="t" className="font-semibold">{formatMoney(q.total, q.currency)}</span>],
            ['Created', formatDateTime(q.created_at)],
            ['Updated', formatDateTime(q.updated_at)],
            [
              'PDF',
              q.pdf_path ? (
                <span key="p" className="mono text-[13px]">{q.pdf_path}</span>
              ) : (
                <span key="p">—</span>
              ),
            ],
          ]}
        />
        {BRANCHES.includes(status) && (
          <StatusBadge tone={QUOTE_TONE[status]} label={`branch: ${status}`} />
        )}
      </SectionPanel>

      <SectionPanel title="Parsed request" bodyClassName="p-0">
        <pre
          className="max-h-56 overflow-auto rounded-b-lg p-4 text-caption leading-relaxed text-text-primary"
          style={{ background: 'var(--ai-wash)' }}
        >
          {JSON.stringify(q.request_json, null, 2)}
        </pre>
        <p className="border-t px-4 py-2 text-micro" style={{ color: 'var(--ai-fg)' }}>
          Extracted by the model — digits verified by calc before quoting.
        </p>
      </SectionPanel>

      <SectionPanel title="Calc result" bodyClassName="p-0">
        <pre className="max-h-56 overflow-auto rounded-b-lg bg-surface-subtle p-4 text-caption leading-relaxed">
          {JSON.stringify(q.result_json, null, 2)}
        </pre>
        <p className="border-t px-4 py-2 text-caption text-text-muted">
          Deterministic output — the LLM never touched this math.
        </p>
      </SectionPanel>
    </div>
  )
}
