import { useMemo, useState } from 'react'
import { Search } from 'lucide-react'
import { useSearchParams } from 'react-router-dom'
import { glueApi } from '../../api/glue'
import { spine } from '../../api/spine'
import type { CustomerRow } from '../../api/spine'
import { Button } from '../../components/ui/Button'
import { DataTable } from '../../components/ui/DataTable'
import type { Column } from '../../components/ui/DataTable'
import { GateBanner } from '../../components/ui/GateBanner'
import { KeyValue, SectionPanel } from '../../components/ui/SectionPanel'
import { StatusBadge } from '../../components/ui/StatusBadge'
import { TIER_TONE } from '../../lib/domain'
import { formatDate, truncateMiddle } from '../../lib/format'
import { useAsync } from '../../lib/useAsync'

const COLUMNS: Column<CustomerRow>[] = [
  {
    key: 'name',
    header: 'Customer',
    render: (r) => (
      <div>
        <p className="text-body font-medium">{r.name || '(unnamed)'}</p>
        {r.email && <p className="text-caption text-text-muted">{r.email}</p>}
      </div>
    ),
  },
  {
    key: 'wa_jid',
    header: 'WhatsApp JID',
    mono: true,
    width: 220,
    render: (r) => (r.wa_jid ? truncateMiddle(r.wa_jid, 30) : '—'),
  },
  { key: 'country', header: 'Country', width: 90 },
  {
    key: 'tier',
    header: 'Tier',
    width: 120,
    render: (r) => (
      <StatusBadge tone={TIER_TONE[r.tier] ?? 'neutral'} label={r.tier} />
    ),
  },
  { key: 'language', header: 'Lang', width: 70 },
  { key: 'first_seen', header: 'First seen', width: 100, render: (r) => formatDate(r.first_seen) },
]

export function CustomersPage() {
  const customers = useAsync(() => spine.listCustomers(), [])
  const rules = useAsync(() => glueApi.pricingRules(), [])
  const [q, setQ] = useState('')
  const [params, setParams] = useSearchParams()
  const activeId = params.get('c') ?? ''

  const rows = useMemo(() => {
    const items = customers.data?.items ?? []
    const needle = q.trim().toLowerCase()
    if (!needle) return items
    return items.filter((c) =>
      [c.name, c.email, c.wa_jid, c.country]
        .filter(Boolean)
        .some((f) => String(f).toLowerCase().includes(needle)),
    )
  }, [customers.data, q])

  const selected = rows.find((c) => c.customer_id === activeId)
  // S2 owns the FACTORS; the dropdown only ever offers tiers S2 can price
  const s2Tiers = rules.data?.rules.customer_tiers ?? []

  return (
    <div className="grid h-full grid-cols-1 items-start gap-4 overflow-y-auto lg:grid-cols-[55%_1fr]">
      <div className="space-y-3">
        <div className="relative max-w-sm">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search name, email, JID…"
            aria-label="Search customers"
            className="h-9 w-full rounded-md border border-line bg-surface-card pl-8 pr-3 text-body outline-none transition-colors focus:border-brand focus:ring-2 focus:ring-brand/20"
          />
        </div>
        <DataTable
          columns={COLUMNS}
          rows={rows}
          rowKey={(r) => r.customer_id}
          activeKey={activeId || undefined}
          onRowClick={(r) => setParams(r.customer_id === activeId ? {} : { c: r.customer_id })}
          loading={customers.loading}
          emptyMessage={
            q ? `No customer matches “${q}”.` : 'No customers yet — inbound messages create them.'
          }
        />
      </div>
      {selected ? (
        <CustomerDetail
          key={selected.customer_id}
          customer={selected}
          s2Tiers={s2Tiers.map((t) => t.name)}
          onSaved={() => customers.retry()}
        />
      ) : (
        <div className="hidden items-center justify-center rounded-lg border border-dashed border-line lg:flex lg:min-h-[300px]">
          <p className="text-body text-text-muted">Select a customer to view and edit.</p>
        </div>
      )}
    </div>
  )
}

function CustomerDetail({
  customer,
  s2Tiers,
  onSaved,
}: {
  customer: CustomerRow
  s2Tiers: string[]
  onSaved: () => void
}) {
  const [tier, setTier] = useState(customer.tier)
  const [name, setName] = useState(customer.name ?? '')
  const [country, setCountry] = useState(customer.country ?? '')
  const [language, setLanguage] = useState(customer.language ?? 'en')
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState<{ tone: 'success' | 'danger'; text: string } | null>(null)

  const dirty =
    tier !== customer.tier ||
    name !== (customer.name ?? '') ||
    country !== (customer.country ?? '') ||
    language !== (customer.language ?? '')

  async function save() {
    if (!dirty || saving) return
    setSaving(true)
    setMsg(null)
    try {
      await spine.updateCustomer(customer.customer_id, {
        ...(tier !== customer.tier ? { tier: tier.trim() } : {}),
        ...(name !== (customer.name ?? '') ? { name: name.trim() } : {}),
        ...(country !== (customer.country ?? '') ? { country: country.trim() } : {}),
        ...(language !== (customer.language ?? '') ? { language: language.trim() } : {}),
      })
      onSaved()
      setMsg({ tone: 'success', text: 'Saved. The next quote this buyer asks for uses these values.' })
    } catch (e) {
      setMsg({ tone: 'danger', text: e instanceof Error ? e.message : String(e) })
    } finally {
      setSaving(false)
    }
  }

  // a stored tier that S2 no longer knows must remain selectable so staff can see/fix it
  const options = s2Tiers.includes(customer.tier) ? s2Tiers : [customer.tier, ...s2Tiers]
  const unknownTier = !s2Tiers.includes(customer.tier)

  return (
    <div className="space-y-4">
      <SectionPanel title={customer.name || customer.customer_id} bodyClassName="p-4 space-y-3">
        <KeyValue
          rows={[
            ['ID', <span key="i" className="mono text-[13px]">{customer.customer_id}</span>],
            ['WhatsApp', <span key="w" className="mono text-[13px]">{customer.wa_jid || '—'}</span>],
            ['Email', customer.email || '—'],
            ['First seen', formatDate(customer.first_seen)],
          ]}
        />
        <p className="text-caption text-text-muted">
          The agent never assigns tiers — that is a commercial call made here by
          your team. Pricing always comes from S2's factor for whatever S3 says;
          a tier missing from S2 fails safe (the request escalates, never guesses).
        </p>
      </SectionPanel>

      <SectionPanel title="Edit" bodyClassName="p-4 space-y-3">
        {msg && <GateBanner tone={msg.tone === 'success' ? 'success' : 'danger'}
          title={msg.tone === 'success' ? 'Saved' : 'Save failed'} meta={msg.text} />}
        <label className="block">
          <span className="mb-1 flex items-center gap-2 text-caption uppercase tracking-wide text-text-secondary">
            Tier
            <StatusBadge tone={TIER_TONE[customer.tier] ?? 'neutral'} label={customer.tier} />
          </span>
          <select
            value={tier}
            onChange={(e) => setTier(e.target.value)}
            aria-label="Customer tier"
            className="h-9 w-full rounded-md border border-line bg-surface-card px-2 text-body outline-none transition-colors focus:border-brand focus:ring-2 focus:ring-brand/20"
          >
            {options.map((t) => (
              <option key={t} value={t}>
                {t}
                {!s2Tiers.includes(t) ? '  (not in pricing rules!)' : ''}
              </option>
            ))}
          </select>
          {unknownTier && (
            <span className="mt-1 block text-micro text-[#B91C1C]">
              This tier is not in S2 pricing rules — quotes for this customer will escalate until you add it.
            </span>
          )}
        </label>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <Field label="Name" value={name} onChange={setName} />
          <Field label="Country" value={country} onChange={setCountry} />
          <Field label="Language" value={language} onChange={setLanguage} />
        </div>
        <div className="flex justify-end">
          <Button variant="primary" size="sm" onClick={save} loading={saving} disabled={!dirty}>
            Save changes
          </Button>
        </div>
      </SectionPanel>

      <p className="text-caption text-text-muted">
        How pricing uses this: buyer messages in → spine resolves who they are (S3,
        including this tier) → calc multiplies the quote by S2's{' '}
        <span className="mono text-[13px]">price_factor</span> and applies that tier's payment terms.
        Tier changes land in the audit log (<span className="mono text-[13px]">tier_change</span> events).
      </p>
    </div>
  )
}

function Field({
  label, value, onChange,
}: {
  label: string
  value: string
  onChange: (v: string) => void
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-micro uppercase tracking-wide text-text-secondary">{label}</span>
      <input
        className="h-9 w-full rounded-md border border-line bg-surface-card px-2 text-body outline-none transition-colors focus:border-brand focus:ring-2 focus:ring-brand/20"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </label>
  )
}
