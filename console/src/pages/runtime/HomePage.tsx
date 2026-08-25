import { spine } from '../../api/spine'
import { GateBanner } from '../../components/ui/GateBanner'
import { KpiTile } from '../../components/ui/KpiTile'
import { SectionPanel } from '../../components/ui/SectionPanel'
import { SkeletonBlock, SkeletonRows } from '../../components/ui/Skeleton'
import type { TimelineItem } from '../../components/ui/Timeline'
import { Timeline } from '../../components/ui/Timeline'
import { GATE_LABELS } from '../../lib/domain'
import type { Tone } from '../../lib/domain'
import { hoursAgo, truncateMiddle } from '../../lib/format'
import { useAsync } from '../../lib/useAsync'

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

export function HomePage() {
  const events = useAsync(() => spine.listEvents('', 100), [])
  const quotes = useAsync(() => spine.listQuotes({ status: 'sent', older_than_hours: 48 }), [])
  const posts = useAsync(() => spine.listPosts('pending'), [])

  if (events.loading || quotes.loading || posts.loading) {
    return (
      <div className="mx-auto max-w-5xl space-y-4">
        <div className="grid grid-cols-4 gap-4">
          <SkeletonBlock height={92} />
          <SkeletonBlock height={92} />
          <SkeletonBlock height={92} />
          <SkeletonBlock height={92} />
        </div>
        <SkeletonRows rows={6} />
      </div>
    )
  }

  const allEvents = events.data?.items ?? []
  const esc24 = allEvents.filter((e) => e.kind === 'escalation' && hoursAgo(e.ts) < 24).length
  const stale = quotes.data?.items ?? []
  const pendingPosts = posts.data?.items.length ?? 0
  const today = new Date().toISOString().slice(0, 10)
  const eventsToday = allEvents.filter((e) => e.ts.startsWith(today)).length

  const queue: TimelineItem[] = allEvents.slice(0, 8).map((e) => ({
    id: e.id,
    ts: e.ts,
    title: GATE_LABELS[e.kind] ?? e.kind,
    meta: truncateMiddle(eventMeta(e.detail_json) ?? '', 140),
    tone: KIND_TONE[e.kind] ?? 'neutral',
  }))

  return (
    <div className="mx-auto max-w-5xl space-y-4">
      <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
        <KpiTile label="Escalations · 24h" value={String(esc24)} />
        <KpiTile label="Quotes awaiting >48h" value={String(stale.length)} />
        <KpiTile label="Social pending approval" value={String(pendingPosts)} />
        <KpiTile label="Events today" value={String(eventsToday)} />
      </div>

      {pendingPosts > 0 && (
        <GateBanner
          tone="attention"
          title={`${pendingPosts} social post${pendingPosts === 1 ? '' : 's'} waiting for approval`}
          meta="Approvals are WhatsApp-canonical — reply APPROVE / REJECT on the boss number."
        />
      )}
      {stale.length > 0 && (
        <GateBanner
          tone="info"
          title={`${stale.length} sent quote${stale.length === 1 ? '' : 's'} past the 48h follow-up window`}
          meta={
            stale
              .slice(0, 3)
              .map((q) => q.quote_id)
              .join(' · ') + (stale.length > 3 ? ` +${stale.length - 3}` : '')
          }
        />
      )}

      <SectionPanel title="Attention queue" bodyClassName="p-4 pl-2">
        {events.error ? (
          <p className="text-body text-[#B91C1C]">Failed to load events. Is spine up?</p>
        ) : (
          <Timeline items={queue} emptyMessage="No appliance activity yet — escalations and approvals land here." />
        )}
      </SectionPanel>
    </div>
  )
}
