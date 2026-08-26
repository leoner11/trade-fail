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

function DraftEditor({
  post,
  onClose,
  onSaved,
}: {
  post: PostRow
  onClose: () => void
  onSaved: () => void
}) {
  const [caption, setCaption] = useState(post.caption)
  const [hashtags, setHashtags] = useState(post.hashtags)
  const [schedule, setSchedule] = useState(post.scheduled_at ?? '')
  const [platform, setPlatform] = useState(post.platform)
  const platformsList = useAsync(() => glueApi.socialPlatforms(), [])
  const [images, setImages] = useState<string[]>(
    JSON.parse((post as unknown as { images_json?: string }).images_json ?? '[]'),
  )
  const [imgTs, setImgTs] = useState(() => Date.now())
  const [hint, setHint] = useState('')
  const [busy, setBusy] = useState('')
  const [msg, setMsg] = useState<{ tone: 'ok' | 'err'; text: string } | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  const run = async (label: string, fn: () => Promise<void>) => {
    setBusy(label); setMsg(null)
    try {
      await fn()
    } catch (e) {
      setMsg({ tone: 'err', text: errText(e) })
    } finally {
      setBusy('')
    }
  }

  return (
    <SectionPanel title={`Draft editor · ${post.post_id} (${post.sku})`} bodyClassName="p-4 space-y-3">
      <div>
        <label className="text-caption text-text-secondary">Caption</label>
        <textarea
          value={caption}
          onChange={(e) => setCaption(e.target.value)}
          rows={6}
          className="mt-1 w-full rounded-md border border-line bg-surface-card p-2.5 text-body text-text-primary"
        />
      </div>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <div>
          <label className="text-caption text-text-secondary">Post as (channel)</label>
          <select
            value={platform}
            onChange={(e) => setPlatform(e.target.value)}
            className="mt-1 w-full rounded-md border border-line bg-surface-card p-2.5 text-body text-text-primary"
          >
            {(platformsList.data?.platforms ?? [post.platform]).map((p) => (
              <option key={p} value={p}>{p === 'linkedin' ? 'LinkedIn — personal profile' : p === 'linkedin-page' ? 'LinkedIn — company page' : p}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-caption text-text-secondary">Hashtags</label>
          <input
            value={hashtags}
            onChange={(e) => setHashtags(e.target.value)}
            className="mt-1 w-full rounded-md border border-line bg-surface-card p-2.5 text-body text-text-primary"
          />
        </div>
        <div>
          <label className="text-caption text-text-secondary">Schedule (optional)</label>
          <input
            type="datetime-local"
            value={(schedule || '').slice(0, 16)}
            onChange={(e) => setSchedule(e.target.value ? new Date(e.target.value).toISOString() : '')}
            className="mt-1 w-full rounded-md border border-line bg-surface-card p-2.5 text-body text-text-primary"
          />
        </div>
      </div>

      <div>
        <label className="text-caption text-text-secondary">Pictures</label>
        <div className="mt-1 flex flex-wrap items-center gap-2">
          {images.map((_, i) => (
            <div key={i} className="relative">
              <img
                src={glueApi.draftImageUrl(post.post_id, i, imgTs)}
                alt=""
                className="h-16 w-16 rounded-md border border-line object-cover"
              />
              <button
                disabled={busy !== ''}
                onClick={() =>
                  run('imgdel', async () => {
                    await glueApi.socialRemoveImage(post.post_id, i)
                    setImages((cur) => cur.filter((_, j) => j !== i))
                    setImgTs(Date.now())
                  })
                }
                className="absolute -right-1.5 -top-1.5 h-5 w-5 rounded-full border border-line bg-surface-card text-caption text-[#B91C1C]"
                aria-label="remove picture"
              >
                ×
              </button>
            </div>
          ))}
          <button
            disabled={busy !== ''}
            onClick={() => fileRef.current?.click()}
            className="h-16 w-16 rounded-md border border-dashed border-line text-caption text-text-muted hover:bg-surface-subtle"
          >
            {busy === 'img' ? '…' : '+ add'}
          </button>
          <input
            ref={fileRef}
            type="file"
            accept=".png,.jpg,.jpeg,.webp"
            hidden
            onChange={(e) => {
              const f = e.target.files?.[0]
              if (!f) return
              run('img', async () => {
                await glueApi.socialAttachImage(post.post_id, f)
                setImages((cur) => [...cur, f.name])
                setImgTs(Date.now())
              })
              e.target.value = ''
            }}
          />
        </div>
        <p className="mt-1 text-caption text-text-muted">PNG/JPG/WebP · first picture leads the post.</p>
      </div>

      <div>
        <label className="text-caption text-text-secondary">Regenerate with guidance (optional)</label>
        <div className="mt-1 flex gap-2">
          <input
            value={hint}
            onChange={(e) => setHint(e.target.value)}
            placeholder="e.g. lead with fast lead times"
            className="w-full rounded-md border border-line bg-surface-card p-2.5 text-body text-text-primary"
          />
          <button
            disabled={busy !== ''}
            onClick={() =>
              run('regen', async () => {
                const res = await glueApi.socialRegenerate(post.post_id, hint)
                setCaption(res.caption)
                setHashtags(res.hashtags)
                setHint('')
              })
            }
            className="whitespace-nowrap rounded-md border border-brand px-3 py-1.5 text-caption font-medium text-brand hover:bg-brand-wash disabled:opacity-50"
          >
            {busy === 'regen' ? 'writing…' : 'Regenerate'}
          </button>
        </div>
      </div>

      {msg && (
        <p className={`text-caption ${msg.tone === 'ok' ? 'text-[#15803D]' : 'text-[#B91C1C]'}`}>{msg.text}</p>
      )}

      <div className="flex gap-2">
        <button
          disabled={busy !== ''}
          onClick={() =>
            run('save', async () => {
              await spine.editPost(post.post_id, {
                caption,
                hashtags,
                scheduled_at: schedule || undefined,
                platform: platform !== post.platform ? platform : undefined,
              })
              setMsg({ tone: 'ok', text: 'Saved — approve via WhatsApp (APPROVE ' + post.post_id + ')' })
              onSaved()
            })
          }
          className="rounded-md bg-brand px-3 py-1.5 text-caption font-medium text-white hover:opacity-90 disabled:opacity-50"
        >
          {busy === 'save' ? 'Saving…' : 'Save draft'}
        </button>
        <button
          onClick={onClose}
          className="rounded-md border border-line px-3 py-1.5 text-caption text-text-secondary hover:bg-surface-subtle"
        >
          Close
        </button>
      </div>
      <p className="text-caption text-text-muted">
        Approval stays on WhatsApp by design — APPROVE / REJECT {post.post_id}. Nothing schedules without it.
      </p>
    </SectionPanel>
  )
}

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
  const [editingId, setEditingId] = useState<string | null>(null)
  const editing = rows.find((r) => r.post_id === editingId && r.status === 'pending') ?? null

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
          meta="Click a pending draft to edit it here; approval stays on WhatsApp — APPROVE P-XXXXXX / REJECT P-XXXXXX."
        />
      )}
      {editing && (
        <DraftEditor
          post={editing}
          onClose={() => setEditingId(null)}
          onSaved={() => posts.retry()}
        />
      )}
      <DataTable
        columns={COLUMNS}
        rows={rows}
        rowKey={(r) => r.post_id}
        onRowClick={(r) => setEditingId(r.status === 'pending' ? r.post_id : null)}
        emptyMessage="No social drafts yet — the Monday cron fills this."
      />
      <p className="text-caption text-text-muted">
        Publishing runs through postiz's scheduling engine — drafts are approved on
        WhatsApp, channels are managed here.
      </p>
    </div>
  )
}
