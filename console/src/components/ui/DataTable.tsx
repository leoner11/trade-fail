import type { ReactNode } from 'react'
import { EmptyState } from './EmptyState'
import { SkeletonRows } from './Skeleton'

export interface Column<T> {
  key: string
  header: string
  align?: 'left' | 'right'
  width?: number | string
  mono?: boolean
  render?: (row: T) => ReactNode
}

interface Props<T> {
  columns: Column<T>[]
  rows: T[]
  rowKey: (row: T) => string
  loading?: boolean
  onRowClick?: (row: T) => void
  activeKey?: string
  emptyMessage?: string
  emptyAction?: ReactNode
}

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  loading = false,
  onRowClick,
  activeKey,
  emptyMessage = 'Nothing here yet.',
  emptyAction,
}: Props<T>) {
  return (
    <div className="overflow-auto rounded-lg border border-line bg-surface-card">
      <table className="w-full border-collapse">
        <thead className="sticky top-0 z-10">
          <tr>
            {columns.map((c) => (
              <th
                key={c.key}
                scope="col"
                style={{ width: c.width }}
                className={`border-b border-line bg-surface-subtle px-4 py-2.5 text-micro font-medium uppercase tracking-wide text-text-secondary ${
                  c.align === 'right' ? 'text-right' : 'text-left'
                }`}
              >
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        {!loading && (
          <tbody>
            {rows.map((row) => {
              const key = rowKey(row)
              const selected = key === activeKey
              return (
                <tr
                  key={key}
                  onClick={onRowClick ? () => onRowClick(row) : undefined}
                  className={`border-b border-line last:border-b-0 ${
                    onRowClick ? 'cursor-pointer' : ''
                  } hover:bg-surface-subtle`}
                  style={
                    selected
                      ? {
                          background: 'var(--brand-primary-wash)',
                          boxShadow: 'inset 2px 0 0 var(--brand-primary)',
                        }
                      : undefined
                  }
                >
                  {columns.map((c) => (
                    <td
                      key={c.key}
                      className={`px-4 py-3 text-body text-text-primary ${
                        c.align === 'right' ? 'text-right tabular' : 'text-left'
                      } ${c.mono ? 'mono text-[13px]' : ''}`}
                    >
                      {c.render ? c.render(row) : String((row as Record<string, unknown>)[c.key] ?? '—')}
                    </td>
                  ))}
                </tr>
              )
            })}
            {rows.length === 0 && (
              <tr>
                <td colSpan={columns.length}>
                  <EmptyState message={emptyMessage} action={emptyAction} />
                </td>
              </tr>
            )}
          </tbody>
        )}
      </table>
      {loading && <SkeletonRows rows={5} />}
    </div>
  )
}
