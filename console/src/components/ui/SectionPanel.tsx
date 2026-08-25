import type { ReactNode } from 'react'

interface Props {
  title: string
  action?: ReactNode
  children: ReactNode
  bodyClassName?: string
}

export function SectionPanel({ title, action, children, bodyClassName = 'p-4' }: Props) {
  return (
    <section className="rounded-lg border border-line bg-surface-card">
      <header className="flex items-center justify-between px-4 py-3">
        <h2 className="text-section font-semibold text-text-primary">{title}</h2>
        {action}
      </header>
      <div className={`border-t border-line ${bodyClassName}`}>{children}</div>
    </section>
  )
}

export function KeyValue({ rows }: { rows: [string, ReactNode][] }) {
  return (
    <dl className="grid grid-cols-[minmax(120px,auto)_1fr] gap-x-4 gap-y-2">
      {rows.map(([k, v]) => (
        <div key={k} className="col-span-2 grid grid-cols-subgrid items-baseline">
          <dt className="text-caption uppercase tracking-wide text-text-secondary">{k}</dt>
          <dd className="break-words text-body text-text-primary">{v}</dd>
        </div>
      ))}
    </dl>
  )
}
