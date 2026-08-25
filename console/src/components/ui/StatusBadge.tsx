import type { Tone } from '../../lib/domain'

const TONE_VAR: Record<Tone, { dot: string; wash: string; fg: string }> = {
  neutral: { dot: '--st-neutral-dot', wash: '--st-neutral-wash', fg: '--st-neutral-fg' },
  info: { dot: '--st-info-dot', wash: '--st-info-wash', fg: '--st-info-fg' },
  attention: { dot: '--st-attention-dot', wash: '--st-attention-wash', fg: '--st-attention-fg' },
  success: { dot: '--st-success-dot', wash: '--st-success-wash', fg: '--st-success-fg' },
  danger: { dot: '--st-danger-dot', wash: '--st-danger-wash', fg: '--st-danger-fg' },
  special: { dot: '--st-special-dot', wash: '--st-special-wash', fg: '--st-special-fg' },
  ai: { dot: '--ai-dot', wash: '--ai-wash', fg: '--ai-fg' },
}

export function StatusBadge({ tone, label }: { tone: Tone; label: string }) {
  const v = TONE_VAR[tone]
  return (
    <span
      className="inline-flex h-[22px] items-center gap-1.5 rounded px-2 text-micro font-medium"
      style={{ background: `var(${v.wash})`, color: `var(${v.fg})` }}
    >
      <span
        className="h-1.5 w-1.5 rounded-full"
        style={{ background: `var(${v.dot})` }}
        aria-hidden
      />
      {label}
    </span>
  )
}
