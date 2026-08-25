import { useMemo, useState } from 'react'
import type { EventRow } from '../../api/spine'
import { Timeline } from '../../components/ui/Timeline'
import type { TimelineItem } from '../../components/ui/Timeline'
import { SkeletonRows } from '../../components/ui/Skeleton'
import { GATE_LABELS } from '../../lib/domain'
import type { Tone } from '../../lib/domain'
import { truncateMiddle } from '../../lib/format'
import { useAsync } from '../../lib/useAsync'
import { spine } from '../../api/spine'

const KIND_TONE: Record<string, Tone> = {
  escalation: 'danger',
  sla_beacon: 'attention',
  postiz_push_skipped: 'attention',
  followup_draft: 'ai',
  followup_sent: 'info',
  gate_o2: 'special',
  gate_o3: 'special',
  go_live: 'success',
}

function eventMeta(detail: string): string | undefined {
  if (!detail) return undefined
  try {
    const obj = JSON.parse(detail) as Record<string, unknown>
    return Object.entries(obj)
      .map(([k, v]) => `${k}=${String(v)}`)
      .join(' · ')
  } catch {
    return detail
  }
}

function toItems(rows: EventRow[]): TimelineItem[] {
  return rows.map((e) => ({
    id: e.id,
    ts: e.ts,
    title: GATE_LABELS[e.kind] ?? e.kind,
    meta: truncateMiddle(eventMeta(e.detail_json) ?? '', 180),
    tone: KIND_TONE[e.kind] ?? 'neutral',
  }))
}

const LIMITS = [20, 50, 100] as const

export function EventsPage() {
  const [kind, setKind] = useState('')
  const [limit, setLimit] = useState<number>(50)
  const events = useAsync(() => spine.listEvents(kind, limit), [kind, limit])

  const kinds = useMemo(() => {
    const set = new Set((events.data?.items ?? []).map((e) => e.kind))
    return ['all', ...Array.from(set).sort()]
  }, [events.data])

  const items = toItems(events.data?.items ?? [])

  return (
    <div className="mx-auto max-w-3xl space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        {kinds.map((k) => (
          <button
            key={k}
            onClick={() => setKind(k === 'all' ? '' : k)}
            aria-pressed={kind === k || (k === 'all' && kind === '')}
            className={`h-7 rounded-md border px-2.5 text-caption font-medium transition-colors ${
              (k === 'all' && kind === '') || k === kind
                ? 'border-brand bg-brand-wash text-brand'
                : 'border-line bg-surface-card text-text-secondary hover:bg-surface-subtle'
            }`}
          >
            {GATE_LABELS[k] ?? k}
          </button>
        ))}
        <select
          value={limit}
          onChange={(e) => setLimit(Number(e.target.value))}
          aria-label="Rows"
          className="ml-auto h-7 rounded-md border border-line bg-surface-card px-2 text-caption text-text-secondary"
        >
          {LIMITS.map((l) => (
            <option key={l} value={l}>
              Last {l}
            </option>
          ))}
        </select>
      </div>

      <div className="rounded-lg border border-line bg-surface-card p-4">
        {events.loading ? (
          <SkeletonRows rows={5} height={56} />
        ) : events.error ? (
          <p className="text-body text-[#B91C1C]">Failed to load events. ({events.error})</p>
        ) : (
          <Timeline items={items} />
        )}
      </div>
    </div>
  )
}
