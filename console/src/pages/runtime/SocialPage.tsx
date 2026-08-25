import { spine } from '../../api/spine'
import type { PostRow } from '../../api/spine'
import { GateBanner } from '../../components/ui/GateBanner'
import { DataTable } from '../../components/ui/DataTable'
import type { Column } from '../../components/ui/DataTable'
import { SkeletonRows } from '../../components/ui/Skeleton'
import { StatusBadge } from '../../components/ui/StatusBadge'
import { POST_TONE } from '../../lib/domain'
import type { PostStatus } from '../../lib/domain'
import { formatDateTime } from '../../lib/format'
import { useAsync } from '../../lib/useAsync'

const COLUMNS: Column<PostRow>[] = [
  { key: 'post_id', header: 'Post', mono: true, width: 100 },
  { key: 'sku', header: 'SKU', mono: true, width: 100 },
  { key: 'platform', header: 'Platform', width: 110 },
  {
    key: 'caption',
    header: 'Caption',
    render: (r) => <span className="line-clamp-2 text-text-secondary">{r.caption}</span>,
  },
  {
    key: 'status',
    header: 'Status',
    width: 120,
    render: (r) => (
      <StatusBadge tone={POST_TONE[r.status as PostStatus] ?? 'neutral'} label={r.status} />
    ),
  },
  {
    key: 'scheduled_at',
    header: 'Scheduled',
    width: 150,
    render: (r) => (r.scheduled_at ? formatDateTime(r.scheduled_at) : '—'),
  },
]

export function SocialPage() {
  const posts = useAsync(() => spine.listPosts(), [])
  const rows = posts.data?.items ?? []
  const pending = rows.filter((r) => r.status === 'pending').length

  if (posts.loading) {
    return (
      <div className="mx-auto max-w-6xl">
        <SkeletonRows rows={6} />
      </div>
    )
  }
  if (posts.error) {
    return (
      <div className="mx-auto max-w-6xl">
        <p className="text-body text-[#B91C1C]">Failed to load the social queue. ({posts.error})</p>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-6xl space-y-4">
      {pending > 0 && (
        <GateBanner
          tone="attention"
          title={`${pending} draft${pending === 1 ? '' : 's'} waiting for the boss`}
          meta="WhatsApp is the approval channel — APPROVE P-XXXXXX / REJECT P-XXXXXX. This queue is read-only by design."
        />
      )}
      <DataTable
        columns={COLUMNS}
        rows={rows}
        rowKey={(r) => r.post_id}
        emptyMessage="No social drafts yet — the Monday cron fills this."
      />
      <p className="text-caption text-text-muted">
        Publishing happens in postiz (:13000) — this console reads S6 state only.
      </p>
    </div>
  )
}
