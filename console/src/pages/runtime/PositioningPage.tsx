import { useState } from 'react'
import { positioningApi } from '../../api/glue'
import type { PositioningDraft, PositioningListing, PositioningResult } from '../../api/glue'
import { spine } from '../../api/spine'
import type { CatalogItem } from '../../api/spine'
import { CATALOG_TONE } from '../../lib/domain'
import { Button } from '../../components/ui/Button'
import { DataTable } from '../../components/ui/DataTable'
import type { Column } from '../../components/ui/DataTable'
import { SectionPanel } from '../../components/ui/SectionPanel'
import { StatusBadge } from '../../components/ui/StatusBadge'
import { usePoll } from '../../lib/usePoll'

// One listing per line:  title | price | url-or-note   (only title is required)
function parseListings(text: string): PositioningListing[] {
  return text
    .split('\n')
    .map((l) => l.trim())
    .filter(Boolean)
    .map((line) => {
      const [title = '', price = '', extra = ''] = line.split('|').map((s) => s.trim())
      const listing: PositioningListing = { title }
      const n = Number(price)
      if (price && Number.isFinite(n)) listing.price = n
      if (extra) {
        if (/^https?:\/\//.test(extra)) listing.url = extra
        else listing.notes = extra
      }
      return listing
    })
    .filter((l) => l.title.length > 0)
}

export function PositioningPage() {
  const [category, setCategory] = useState('')
  const [text, setText] = useState('')
  const [analyzing, setAnalyzing] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<PositioningResult | null>(null)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [promoting, setPromoting] = useState(false)
  const [promoteMsg, setPromoteMsg] = useState('')
  const [approving, setApproving] = useState('')

  const catalog = usePoll(() => spine.listCatalog(), 15_000)
  const proposed = (catalog.data?.items ?? []).filter((c) => c.status === 'proposed')

  const listings = parseListings(text)
  const canAnalyze = category.trim() && listings.length > 0 && !analyzing

  async function analyze() {
    setAnalyzing(true)
    setError('')
    setResult(null)
    setSelected(new Set())
    try {
      setResult(await positioningApi.analyze(category.trim(), listings))
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setAnalyzing(false)
    }
  }

  async function promote() {
    if (!result) return
    const drafts = result.drafts.filter((d) => selected.has(d.sku))
    if (!drafts.length) return
    setPromoting(true)
    setPromoteMsg('')
    try {
      const res = await positioningApi.promote(drafts)
      setPromoteMsg(`${res.promoted.length} draft(s) pushed to catalog as PROPOSED — approve below.`)
      setSelected(new Set())
      catalog.refresh()
    } catch (e) {
      setPromoteMsg(e instanceof Error ? e.message : String(e))
    } finally {
      setPromoting(false)
    }
  }

  async function approve(sku: string) {
    setApproving(sku)
    try {
      await spine.approveCatalogDraft(sku)
      catalog.refresh()
    } finally {
      setApproving('')
    }
  }

  function toggle(sku: string) {
    setSelected((s) => {
      const next = new Set(s)
      if (next.has(sku)) next.delete(sku)
      else next.add(sku)
      return next
    })
  }

  const draftCols: Column<PositioningDraft & { _specs: string }>[] = [
    {
      key: 'pick',
      header: '',
      width: 36,
      render: (d) => (
        <input
          type="checkbox"
          aria-label={`select ${d.sku}`}
          checked={selected.has(d.sku)}
          onChange={() => toggle(d.sku)}
        />
      ),
    },
    { key: 'sku', header: 'SKU', mono: true, width: 160 },
    { key: 'name', header: 'Name' },
    { key: 'moq', header: 'MOQ', align: 'right', width: 70 },
    { key: '_specs', header: 'Specs' },
  ]
  const draftRows = (result?.drafts ?? []).map((d) => ({
    ...d,
    _specs: Object.entries(d.specs ?? {})
      .map(([k, v]) => `${k}=${v}`)
      .join(', '),
  }))

  const proposedCols: Column<CatalogItem>[] = [
    { key: 'sku', header: 'SKU', mono: true, width: 160 },
    { key: 'name', header: 'Name' },
    { key: 'category', header: 'Category', width: 160 },
    {
      key: 'status',
      header: 'Status',
      width: 110,
      render: (r) => <StatusBadge tone={CATALOG_TONE[r.status ?? ''] ?? 'neutral'} label={r.status ?? '?'} />,
    },
    {
      key: 'act',
      header: '',
      align: 'right',
      width: 100,
      render: (r) => (
        <Button size="sm" loading={approving === r.sku} onClick={() => approve(r.sku)}>
          Approve
        </Button>
      ),
    },
  ]

  return (
    <div className="mx-auto max-w-4xl space-y-4">
      <SectionPanel title="1 · Paste marketplace listings">
        <div className="space-y-3">
          <input
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            placeholder="Category — e.g. solar panels 550W"
            aria-label="Category"
            className="h-9 w-full rounded-md border border-line bg-surface-card px-3 text-body outline-none transition-colors focus:border-brand focus:ring-2 focus:ring-brand/20"
          />
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={8}
            spellCheck={false}
            placeholder={'one listing per line:  title | price | url or note\ne.g.  mono solar panel 550W half-cut | 0.28 | https://...\n      panel 550W bifacial grade A | 0.31 | seller claims TUV'}
            aria-label="Listings"
            className="mono w-full rounded-md border border-line bg-surface-card p-3 text-caption leading-relaxed outline-none transition-colors focus:border-brand focus:ring-2 focus:ring-brand/20"
          />
          <div className="flex items-center justify-between">
            <p className="text-caption text-text-muted">
              {listings.length} listing{listings.length === 1 ? '' : 's'} parsed — analysis cites them as [L1]…[Ln]
            </p>
            <Button variant="primary" loading={analyzing} disabled={!canAnalyze} onClick={analyze}>
              Analyze
            </Button>
          </div>
          {error && <p className="text-caption text-[#EF4444]">{error}</p>}
        </div>
      </SectionPanel>

      {result && (
        <>
          <SectionPanel title="2 · Memo">
            <div className="space-y-3">
              {result.price_band && (
                <div className="flex gap-2">
                  <StatusBadge tone="info" label={`min ${result.price_band.min}`} />
                  <StatusBadge tone="info" label={`median ${result.price_band.median}`} />
                  <StatusBadge tone="info" label={`max ${result.price_band.max}`} />
                </div>
              )}
              <pre className="max-h-72 overflow-auto whitespace-pre-wrap rounded-md bg-surface-subtle p-3 text-caption leading-relaxed">
                {result.memo}
              </pre>
              <p className="mono text-micro text-text-muted">saved: {result.memo_path}</p>
            </div>
          </SectionPanel>

          {draftRows.length > 0 && (
            <SectionPanel
              title={`3 · Catalog drafts (${draftRows.length})`}
              action={
                <Button
                  variant="primary"
                  size="sm"
                  loading={promoting}
                  disabled={selected.size === 0}
                  onClick={promote}
                >
                  Promote selected ({selected.size})
                </Button>
              }
              bodyClassName="p-0"
            >
              {promoteMsg && (
                <p className="border-b border-line px-4 py-2 text-caption text-text-secondary">{promoteMsg}</p>
              )}
              <DataTable columns={draftCols} rows={draftRows} rowKey={(d) => d.sku} />
            </SectionPanel>
          )}
        </>
      )}

      <SectionPanel title={`Proposed — awaiting approval (${proposed.length})`} bodyClassName="p-0">
        <DataTable
          columns={proposedCols}
          rows={proposed}
          rowKey={(r) => r.sku}
          loading={catalog.loading && !catalog.data}
          emptyMessage="No proposed drafts. Promote analysis drafts above, or approve directly in Catalog."
        />
      </SectionPanel>
    </div>
  )
}
