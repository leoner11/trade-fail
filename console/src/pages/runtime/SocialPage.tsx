import { useEffect, useRef, useState } from 'react'
import { glueApi } from '../../api/glue'
import type { SocialChannel } from '../../api/glue'
import { spine } from '../../api/spine'
import type { PostRow } from '../../api/spine'
import { GateBanner } from '../../components/ui/GateBanner'
import { DataTable } from '../../components/ui/DataTable'
import type { Column } from '../../components/ui/DataTable'
import { SectionPanel } from '../../components/ui/SectionPanel'
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

const errText = (e: unknown) => (e instanceof Error ? e.message : String(e))

function ChannelsPanel() {
  const channels = useAsync(() => glueApi.socialChannels(), [])
  const platforms = useAsync(() => glueApi.socialPlatforms(), [])
  const [busy, setBusy] = useState('')
  const [msg, setMsg] = useState<{ tone: 'ok' | 'err'; text: string } | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // while a consent popup is open, refresh the channel list when it closes
  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current) }, [])

  const startPoll = (popup: Window | null) => {
    if (pollRef.current) clearInterval(pollRef.current)
    pollRef.current = setInterval(() => {
      if (!popup || popup.closed) {
        if (pollRef.current) clearInterval(pollRef.current)
        channels.retry()
      }
    }, 1500)
  }

  const connect = async (platform: string) => {
    setBusy(platform); setMsg(null)
    try {
      const res = await glueApi.socialConnectUrl(platform)
      if (res.url) {
        const popup = window.open(res.url, 'postiz-oauth', 'width=520,height=680')
        startPoll(popup)
      } else {
        setMsg({ tone: 'err', text: res.err ?? 'no url returned' })
      }
    } catch (e) {
      setMsg({ tone: 'err', text: errText(e) })
    } finally {
      setBusy('')
    }
  }

  const remove = async (ch: SocialChannel) => {
    if (!window.confirm(`Disconnect ${ch.name || ch.platform}?`)) return
    setBusy(ch.id); setMsg(null)
    try {
      await glueApi.socialDelete(ch.id)
      await channels.retry()
    } catch (e) {
      setMsg({ tone: 'err', text: errText(e) })
    } finally {
      setBusy('')
    }
  }

  const list = channels.data?.channels ?? []

  return (
    <SectionPanel title="Channels" bodyClassName="p-4">
      <p className="text-caption text-text-muted">
        Connected accounts the agent publishes through. Connect opens the platform's own
        consent window — postiz's dashboard is never needed.
      </p>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        {(platforms.data?.platforms ?? []).map((p) => (
          <button
            key={p}
            disabled={busy === p}
            onClick={() => connect(p)}
            className="h-7 rounded-md border border-line bg-surface-card px-2.5 text-caption font-medium text-text-secondary transition-colors hover:bg-surface-subtle disabled:opacity-50"
          >
            + Connect {p}
          </button>
        ))}
        {platforms.loading && <span className="text-caption text-text-muted">loading…</span>}
      </div>
      {msg && (
        <p className={`mt-2 text-caption ${msg.tone === 'ok' ? 'text-[#15803D]' : 'text-[#B91C1C]'}`}>
          {msg.text}
        </p>
      )}
      {list.length > 0 ? (
        <ul className="mt-3 divide-y divide-line rounded-lg border border-line bg-surface-card">
          {list.map((ch) => (
            <li key={ch.id} className="flex items-center justify-between px-4 py-2.5">
              <div className="flex items-center gap-3">
                {ch.picture
                  ? <img src={ch.picture} alt="" className="h-8 w-8 rounded-full object-cover" />
                  : <div className="h-8 w-8 rounded-full bg-surface-subtle" />}
                <div>
                  <p className="text-body text-text-primary">{ch.name || ch.platform}</p>
                  <p className="text-caption text-text-muted">{ch.platform}{ch.disabled ? ' · disabled' : ''}</p>
                </div>
              </div>
              <button
                disabled={busy === ch.id}
                onClick={() => remove(ch)}
                className="rounded-md border border-line px-2 py-1 text-caption text-[#B91C1C] hover:bg-surface-subtle disabled:opacity-50"
              >
                Disconnect
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-3 text-body text-text-secondary">
          No channels connected yet — scheduling stays blocked until one is connected.
        </p>
      )}
    </SectionPanel>
  )
}

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
      <ChannelsPanel />
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
        Publishing runs through postiz's scheduling engine — drafts are approved on
        WhatsApp, channels are managed here.
      </p>
    </div>
  )
}
