import { useState } from 'react'
import { intelApi } from '../../api/glue'
import type { IntelDigest } from '../../api/glue'
import { spine } from '../../api/spine'
import type { IntelItem } from '../../api/spine'
import { INTEL_TONE } from '../../lib/domain'
import { Button } from '../../components/ui/Button'
import { DataTable } from '../../components/ui/DataTable'
import type { Column } from '../../components/ui/DataTable'
import { SectionPanel } from '../../components/ui/SectionPanel'
import { StatusBadge } from '../../components/ui/StatusBadge'
import { formatStamp } from '../../lib/format'
import { usePoll } from '../../lib/usePoll'

const KINDS = ['', 'news', 'tariff', 'price_watch'] as const
const KIND_LABEL: Record<string, string> = {
  '': 'All kinds',
  news: 'News',
  tariff: 'Tariff',
  price_watch: 'Price watch',
}

export function IntelPage() {
  const [kind, setKind] = useState('')
  const items = usePoll(() => spine.listIntel(100, kind), 30_000)

  const [fetching, setFetching] = useState(false)
  const [fetchMsg, setFetchMsg] = useState('')
  const [hours, setHours] = useState(24)
  const [digest, setDigest] = useState<IntelDigest | null>(null)
  const [digesting, setDigesting] = useState(false)
  const [error, setError] = useState('')

  async function fetchFeeds() {
    setFetching(true)
    setFetchMsg('')
    setError('')
    try {
      const res = await intelApi.fetchFeeds()
      setFetchMsg(`${res.feeds} feed(s) pulled — ${res.new_items} new item(s).`)
      items.refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setFetching(false)
    }
  }

  async function generateDigest() {
    setDigesting(true)
    setError('')
    try {
      setDigest(await intelApi.digest(hours))
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setDigesting(false)
    }
  }

  const cols: Column<IntelItem>[] = [
    { key: 'id', header: 'ID', mono: true, width: 60, render: (r) => `I${r.id}` },
    { key: 'ts', header: 'Seen', width: 130, render: (r) => formatStamp(r.ts) },
    {
      key: 'kind',
      header: 'Kind',
      width: 120,
      render: (r) => <StatusBadge tone={INTEL_TONE[r.kind] ?? 'neutral'} label={r.kind} />,
    },
    {
      key: 'title',
      header: 'Title',
      render: (r) =>
        r.url ? (
          <a
            href={r.url}
            target="_blank"
            rel="noreferrer"
            className="text-body text-brand hover:underline"
          >
            {r.title || r.url}
          </a>
        ) : (
          <span className="text-body">{r.title || '—'}</span>
        ),
    },
    { key: 'source', header: 'Source', width: 200 },
  ]

  return (
    <div className="mx-auto max-w-4xl space-y-4">
      <SectionPanel title="Feeds & boss digest">
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="primary" loading={fetching} onClick={fetchFeeds}>
              Fetch feeds now
            </Button>
            <span className="text-caption text-text-muted">Digest window</span>
            <select
              value={hours}
              onChange={(e) => setHours(Number(e.target.value))}
              aria-label="Digest window"
              className="h-9 rounded-md border border-line bg-surface-card px-2 text-body outline-none focus:border-brand"
            >
              <option value={24}>24h</option>
              <option value={72}>72h</option>
              <option value={168}>7 days</option>
            </select>
            <Button loading={digesting} onClick={generateDigest}>
              Generate digest
            </Button>
          </div>
          {fetchMsg && <p className="text-caption text-text-secondary">{fetchMsg}</p>}
          {error && <p className="text-caption text-[#EF4444]">{error}</p>}
          {digest && (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <StatusBadge
                  tone={digest.mode === 'glm' ? 'ai' : 'neutral'}
                  label={digest.mode === 'glm' ? 'GLM summary' : 'deterministic'}
                />
                <span className="text-caption text-text-muted">
                  {digest.item_ids.length} item(s) cited
                </span>
              </div>
              <pre className="max-h-72 overflow-auto whitespace-pre-wrap rounded-md bg-surface-subtle p-3 text-caption leading-relaxed">
                {digest.digest}
              </pre>
              <p className="text-micro text-text-muted">
                Every claim cites [I&lt;id&gt;] rows from the table below — the model may not add
                knowledge.
              </p>
            </div>
          )}
          <p className="text-micro text-text-muted">
            Price-watch webhooks (changedetection.io) POST to{' '}
            <span className="mono">{`${window.location.origin}/glue/console/intel/watch`}</span>
          </p>
        </div>
      </SectionPanel>

      <SectionPanel
        title={`Intel items (${items.data?.items.length ?? 0})`}
        action={
          <select
            value={kind}
            onChange={(e) => setKind(e.target.value)}
            aria-label="Filter by kind"
            className="h-8 rounded-md border border-line bg-surface-card px-2 text-caption outline-none focus:border-brand"
          >
            {KINDS.map((k) => (
              <option key={k} value={k}>
                {KIND_LABEL[k]}
              </option>
            ))}
          </select>
        }
        bodyClassName="p-0"
      >
        <DataTable
          columns={cols}
          rows={items.data?.items ?? []}
          rowKey={(r) => String(r.id)}
          loading={items.loading && !items.data}
          emptyMessage="No intel yet — fetch feeds or point changedetection.io at the watch webhook."
        />
      </SectionPanel>
    </div>
  )
}
