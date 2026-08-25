interface SkeletonProps {
  rows?: number
  height?: number
  className?: string
}

export function SkeletonRows({ rows = 5, height = 48, className = '' }: SkeletonProps) {
  return (
    <div className={`animate-pulse ${className}`} aria-hidden>
      {Array.from({ length: rows }, (_, i) => (
        <div
          key={i}
          className="border-b border-line bg-surface-subtle/60"
          style={{ height }}
        />
      ))}
    </div>
  )
}

export function SkeletonBlock({ height = 96, className = '' }: { height?: number; className?: string }) {
  return (
    <div
      className={`animate-pulse rounded-lg bg-surface-subtle ${className}`}
      style={{ height }}
      aria-hidden
    />
  )
}

export function Spinner({ size = 16 }: { size?: number }) {
  return (
    <span
      className="inline-block animate-spin rounded-full border-2 border-line-strong border-t-brand"
      style={{ width: size, height: size }}
      role="status"
      aria-label="Loading"
    />
  )
}
