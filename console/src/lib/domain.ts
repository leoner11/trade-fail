export type Tone = 'neutral' | 'info' | 'attention' | 'success' | 'danger' | 'special' | 'ai'

export type QuoteStatus = 'draft' | 'sent' | 'viewed' | 'accepted' | 'rejected' | 'negotiating'
export type PostStatus = 'pending' | 'approved' | 'rejected' | 'scheduled' | 'posted'
export type WaState = 'open' | 'close' | 'connecting' | 'absent'

export const QUOTE_TONE: Record<QuoteStatus, Tone> = {
  draft: 'neutral',
  sent: 'info',
  viewed: 'attention',
  accepted: 'success',
  rejected: 'danger',
  negotiating: 'attention',
}

export const POST_TONE: Record<PostStatus, Tone> = {
  pending: 'attention',
  approved: 'success',
  rejected: 'danger',
  scheduled: 'info',
  posted: 'success',
}

export const WA_TONE: Record<WaState, Tone> = {
  open: 'success',
  close: 'attention',
  connecting: 'info',
  absent: 'danger',
}

export const TIER_TONE: Record<string, Tone> = {
  new: 'neutral',
  repeat: 'info',
  distributor: 'special',
}

export type POStatus =
  | 'draft'
  | 'approved'
  | 'sent'
  | 'confirmed'
  | 'shipped'
  | 'received'
  | 'cancelled'

export const PO_TONE: Record<POStatus, Tone> = {
  draft: 'neutral',
  approved: 'info',
  sent: 'info',
  confirmed: 'special',
  shipped: 'special',
  received: 'success',
  cancelled: 'danger',
}

export const INTEL_TONE: Record<string, Tone> = {
  news: 'neutral',
  tariff: 'attention',
  price_watch: 'special',
}

export const CATALOG_TONE: Record<string, Tone> = {
  proposed: 'attention',
  live: 'success',
}

export const GATE_LABELS: Record<string, string> = {
  escalation: 'Escalation',
  sla_beacon: 'SLA beacon',
  postiz_push_skipped: 'Postiz push skipped',
  followup_draft: 'Follow-up drafted',
  followup_sent: 'Follow-up sent',
}

export function internalMaterials(rules?: { price_visibility?: { default?: string; per_material?: Record<string, string> } } | null): Set<string> {
  const per = rules?.price_visibility?.per_material ?? {}
  return new Set(
    Object.entries(per)
      .filter(([, v]) => v === 'internal_only')
      .map(([k]) => k),
  )
}
