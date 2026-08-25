import type { ReactNode } from 'react'

export function EmptyState({
  message,
  action,
}: {
  message: string
  action?: ReactNode
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-12">
      <p className="text-body text-text-muted">{message}</p>
      {action}
    </div>
  )
}
