import { apiFetch } from './client'

export interface QuoteRow {
  quote_id: string
  customer_id: string
  status: string
  total: number
  currency: string
  pdf_path?: string | null
  request_json?: unknown
  created_at: string
  updated_at: string
}

export interface QuoteDetail extends QuoteRow {
  request_json: Record<string, unknown>
  result_json: Record<string, unknown>
}

export interface PostRow {
  post_id: string
  sku: string
  platform: string
  caption: string
  hashtags: string
  status: string
  postiz_id?: string | null
  scheduled_at?: string | null
  created_at: string
  updated_at: string
}

export interface EventRow {
  id: number
  ts: string
  kind: string
  detail_json: string
}

export interface CustomerRow {
  customer_id: string
  wa_jid?: string | null
  email?: string | null
  name?: string | null
  country?: string | null
  language: string
  tier: string
  first_seen: string
}

export interface CatalogItem {
  sku: string
  name: string
  category?: string | null
}

export interface CatalogDetail extends CatalogItem {
  specs?: Record<string, string> | null
  moq?: number | null
  hs_code?: string | null
  certs?: string | null
  updated_at?: string
}

export interface CatalogItemIn {
  sku: string
  name: string
  category: string
  specs: Record<string, string>
  moq: number
  hs_code: string
  certs: string
}

interface ListResp<T> {
  items: T[]
}

export interface GapReport {
  imported: number
  skipped: { line: number; reason: string }[]
  gap_report: { sku: string; missing: string[] }[]
}

export const spine = {
  listQuotes: (params: { status?: string; older_than_hours?: number; limit?: number } = {}) => {
    const q = new URLSearchParams()
    if (params.status) q.set('status', params.status)
    if (params.older_than_hours) q.set('older_than_hours', String(params.older_than_hours))
    if (params.limit) q.set('limit', String(params.limit))
    return apiFetch<ListResp<QuoteRow>>(`/spine/quotes?${q}`)
  },
  getQuote: (qid: string) => apiFetch<QuoteDetail>(`/spine/quotes/${qid}`),
  listPosts: (status = '', limit = 200) =>
    apiFetch<ListResp<PostRow>>(
      `/spine/posts?limit=${limit}${status ? `&status=${status}` : ''}`,
    ),
  listEvents: (kind = '', limit = 50) =>
    apiFetch<ListResp<EventRow>>(`/spine/events?limit=${limit}${kind ? `&kind=${kind}` : ''}`),
  listCustomers: () => apiFetch<ListResp<CustomerRow>>('/spine/customers'),
  getCustomer: (cid: string) => apiFetch<CustomerRow>(`/spine/customers/${cid}`),
  updateCustomer: (cid: string, patch: Partial<Pick<CustomerRow, 'tier' | 'name' | 'country' | 'language' | 'email'>>) =>
    apiFetch<CustomerRow>(`/spine/customers/${cid}`, { method: 'PATCH', body: JSON.stringify(patch) }),
  listCatalog: (q = '') => apiFetch<ListResp<CatalogItem>>(`/spine/catalog?q=${encodeURIComponent(q)}`),
  getCatalogItem: (sku: string) => apiFetch<CatalogDetail>(`/spine/catalog/${encodeURIComponent(sku)}`),
  upsertCatalogItem: (item: CatalogItemIn) =>
    apiFetch<{ ok: boolean; sku: string; missing: string[] }>('/spine/catalog/item', {
      method: 'POST',
      body: JSON.stringify(item),
    }),
  deleteCatalogItem: (sku: string) =>
    apiFetch<{ ok: boolean; sku: string }>(`/spine/catalog/${encodeURIComponent(sku)}`, { method: 'DELETE' }),
  importCatalog: (csvText: string) =>
    apiFetch<GapReport>('/spine/catalog/import', { method: 'POST', body: csvText }),
  // ---- v1.2 threads (S4 conversation store; chatwoot replacement) ----
  listThreads: (status = 'open') =>
    apiFetch<ListResp<ThreadRow>>(`/spine/conversations?status=${status}&include_last=1`),
  getThread: (cid: number) => apiFetch<ThreadDetail>(`/spine/conversations/${cid}/messages`),
  setThreadStatus: (cid: number, status: 'open' | 'resolved') =>
    apiFetch<{ ok?: boolean; conversation_id: number; status: string }>(
      `/spine/conversations/${cid}/status`,
      { method: 'POST', body: JSON.stringify({ status }) },
    ),
}

export interface ThreadRow {
  id: number
  wa_jid: string
  contact_name?: string | null
  status: string
  escalation_tag?: string | null
  escalated_at?: string | null
  sla_beacon_at?: string | null
  updated_at: string
  last_in_at?: string | null
  last_human_out_at?: string | null
  preview?: string
}

export interface ThreadMsg {
  id: number
  direction: 'in' | 'out'
  sender_kind: 'buyer' | 'bot' | 'human' | 'system'
  body: string
  ts: string
}

export interface ThreadDetail {
  conversation: ThreadRow
  items: ThreadMsg[]
}
