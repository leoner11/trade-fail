import { Bot, Send } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { useSearchParams } from 'react-router-dom'
import { glueApi } from '../../api/glue'
import type { InboxConversation, InboxMessage } from '../../api/glue'
import { Button } from '../../components/ui/Button'
import { SkeletonRows } from '../../components/ui/Skeleton'
import { StatusBadge } from '../../components/ui/StatusBadge'
import { formatChatStamp, formatClock, truncateMiddle } from '../../lib/format'
import { usePoll } from '../../lib/usePoll'

const REFRESH_MS = 5000

export function InboxPage() {
  const [params, setParams] = useSearchParams()
  const activeId = params.get('c') ?? ''
  const convs = usePoll(() => glueApi.inboxConversations(), REFRESH_MS)

  const rows = convs.data?.items ?? []
  const selected = rows.find((c) => String(c.id) === activeId)

  return (
    <div className="grid h-full min-h-0 grid-cols-1 gap-4 lg:grid-cols-[45%_1fr]">
      <div className="min-h-0 overflow-y-auto rounded-lg border border-line bg-surface-card">
        <ConversationList
          rows={rows}
          loading={convs.loading}
          error={convs.error}
          activeId={activeId}
          onSelect={(c) => setParams(c ? { c: String(c.id) } : {})}
        />
      </div>
      {selected ? (
        <ThreadPanel key={selected.id} cid={selected.id} />
      ) : (
        <div className="hidden items-center justify-center rounded-lg border border-dashed border-line lg:flex">
          <p className="text-body text-text-muted">
            Select a conversation — live from the WhatsApp inbox.
          </p>
        </div>
      )}
    </div>
  )
}

function ConversationList({
  rows,
  loading,
  error,
  activeId,
  onSelect,
}: {
  rows: InboxConversation[]
  loading: boolean
  error: string | null
  activeId: string
  onSelect: (c?: InboxConversation) => void
}) {
  if (loading && !rows.length)
    return (
      <div className="p-4">
        <SkeletonRows rows={6} height={52} />
      </div>
    )
  if (error && !rows.length)
    return (
      <p className="p-4 text-body text-[#B91C1C]">
        Inbox unavailable — is chatwoot on :3000? ({error})
      </p>
    )
  return (
    <ul className="divide-y divide-line">
      {rows.map((c) => {
        const active = String(c.id) === activeId
        return (
          <li key={c.id}>
            <button
              onClick={() => onSelect(active ? undefined : c)}
              className={`w-full px-4 py-3 text-left transition-colors duration-150 ${
                active ? 'bg-brand-wash' : 'hover:bg-surface-subtle'
              }`}
              style={active ? { boxShadow: 'inset 2px 0 0 var(--brand-primary)' } : undefined}
            >
              <div className="flex items-baseline justify-between gap-2">
                <span className="truncate text-body font-medium text-text-primary">
                  {c.contact_name}
                </span>
                <span className="shrink-0 text-caption text-text-muted">
                  {formatChatStamp(c.last_activity_at)}
                </span>
              </div>
              <div className="mt-0.5 flex items-center justify-between gap-2">
                <span className="truncate text-caption text-text-secondary">
                  {c.last_buyer_line || truncateMiddle(c.identifier || `#${c.id}`, 40)}
                </span>
                {c.unread_count > 0 && (
                  <span className="flex h-[18px] min-w-[18px] shrink-0 items-center justify-center rounded-full px-1.5 text-micro font-semibold text-white"
                    style={{ background: 'var(--st-attention-dot)' }}>
                    {c.unread_count}
                  </span>
                )}
              </div>
            </button>
          </li>
        )
      })}
      {!rows.length && (
        <li className="p-4 text-body text-text-muted">
          No open conversations yet.
        </li>
      )}
    </ul>
  )
}

function ThreadPanel({ cid }: { cid: number }) {
  const thread = usePoll(() => glueApi.inboxMessages(cid), REFRESH_MS)
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)
  const [sendError, setSendError] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  const msgs = (thread.data?.messages ?? []).filter(
    (m) => !m.private && m.message_type !== 2,
  )

  useEffect(() => {
    bottomRef.current?.scrollIntoView()
  }, [msgs.length])

  async function send(e: FormEvent) {
    e.preventDefault()
    const content = draft.trim()
    if (!content || sending) return
    setSending(true)
    setSendError('')
    try {
      await glueApi.inboxReply(cid, content)
      setDraft('')
      await thread.refresh()
    } catch (err) {
      setSendError(err instanceof Error ? err.message : String(err))
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="flex min-h-0 flex-col rounded-lg border border-line bg-surface-card">
      <header className="flex shrink-0 items-center justify-between gap-3 border-b border-line px-4 py-3">
        <div className="min-w-0">
          <h2 className="truncate text-section font-semibold text-text-primary">
            {thread.data?.contact.name ?? `Conversation #${cid}`}
          </h2>
          <p className="mono truncate text-caption text-text-muted">
            {thread.data?.contact.identifier || ''}
          </p>
        </div>
        {thread.data?.status &&
          thread.data.status !== 'open' && (
            <StatusBadge tone={thread.data.status === 'resolved' ? 'success' : 'neutral'}
              label={thread.data.status} />
          )}
      </header>

      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-4">
        {thread.loading && !msgs.length && <SkeletonRows rows={4} height={44} />}
        {thread.error && (
          <p className="text-body text-[#B91C1C]">Thread unavailable ({thread.error})</p>
        )}
        {msgs.map((m) => (
          <Bubble key={m.id} m={m} botIds={thread.data?.bot_sender_ids ?? []}
            agents={thread.data?.agents ?? {}} />
        ))}
        <div ref={bottomRef} />
      </div>

      <form onSubmit={send} className="shrink-0 space-y-2 border-t border-line p-3">
        {sendError && (
          <p className="text-caption text-[#B91C1C]">Send failed — {sendError}</p>
        )}
        <div className="flex items-end gap-2">
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            rows={2}
            placeholder="Reply as yourself (human take-over) — sends over WhatsApp…"
            className="min-h-[44px] flex-1 resize-y rounded-md border border-line bg-surface-card p-2.5 text-body leading-snug outline-none transition-colors focus:border-brand focus:ring-2 focus:ring-brand/20"
          />
          <Button variant="primary" size="md" type="submit" loading={sending}
            disabled={!draft.trim()} aria-label="Send reply">
            <Send size={15} strokeWidth={1.75} />
            Send
          </Button>
        </div>
        <p className="text-micro text-text-muted">
          Public reply under your admin identity — evo delivers it to the buyer;
          the SLA beacon stops for this conversation once a human has replied.
        </p>
      </form>
    </div>
  )
}

function Bubble({
  m,
  botIds,
  agents,
}: {
  m: InboxMessage
  botIds: number[]
  agents: Record<string, string>
}) {
  const incoming = m.message_type === 0
  const isBot = !incoming && m.sender_id != null && botIds.includes(m.sender_id)
  const author = isBot
    ? 'AI assistant'
    : m.sender_name || (m.sender_id != null ? agents[String(m.sender_id)] : '')

  if (incoming) {
    return (
      <div className="flex flex-col items-start">
        <div className="max-w-[80%] whitespace-pre-wrap rounded-lg rounded-bl-sm border border-line bg-surface-subtle px-3.5 py-2.5 text-body leading-relaxed text-text-primary">
          {m.content}
        </div>
        <span className="mt-1 px-1 text-micro text-text-muted">{formatClock(m.created_at)}</span>
      </div>
    )
  }

  return (
    <div className="flex flex-col items-end">
      {isBot ? (
        <div
          className="max-w-[80%] rounded-lg rounded-br-sm border px-3.5 py-2.5"
          style={{ background: 'var(--ai-wash)', borderColor: 'var(--ai-dot)' }}
        >
          <p className="mb-1 flex items-center gap-1.5 text-micro font-medium"
            style={{ color: 'var(--ai-fg)' }}>
            <Bot size={12} strokeWidth={1.75} />
            AI assistant
          </p>
          <p className="whitespace-pre-wrap text-body leading-relaxed text-text-primary">
            {m.content}
          </p>
        </div>
      ) : (
        <div className="max-w-[80%] rounded-lg rounded-br-sm border border-line bg-surface-card px-3.5 py-2.5">
          {author && (
            <p className="mb-1 text-micro font-medium text-text-secondary">{author}</p>
          )}
          <p className="whitespace-pre-wrap text-body leading-relaxed text-text-primary">
            {m.content}
          </p>
        </div>
      )}
      <span className="mt-1 px-1 text-micro text-text-muted">{formatClock(m.created_at)}</span>
    </div>
  )
}
