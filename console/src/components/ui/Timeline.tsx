import type { Tone } from '../../lib/domain'
import { formatDateTime } from '../../lib/format'

const DOT: Record<Tone, string> = {
  neutral: 'var(--st-neutral-dot)',
  info: 'var(--st-info-dot)',
  attention: 'var(--st-attention-dot)',
  success: 'var(--st-success-dot)',
  danger: 'var(--st-danger-dot)',
  special: 'var(--st-special-dot)',
  ai: 'var(--ai-dot)',
}

export interface TimelineItem {
  id: string | number
  ts?: string | null
  title: string
  meta?: string
  tone: Tone
}

export function Timeline({ items, emptyMessage = 'No activity yet.' }: {
  items: TimelineItem[]
  emptyMessage?: string
}) {
  if (items.length === 0) {
    return <p className="py-8 text-center text-body text-text-muted">{emptyMessage}</p>
  }
  return (
    <ol className="flex flex-col">
      {items.map((it, i) => (
        <li key={it.id} className="relative flex gap-3 pb-5 last:pb-0">
          {i < items.length - 1 && (
            <span
              className="absolute left-[4.5px] top-4 bottom-0 w-px bg-line"
              aria-hidden
            />
          )}
          <span
            className="mt-1 h-2.5 w-2.5 shrink-0 rounded-full ring-2 ring-surface-card"
            style={{ background: DOT[it.tone] }}
            aria-hidden
          />
          <div className="min-w-0 flex-1">
            <div className="flex items-baseline justify-between gap-3">
              <p className="text-body font-medium text-text-primary">{it.title}</p>
              <span className="shrink-0 text-caption text-text-muted">{formatDateTime(it.ts)}</span>
            </div>
            {it.meta && <p className="mt-0.5 break-words text-caption text-text-secondary">{it.meta}</p>}
          </div>
        </li>
      ))}
    </ol>
  )
}
