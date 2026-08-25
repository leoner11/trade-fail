import { AlertTriangle, CheckCircle2, Info, XCircle } from 'lucide-react'
import type { ReactNode } from 'react'

type GateTone = 'success' | 'danger' | 'attention' | 'info'

const TONE: Record<
  GateTone,
  { wash: string; border: string; fg: string; icon: typeof Info }
> = {
  success: {
    wash: 'var(--st-success-wash)',
    border: 'rgba(34,197,94,0.3)',
    fg: 'var(--st-success-fg)',
    icon: CheckCircle2,
  },
  danger: {
    wash: 'var(--st-danger-wash)',
    border: 'rgba(239,68,68,0.3)',
    fg: 'var(--st-danger-fg)',
    icon: XCircle,
  },
  attention: {
    wash: 'var(--st-attention-wash)',
    border: 'rgba(245,158,11,0.3)',
    fg: 'var(--st-attention-fg)',
    icon: AlertTriangle,
  },
  info: {
    wash: 'var(--st-info-wash)',
    border: 'rgba(59,130,246,0.3)',
    fg: 'var(--st-info-fg)',
    icon: Info,
  },
}

interface Props {
  tone: GateTone
  title: string
  meta?: ReactNode
  actions?: ReactNode
}

export function GateBanner({ tone, title, meta, actions }: Props) {
  const t = TONE[tone]
  const Icon = t.icon
  return (
    <div
      className="flex items-center gap-3 rounded-lg px-4 py-3"
      style={{ background: t.wash, border: `1px solid ${t.border}` }}
      role="status"
    >
      <Icon size={16} style={{ color: t.fg }} className="shrink-0" />
      <div className="min-w-0 flex-1">
        <p className="text-card font-semibold text-text-primary">{title}</p>
        {meta && <p className="mt-0.5 text-caption text-text-secondary">{meta}</p>}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  )
}
