import { apiFetch, ApiError, getToken } from './client'

export interface WaStatus {
  state: string
  instance: string
  detail?: string
}

export interface WaQr {
  qr: string | null
  state?: string
  detail?: string
}

export interface OrganRow {
  name: string
  url: string
  up: boolean
}

export interface KbDoc {
  id: string
  name: string
  status: string
  enabled: boolean
}

export interface KbDocsResp {
  dataset: { id: string; name: string } | null
  items: KbDoc[]
  error?: string
}

export interface QuizResultRow {
  q: string
  answer: string
  hit: boolean
  fabricated: boolean
}

export interface QuizJob {
  kind: string
  status: 'running' | 'done'
  progress?: string
  passed?: number
  total?: number
  required?: number
  fabricated?: number
  gate_pass?: boolean
  results?: QuizResultRow[]
}

export interface GateLast {
  found: boolean
  ts?: string
  passed?: number
  total?: number
  required?: number
  fabricated?: number
  gate_pass?: boolean
}

// ---- social channels (postiz driven headlessly — trap #45) ----

export interface SocialChannel {
  id: string
  name: string
  platform: string
  disabled?: boolean | null
  picture?: string | null
}

export const glueApi = {
  socialPlatforms: () =>
    apiFetch<{ platforms: string[] }>('/glue/console/social/platforms'),
  socialChannels: () =>
    apiFetch<{ channels: SocialChannel[] }>('/glue/console/social/channels'),
  socialConnectUrl: (platform: string) =>
    apiFetch<{ url?: string; err?: string }>(
      `/glue/console/social/connect-url/${encodeURIComponent(platform)}`,
    ),
  socialFinish: (platform: string, params: Record<string, string>) =>
    apiFetch<{ ok: boolean }>(
      `/glue/console/social/finish/${encodeURIComponent(platform)}`,
      { method: 'POST', body: JSON.stringify(params) },
    ),
  socialDelete: (id: string) =>
    apiFetch<{ ok: boolean }>(`/glue/console/social/channels?id=${encodeURIComponent(id)}`, {
      method: 'DELETE',
    }),
  // draft editor (v1.5)
  socialAttachImage: async (pid: string, file: File): Promise<{ ok: boolean; index: number }> => {
    const res = await fetch(`/glue/console/social/draft/${encodeURIComponent(pid)}/image`, {
      method: 'POST',
      headers: { 'X-Filename': file.name, Authorization: `Bearer ${getToken()}` },
      body: file,
    })
    if (!res.ok) throw new ApiError(res.status, await res.text())
    return res.json()
  },
  socialRemoveImage: (pid: string, idx: number) =>
    apiFetch<{ ok: boolean; images: string[] }>(
      `/glue/console/social/draft/${encodeURIComponent(pid)}/image/${idx}`,
      { method: 'DELETE' },
    ),
  draftImageUrl: (pid: string, idx: number, ts: number) =>
    `/glue/console/social/draft/${encodeURIComponent(pid)}/image/${idx}?v=${ts}`,
  socialRegenerate: (pid: string, hint: string) =>
    apiFetch<{ ok: boolean; caption: string; hashtags: string }>(
      '/glue/console/social/regenerate',
      { method: 'POST', body: JSON.stringify({ post_id: pid, hint }) },
    ),

  waStatus: () => apiFetch<WaStatus>('/glue/console/wa/status'),
  waQr: () => apiFetch<WaQr>('/glue/console/wa/qr'),
  waLogout: () =>
    apiFetch<{ ok: boolean; detail: string }>('/glue/console/wa/logout', { method: 'POST' }),
  organs: () => apiFetch<{ items: OrganRow[] }>('/glue/console/organs'),

  kbDocs: () => apiFetch<KbDocsResp>('/glue/console/kb/docs'),
  kbUpload: async (file: File): Promise<{ ok: boolean; replaced: boolean }> => {
    const res = await fetch('/glue/console/kb/ingest', {
      method: 'POST',
      headers: { 'X-Filename': file.name, Authorization: `Bearer ${getToken()}` },
      body: await file.text(),
    })
    if (!res.ok) throw new ApiError(res.status, await res.text())
    return res.json()
  },
  kbWriteDoc: (name: string, text: string): Promise<{ ok: boolean; replaced: boolean }> => {
    const fname = name.toLowerCase().endsWith('.md') || name.toLowerCase().endsWith('.txt')
      ? name
      : `${name}.md`
    return apiFetch('/glue/console/kb/ingest', {
      method: 'POST',
      headers: { 'X-Filename': fname },
      body: text,
    })
  },
  kbDelete: (docId: string) =>
    apiFetch<{ ok: boolean }>(`/glue/console/kb/docs/${docId}`, { method: 'DELETE' }),

  quizStart: () =>
    apiFetch<{ job_id: string }>('/glue/console/gates/o2_quiz', { method: 'POST' }),
  quizJob: (jobId: string) => apiFetch<QuizJob>(`/glue/console/gates/o2_quiz/${jobId}`),
  gateLast: () => apiFetch<GateLast>('/glue/console/gates/last'),

  pricingRules: () =>
    apiFetch<{ path: string; currency: string; validity_days: number; rules: PricingRules }>(
      '/glue/console/pricing/rules',
    ),
  pricingSave: (rules: PricingRules) =>
    apiFetch<PricingSaveResult>('/glue/console/pricing/rules', {
      method: 'POST',
      body: JSON.stringify({ rules }),
    }),
  o3Backtest: (history: unknown[]) =>
    apiFetch<O3Result>('/glue/console/gates/o3_backtest', {
      method: 'POST',
      body: JSON.stringify({ history }),
    }),
  o3SelfTest: () => apiFetch<O3Result>('/glue/console/gates/o3_backtest', { method: 'POST' }),
  gatesSummary: () => apiFetch<GatesSummary>('/glue/console/gates/summary'),
  goLive: (manual: string[]) =>
    apiFetch<{ ok: boolean; blockers?: string[] }>('/glue/console/gates/go_live', {
      method: 'POST',
      body: JSON.stringify({ manual_confirmed: manual }),
    }),

  voiceSamples: () => apiFetch<{ text: string }>('/glue/console/voice/samples'),
  voiceSave: (text: string) =>
    apiFetch<{ ok: boolean }>('/glue/console/voice/samples', {
      method: 'POST',
      body: JSON.stringify({ text }),
    }),

  inboxConversations: () => apiFetch<InboxConversationsResp>('/glue/console/inbox/conversations'),
  inboxMessages: (cid: number | string) =>
    apiFetch<InboxThread>(`/glue/console/inbox/${cid}/messages`),
  inboxReply: (cid: number | string, content: string) =>
    apiFetch<{ ok: boolean; id: number }>(`/glue/console/inbox/${cid}/reply`, {
      method: 'POST',
      body: JSON.stringify({ content }),
    }),
  // v1.2 threads — spine store, take-over sends via evo directly
  threadsReply: (cid: number | string, content: string) =>
    apiFetch<{ ok: boolean; conversation_id: number; to: string }>(
      `/glue/console/threads/${cid}/reply`,
      { method: 'POST', body: JSON.stringify({ content }) },
    ),
}

export interface InboxConversation {
  id: number
  status: string
  contact_name: string
  identifier: string
  unread_count: number
  priority?: string | null
  created_at?: number | null
  last_activity_at?: number | null
  last_buyer_line: string
}

export interface InboxConversationsResp {
  items: InboxConversation[]
  total_unread: number
}

export interface InboxMessage {
  id: number
  content: string | null
  message_type: number // 0 buyer incoming / 1 agent-side outgoing / 2 activity
  private: boolean
  created_at?: number | null
  sender_type?: string | null
  sender_id?: number | null
  sender_name?: string
}

export interface InboxThread {
  conversation_id: number
  status: string
  contact: { name: string; identifier: string }
  bot_sender_ids: number[]
  agents: Record<string, string>
  messages: InboxMessage[]
}

export interface PricingMaterial {
  name: string
  base_price: number
  bulk_price: number
  note?: string
}

export interface PricingRules {
  currency: string
  validity_days: number
  material_base_prices: PricingMaterial[]
  size_coefficients: { size: string; coefficient: number; note?: string }[]
  process_fees: { name: string; fee: number; note?: string }[]
  quantity_discounts: { min_qty: number; discount_pct: number; label?: string }[]
  customer_tiers: { name: string; price_factor: number; payment_terms?: string }[]
  authority: { max_discount_pct: number; note?: string }
  price_visibility?: PriceVisibility
}

export interface PriceVisibility {
  default?: string
  per_material?: Record<string, string>
  _note?: string
}

export interface O3Result {
  mode: 'REAL' | 'EXAMPLE'
  source: string
  total: number
  match: number
  errors: number
  required: number
  min_quotes: number
  rate_pct: number
  note: string | null
  gate_pass: boolean
  results: { ref: string; got?: number; want?: number; delta_pct?: number; ok: boolean; error?: string }[]
}

export interface PricingSaveResult {
  ok: boolean
  unchanged?: boolean
  schema_version?: number
  path?: string
  backup?: string
  stage?: 'validate' | 'reload'
  problems?: string[]
  error?: string
  rolled_back?: boolean
}

export interface GatePart {
  found: boolean
  ts?: string
  gate_pass?: boolean
  mode?: 'REAL' | 'EXAMPLE'
  passed?: number
  total?: number
  fabricated?: number
}

export interface GatesSummary {
  o2: GatePart
  o3: GatePart
  go_live: GatePart & { go_live?: boolean }
  whatsapp: { found: boolean; state?: string }
  postiz_key_set: boolean
}
