const MONTHS = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
]

function parseTs(ts: string): Date {
  if (ts.endsWith('Z') || ts.includes('+')) return new Date(ts)
  return new Date(ts.replace(' ', 'T') + 'Z')
}

export function formatDateTime(ts?: string | null): string {
  if (!ts) return '—'
  const d = parseTs(ts)
  if (Number.isNaN(d.getTime())) return ts
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  return `${d.getDate()} ${MONTHS[d.getMonth()]} ${d.getFullYear()}, ${hh}:${mm}`
}

export function formatDate(ts?: string | null): string {
  if (!ts) return '—'
  const d = parseTs(ts)
  if (Number.isNaN(d.getTime())) return ts
  return `${d.getDate()} ${MONTHS[d.getMonth()]}`
}

export function formatMoney(amount?: number | null, currency = 'USD'): string {
  if (amount == null) return '—'
  const n = amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  return `${currency} ${n}`
}

export function truncateMiddle(s: string, max = 28): string {
  if (s.length <= max) return s
  const head = Math.ceil((max - 3) / 2)
  const tail = Math.floor((max - 3) / 2)
  return `${s.slice(0, head)}…${s.slice(-tail)}`
}

export function hoursAgo(ts?: string | null): number {
  if (!ts) return Infinity
  return (Date.now() - parseTs(ts).getTime()) / 3_600_000
}

export function formatClock(unixSecs?: number | null): string {
  if (!unixSecs) return ''
  const d = new Date(unixSecs * 1000)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

export function formatChatStamp(unixSecs?: number | null): string {
  // list rows: clock for today, short date otherwise
  if (!unixSecs) return ''
  const d = new Date(unixSecs * 1000)
  const now = new Date()
  if (d.toDateString() === now.toDateString()) return formatClock(unixSecs)
  return `${d.getDate()} ${MONTHS[d.getMonth()]}`
}

export function formatStamp(ts?: string | null): string {
  // spine "YYYY-MM-DD HH:MM:SS" (UTC) variant of the list-row stamp
  if (!ts) return ''
  const d = parseTs(ts)
  if (Number.isNaN(d.getTime())) return ts
  const now = new Date()
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  if (d.toDateString() === now.toDateString()) return `${hh}:${mm}`
  return `${d.getDate()} ${MONTHS[d.getMonth()]}, ${hh}:${mm}`
}
