import { useEffect } from 'react'
import type { ReactNode } from 'react'
import { Button } from './Button'

interface Props {
  open: boolean
  title: string
  body: ReactNode
  confirmLabel?: string
  busy?: boolean
  onCancel: () => void
  onConfirm: () => void
}

export function ConfirmDialog({
  open,
  title,
  body,
  confirmLabel = 'Confirm',
  busy = false,
  onCancel,
  onConfirm,
}: Props) {
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onCancel()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onCancel])

  if (!open) return null
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-6"
      style={{ background: 'rgba(17,24,39,0.45)' }}
      onClick={onCancel}
      role="presentation"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="w-full max-w-md rounded-[10px] bg-surface-card shadow-[0_12px_32px_rgba(17,24,39,0.16)]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-4">
          <h2 className="text-section font-semibold">{title}</h2>
          <div className="mt-1.5 text-body text-text-secondary">{body}</div>
        </div>
        <div className="flex justify-end gap-2 border-t border-line p-4">
          <Button variant="secondary" onClick={onCancel} autoFocus disabled={busy}>
            Cancel
          </Button>
          <Button variant="danger" onClick={onConfirm} loading={busy}>
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  )
}
