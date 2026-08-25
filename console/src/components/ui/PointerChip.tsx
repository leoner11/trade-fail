import { ExternalLink } from 'lucide-react'

type Health = 'up' | 'down' | 'unknown'

const HEALTH_COLOR: Record<Health, string> = {
  up: 'var(--st-success-dot)',
  down: 'var(--st-danger-dot)',
  unknown: 'var(--st-neutral-dot)',
}

interface Props {
  label: string
  href?: string
  health?: Health
  healthLabel?: string
}

export function PointerChip({ label, href, health = 'unknown', healthLabel }: Props) {
  const inner = (
    <>
      <span
        className="h-1.5 w-1.5 shrink-0 rounded-full"
        style={{ background: HEALTH_COLOR[health] }}
        aria-hidden
      />
      <span className="truncate">{label}</span>
      {healthLabel && <span className="shrink-0 text-text-muted">· {healthLabel}</span>}
      {href && <ExternalLink size={12} className="ml-auto shrink-0 text-text-muted" />}
    </>
  )
  const cls =
    'inline-flex max-w-full items-center gap-2 rounded-md border border-line bg-surface-card px-2.5 py-1.5 text-caption text-text-secondary'
  return href ? (
    <a href={href} target="_blank" rel="noreferrer" className={`${cls} hover:bg-surface-subtle`}>
      {inner}
    </a>
  ) : (
    <span className={cls}>{inner}</span>
  )
}
