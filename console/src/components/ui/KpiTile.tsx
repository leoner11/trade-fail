interface Props {
  label: string
  value: string
  delta?: { text: string; tone: 'success' | 'danger' | 'neutral' }
}

export function KpiTile({ label, value, delta }: Props) {
  const deltaColor =
    delta?.tone === 'success'
      ? 'text-[#15803D]'
      : delta?.tone === 'danger'
        ? 'text-[#B91C1C]'
        : 'text-text-muted'
  return (
    <div className="rounded-lg border border-line bg-surface-card px-4 py-3">
      <p className="text-caption text-text-secondary">{label}</p>
      <p className="mt-1 text-data font-semibold tabular text-text-primary">{value}</p>
      {delta && <p className={`mt-0.5 text-caption ${deltaColor}`}>{delta.text}</p>}
    </div>
  )
}
