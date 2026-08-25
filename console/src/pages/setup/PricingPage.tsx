import { useRef, useState } from 'react'
import { Eye, EyeOff } from 'lucide-react'
import { glueApi } from '../../api/glue'
import type { O3Result } from '../../api/glue'
import { Button } from '../../components/ui/Button'
import { DataTable } from '../../components/ui/DataTable'
import type { Column } from '../../components/ui/DataTable'
import { GateBanner } from '../../components/ui/GateBanner'
import { KeyValue, SectionPanel } from '../../components/ui/SectionPanel'
import { StatusBadge } from '../../components/ui/StatusBadge'
import { internalMaterials } from '../../lib/domain'
import type { Tone } from '../../lib/domain'
import { formatMoney } from '../../lib/format'
import { useAsync } from '../../lib/useAsync'
import { PricingEditor } from './PricingEditor'

interface BacktestRow {
  ref: string
  got?: number
  want?: number
  delta_pct?: number
  ok: boolean
  error?: string
}

const ROW_COLUMNS: Column<BacktestRow>[] = [
  { key: 'ref', header: 'Ref', mono: true, width: 110 },
  {
    key: 'got',
    header: 'Rules say',
    align: 'right',
    render: (r) => (r.got != null ? formatMoney(r.got) : '—'),
  },
  {
    key: 'want',
    header: 'Boss charged',
    align: 'right',
    render: (r) => (r.want != null ? formatMoney(r.want) : '—'),
  },
  {
    key: 'delta_pct',
    header: 'Δ',
    align: 'right',
    width: 90,
    render: (r) =>
      r.delta_pct != null ? (
        <span className={Math.abs(r.delta_pct) <= 2 ? 'text-[#15803D]' : 'text-[#B91C1C]'}>
          {r.delta_pct > 0 ? '+' : ''}
          {r.delta_pct.toFixed(1)}%
        </span>
      ) : (
        '—'
      ),
  },
]

export function PricingPage() {
  const rules = useAsync(() => glueApi.pricingRules(), [])
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState<O3Result | null>(null)
  const [error, setError] = useState('')
  const fileInput = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [editing, setEditing] = useState(false)

  if (rules.loading) return <p className="text-body text-text-muted">Loading rules…</p>
  if (rules.error || !rules.data) {
    return <p className="text-body text-[#B91C1C]">Failed to load pricing rules. ({rules.error})</p>
  }

  const { rules: r } = rules.data

  async function run(withFile: boolean) {
    setRunning(true)
    setError('')
    try {
      let res: O3Result
      if (withFile && file) {
        const history = JSON.parse(await file.text())
        res = await glueApi.o3Backtest(history.history ?? history)
      } else {
        res = await glueApi.o3SelfTest()
      }
      setResult(res)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setRunning(false)
    }
  }

  const manualOnly = r.size_coefficients.filter((s) => !s.coefficient)

  return (
    <div className={editing ? 'relative h-full overflow-hidden' : 'relative'}>
      <div className="mx-auto max-w-5xl space-y-4">
      <SectionPanel
        title="Terms"
        bodyClassName="p-4"
        action={
          <Button variant="primary" size="sm" onClick={() => setEditing(true)}>
            Edit rules
          </Button>
        }
      >
        <KeyValue
          rows={[
            ['Currency', rules.data.currency],
            ['Quote validity', `${rules.data.validity_days} days`],
            ['Authority cap', `${r.authority.max_discount_pct}% — beyond this the agent must ask the boss`],
            ['Manual-only configs', manualOnly.map((m) => m.size).join(', ') || 'none'],
          ]}
        />
        <p className="mt-3 text-caption text-text-muted mono">{rules.data.path}</p>
      </SectionPanel>

      <SectionPanel title="Base prices" bodyClassName="p-0">
        <DataTable
          columns={[
            { key: 'name', header: 'Model', mono: true },
            { key: 'base_price', header: 'Base', align: 'right', render: (m) => formatMoney(m.base_price, r.currency) },
            { key: 'bulk_price', header: 'Bulk', align: 'right', render: (m) => formatMoney(m.bulk_price, r.currency) },
            {
              key: 'visibility',
              header: 'Visibility',
              render: (m) =>
                internalMaterials(r).has(m.name) ? (
                  <span className="inline-flex items-center gap-1 text-caption" style={{ color: 'var(--ai-fg)' }}>
                    <EyeOff size={13} strokeWidth={1.75} /> internal
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-caption text-text-secondary">
                    <Eye size={13} strokeWidth={1.75} /> public
                  </span>
                ),
            },
            { key: 'note', header: 'Note', render: (m) => <span className="text-text-secondary">{m.note ?? ''}</span> },
          ]}
          rows={r.material_base_prices}
          rowKey={(m) => m.name}
          emptyMessage="No models in S2."
        />
        {internalMaterials(r).size > 0 && (
          <p className="border-t p-3 text-caption text-text-muted">
            Internal items never enter inline quoting — buyers asking for them
            are routed to a human quote (S2 v3 price_visibility).
          </p>
        )}
      </SectionPanel>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <SectionPanel title="Quantity ladder" bodyClassName="p-0">
          <DataTable
            columns={[
              { key: 'min_qty', header: 'From qty', align: 'right' },
              { key: 'discount_pct', header: 'Discount', align: 'right', render: (q) => `${q.discount_pct}%` },
              { key: 'label', header: '', render: (q) => <span className="text-caption text-text-secondary">{q.label}</span> },
            ]}
            rows={r.quantity_discounts}
            rowKey={(q) => String(q.min_qty)}
            emptyMessage="No quantity tiers."
          />
        </SectionPanel>

        <SectionPanel title="Customer tiers" bodyClassName="p-0">
          <DataTable
            columns={[
              { key: 'name', header: 'Tier', render: (t) => <span className="mono text-[13px]">{t.name}</span> },
              { key: 'price_factor', header: 'Factor', align: 'right', render: (t) => `×${t.price_factor}` },
            ]}
            rows={r.customer_tiers}
            rowKey={(t) => t.name}
            emptyMessage="No customer tiers."
          />
          <div className="border-t p-3">
            {r.customer_tiers.map((t) => (
              <p key={t.name} className="text-caption text-text-secondary">
                <span className="mono text-[13px]">{t.name}</span> · {t.payment_terms}
              </p>
            ))}
          </div>
        </SectionPanel>
      </div>

      <SectionPanel title="Process fees" bodyClassName="p-0">
        <DataTable
          columns={[
            { key: 'name', header: 'Extra' },
            { key: 'fee', header: 'Fee', align: 'right', render: (f) => formatMoney(f.fee, r.currency) },
            { key: 'note', header: '', render: (f) => <span className="text-caption text-text-secondary">{f.note}</span> },
          ]}
          rows={r.process_fees}
          rowKey={(f) => f.name}
          emptyMessage="No process fees."
        />
      </SectionPanel>

      <SectionPanel title="O3 backtest — the go-live gate" bodyClassName="p-4 space-y-3">
        <p className="text-body text-text-secondary">
          Re-computes real past quotes through calc and compares against what
          the boss charged. Pass = ≥90% within ±2% on ≥10 quotes.
        </p>
        <input
          ref={fileInput}
          type="file"
          accept=".json"
          hidden
          onChange={(e) => {
            setFile(e.target.files?.[0] ?? null)
          }}
        />
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="secondary" size="sm" onClick={() => fileInput.current?.click()}>
            {file ? file.name : 'Choose history JSON…'}
          </Button>
          <Button variant="primary" size="sm" onClick={() => run(true)} loading={running} disabled={!file}>
            Run backtest
          </Button>
          <Button variant="ghost" size="sm" onClick={() => run(false)} loading={running}>
            Self-test (example mode)
          </Button>
          <a
            href="/console-template-o3-history.json"
            onClick={(e) => {
              e.preventDefault()
              downloadTemplate()
            }}
            className="text-caption text-brand hover:underline"
          >
            template
          </a>
        </div>
        {error && <GateBanner tone="danger" title="Backtest failed to run" meta={error} />}
        {result && (
          <>
            <GateBanner
              tone={
                result.mode === 'EXAMPLE'
                  ? 'attention'
                  : result.gate_pass
                    ? 'success'
                    : 'danger'
              }
              title={
                result.mode === 'EXAMPLE'
                  ? `EXAMPLE MODE — ${result.match}/${result.total} self-consistent. Gate NOT cleared.`
                  : result.gate_pass
                    ? `O3 gate PASSED — ${result.match}/${result.total} within ±2% (${result.rate_pct}%)`
                    : `O3 gate FAILED — ${result.match}/${result.total} within ±2%. Interview round 2.`
              }
              meta={
                result.note ??
                (result.errors
                  ? `${result.errors} calc error(s)`
                  : `source: ${result.source} · ⛔ go-live blocked until this passes with REAL history`)
              }
            />
            <ResultTable rows={result.results} />
          </>
        )}
        {!result && (
          <GateBanner
            tone="attention"
            title="O3 backtest not passed yet"
            meta="capture 10–20 real past quotes (runbooks/o3-pricing-interview.md), then run here"
          />
        )}
      </SectionPanel>
      </div>

      {editing && (
        <div className="absolute inset-0 z-20">
          <PricingEditor
            initial={rules.data}
            onClose={() => {
              setEditing(false)
              rules.retry()
            }}
          />
        </div>
      )}
    </div>
  )
}

function ResultTable({ rows }: { rows: BacktestRow[] }) {
  return (
    <DataTable
      columns={[
        ...ROW_COLUMNS,
        {
          key: 'ok',
          header: '',
          width: 90,
          render: (r0) => (
            <StatusBadge tone={(r0.ok ? 'success' : 'danger') as Tone} label={r0.ok ? 'match' : 'off'} />
          ),
        },
      ]}
      rows={rows}
      rowKey={(r1) => r1.ref + String(r1.got)}
      emptyMessage="No results."
    />
  )
}

function downloadTemplate() {
  const blob = new Blob(
    [JSON.stringify([{ ref: 'REAL-001', customer_tier: 'repeat', lines: [{ material: 'DG-50', size: 'STD', qty: 2, processes: [] }], quoted_total: 10088.0 }], null, 2)],
    { type: 'application/json' },
  )
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = 'o3_history_template.json'
  a.click()
  URL.revokeObjectURL(a.href)
}
