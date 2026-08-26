import { Bot, CheckCheck, Send } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { useSearchParams } from 'react-router-dom'
import { glueApi } from '../../api/glue'
import { spine } from '../../api/spine'
import type { ThreadMsg, ThreadRow } from '../../api/spine'
import { Button } from '../../components/ui/Button'
import { ConfirmDialog } from '../../components/ui/ConfirmDialog'
import { SkeletonRows } from '../../components/ui/Skeleton'
import { StatusBadge } from '../../components/ui/StatusBadge'
import { formatStamp, truncateMiddle } from '../../lib/format'
import { usePoll } from '../../lib/usePoll'

const REFRESH_MS = 5000

export function ThreadsPage() {
  const [params, setParams] = useSearchParams()
  const activeId = params.get('c') ?? ''
  const threads = usePoll(() => spine.listThreads('open'), REFRESH_MS)

  const rows = threads.data?.items ?? []
  const selected = rows.find((c) => String(c.id) === activeId)

  return (
    <div className="grid h-full min-h-0 grid-cols-1 gap-4 lg:grid-cols-[45%_1fr]">
      <div className="min-h-0 overflow-y-auto rounded-lg border border-line bg-surface-card">
        <ConversationList
          rows={rows}
          loading={threads.loading}
          error={threads.error}
          activeId={activeId}
          onSelect={(c) => setParams(c ? { c: String(c.id) } : {})}
        />
      </div>
      {selected ? (
        <ThreadPanel key={selected.id} row={selected} />
      ) : (
        <div className="hidden items-center justify-center rounded-lg border border-dashed border-line lg:flex">
          <p className="text-body text-text-muted">
            Select a thread — every buyer chat lands here (spine store).
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
  rows: ThreadRow[]
  loading: boolean
  error: string | null
  activeId: string
  onSelect: (c?: ThreadRow) => void
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
        Threads unavailable — is the store on :8101? ({error})
      </p>
    )
  return (
    <ul className="divide-y divide-line">
      {rows.map((c) => {
        const active = String(c.id) === activeId
        const stamp = formatStamp(c.last_in_at || c.updated_at)
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
                <span className="flex min-w-0 items-center gap-2">
                  <span className="truncate text-body font-medium text-text-primary">
                    {c.contact_name || truncateMiddle(c.wa_jid, 28)}
                  </span>
                  {c.escalation_tag && (
                    <StatusBadge tone="attention" label={c.escalation_tag} />
                  )}
                </span>
                <span className="shrink-0 text-caption text-text-muted">{stamp}</span>
              </div>
              <div className="mt-0.5 flex items-center justify-between gap-2">
                <span className="truncate text-caption text-text-secondary">
                  {c.preview || truncateMiddle(c.wa_jid, 40)}
                </span>
              </div>
            </button>
          </li>
        )
      })}
      {!rows.length && (
        <li className="p-4 text-body text-text-muted">No open conversations yet.</li>
      )}
    </ul>
  )
}

function ThreadPanel({ row }: { row: ThreadRow }) {
  const cid = row.id
  const thread = usePoll(() => spine.getThread(cid), REFRESH_MS)
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)
  const [sendError, setSendError] = useState('')
  const [confirmResolve, setConfirmResolve] = useState(false)
  const [resolving, setResolving] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  const msgs = thread.data?.items ?? []

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
      await glueApi.threadsReply(cid, content)
      setDraft('')
      await thread.refresh()
    } catch (err) {
      setSendError(err instanceof Error ? err.message : String(err))
    } finally {
      setSending(false)
    }
  }

  async function resolve() {
    setResolving(true)
    try {
      await spine.setThreadStatus(cid, 'resolved')
      setConfirmResolve(false)
      await thread.refresh()
    } catch (err) {
      setSendError(err instanceof Error ? err.message : String(err))
      setConfirmResolve(false)
    } finally {
      setResolving(false)
    }
  }

  return (
    <div className="flex min-h-0 flex-col rounded-lg border border-line bg-surface-card">
      <header className="flex shrink-0 items-center justify-between gap-3 border-b border-line px-4 py-3">
        <div className="min-w-0">
          <h2 className="truncate text-section font-semibold text-text-primary">
            {row.contact_name || `Conversation #${cid}`}
          </h2>
          <p className="mono truncate text-caption text-text-muted">{row.wa_jid}</p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {row.escalation_tag && (
            <StatusBadge tone="attention" label={`${row.escalation_tag} pending`} />
          )}
          <Button variant="ghost" size="sm" onClick={() => setConfirmResolve(true)}>
            <CheckCheck size={15} strokeWidth={1.75} />
            Resolve
          </Button>
        </div>
      </header>

      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-4">
        {thread.loading && !msgs.length && <SkeletonRows rows={4} height={44} />}
        {thread.error && (
          <p className="text-body text-[#B91C1C]">Thread unavailable ({thread.error})</p>
        )}
        {msgs.map((m) => (
          <Bubble key={m.id} m={m} />
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
          Sent to the buyer over WhatsApp via evo; your reply clears any pending
          escalation and stops the SLA beacon for this conversation.
        </p>
      </form>

      <ConfirmDialog
        open={confirmResolve}
        title="Resolve this conversation?"
        body={`Marks thread #${cid} as resolved and clears its escalation flag. It reopens automatically if ${row.contact_name || 'the buyer'} writes again.`}
        confirmLabel="Resolve"
        busy={resolving}
        onCancel={() => setConfirmResolve(false)}
        onConfirm={resolve}
      />
    </div>
  )
}

function Bubble({ m }: { m: ThreadMsg }) {
  if (m.sender_kind === 'system') {
    return (
      <div className="flex justify-center">
        <p className="max-w-[85%] whitespace-pre-wrap rounded-md bg-surface-subtle px-3 py-1.5 text-center text-micro leading-relaxed text-text-muted">
          {m.body}
        </p>
      </div>
    )
  }

  if (m.direction === 'in') {
    return (
      <div className="flex flex-col items-start">
        <div className="max-w-[80%] whitespace-pre-wrap rounded-lg rounded-bl-sm border border-line bg-surface-subtle px-3.5 py-2.5 text-body leading-relaxed text-text-primary">
          {m.body}
        </div>
        <span className="mt-1 px-1 text-micro text-text-muted">{formatStamp(m.ts)}</span>
      </div>
    )
  }

  if (m.sender_kind === 'bot') {
    return (
      <div className="flex flex-col items-end">
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
            {m.body}
          </p>
        </div>
        <span className="mt-1 px-1 text-micro text-text-muted">{formatStamp(m.ts)}</span>
      </div>
    )
  }

  return (
    <div className="flex flex-col items-end">
      <div className="max-w-[80%] rounded-lg rounded-br-sm border border-line bg-surface-card px-3.5 py-2.5">
        <p className="mb-1 text-micro font-medium text-text-secondary">You</p>
        <p className="whitespace-pre-wrap text-body leading-relaxed text-text-primary">
          {m.body}
        </p>
      </div>
      <span className="mt-1 px-1 text-micro text-text-muted">{formatStamp(m.ts)}</span>
    </div>
  )
}
