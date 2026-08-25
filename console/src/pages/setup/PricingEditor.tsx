import { AlertTriangle, Eye, EyeOff, Plus, RotateCcw, Save, Trash2, X } from 'lucide-react'
import { useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { glueApi } from '../../api/glue'
import type { PricingRules } from '../../api/glue'
import { Button } from '../../components/ui/Button'
import { GateBanner } from '../../components/ui/GateBanner'

type ErrKey = string

interface FeeDraft { key: number; name: string; fee: string }
interface SizeDraft { key: number; size: string; coef: string; locked: boolean }

interface Draft {
  currency: string
  validity_days: string
  authority_cap: string
  materials: { name: string; base: string; bulk: string; internal: boolean; note?: string }[]
  sizes: SizeDraft[]
  fees: FeeDraft[]
  ladder: { min_qty: string; discount_pct: string; label?: string }[]
  tiers: { name: string; factor: string; terms?: string }[]
}

const NUM_RE = /^\d*\.?\d*$/
const CUR_RE = /^[A-Z]{3}$/

let uid = 1
const nextKey = () => uid++

function toDraft(r: PricingRules): Draft {
  const per = r.price_visibility?.per_material ?? {}
  return {
    currency: String(r.currency ?? 'USD'),
    validity_days: String(r.validity_days),
    authority_cap: String(r.authority.max_discount_pct),
    materials: r.material_base_prices.map((m) => ({
      name: m.name, base: String(m.base_price), bulk: String(m.bulk_price),
      internal: per[m.name] === 'internal_only', note: m.note,
    })),
    sizes: r.size_coefficients.map((s) => ({
      key: nextKey(), size: s.size, coef: String(s.coefficient), locked: !s.coefficient,
    })),
    fees: r.process_fees.map((f) => ({ key: nextKey(), name: f.name, fee: String(f.fee) })),
    ladder: r.quantity_discounts.map((q) => ({
      min_qty: String(q.min_qty), discount_pct: String(q.discount_pct), label: q.label,
    })),
    tiers: r.customer_tiers.map((t) => ({
      name: t.name, factor: String(t.price_factor), terms: t.payment_terms,
    })),
  }
}

function num(v: string): number | null {
  if (v === '' || !NUM_RE.test(v)) return null
  const n = Number(v)
  return Number.isFinite(n) ? n : null
}

function validate(d: Draft): Map<ErrKey, string> {
  const errs = new Map<ErrKey, string>()
  const put = (k: ErrKey, msg: string) => { if (!errs.has(k)) errs.set(k, msg) }

  if (!CUR_RE.test(d.currency.trim().toUpperCase()))
    put('currency', '3-letter ISO code (USD, EUR, CNY…)')
  const vd = num(d.validity_days)
  if (vd == null || vd < 1 || vd !== Math.trunc(vd))
    put('validity', 'whole days ≥ 1')
  const cap = num(d.authority_cap)
  if (cap == null || cap < 0 || cap > 100) put('cap', '0–100')

  d.materials.forEach((m, i) => {
    if (num(m.base) == null || num(m.base)! <= 0) put(`mb.${i}.base`, '> 0')
    if (num(m.bulk) == null || num(m.bulk)! <= 0) put(`mb.${i}.bulk`, '> 0')
  })

  const sizeNames = new Map<string, number>()
  d.sizes.forEach((s, i) => {
    const n = s.size.trim()
    if (!n) put(`sz.${i}.name`, 'required')
    else if (sizeNames.has(n.toLowerCase()))
      put(`sz.${i}.name`, `duplicate of row ${sizeNames.get(n.toLowerCase())! + 1}`)
    else sizeNames.set(n.toLowerCase(), i)
    if (!s.locked) {
      const c = num(s.coef)
      if (c == null || c < 0) put(`sz.${i}.coef`, '≥ 0 (0 = manual quote)')
    }
  })
  if (d.sizes.length === 0) put('sizes.empty', 'at least one size must remain')

  const feeNames = new Map<string, number>()
  d.fees.forEach((f, i) => {
    const n = f.name.trim()
    if (!n) put(`fee.${i}.name`, 'required')
    else if (feeNames.has(n.toLowerCase()))
      put(`fee.${i}.name`, `duplicate of row ${feeNames.get(n.toLowerCase())! + 1}`)
    else feeNames.set(n.toLowerCase(), i)
    if (num(f.fee) == null || num(f.fee)! <= 0) put(`fee.${i}.val`, '> 0')
  })

  let prev = 0
  d.ladder.forEach((q, i) => {
    const mq = num(q.min_qty)
    if (mq == null || mq <= 0 || mq !== Math.trunc(mq)) put(`lq.${i}`, 'positive integer')
    else if (mq <= prev && i > 0) put(`lq.${i}`, 'must increase')
    else prev = mq
    const dp = num(q.discount_pct)
    if (dp == null || dp < 0 || dp >= 100) put(`ld.${i}`, '0–99.99')
  })
  d.tiers.forEach((t, i) => {
    const f = num(t.factor)
    if (f == null || f <= 0) put(`tf.${i}`, '> 0')
  })
  return errs
}

type DiffKind = 'change' | 'add' | 'remove'

interface DiffLine { kind: DiffKind; path: string; from?: string; to?: string }

function diff(d: Draft, orig: PricingRules): DiffLine[] {
  const out: DiffLine[] = []
  const push = (path: string, a: unknown, b: string) => {
    if (String(a) !== b) out.push({ kind: 'change', path, from: String(a), to: b })
  }
  const wasInternal = (name: string) =>
    orig.price_visibility?.per_material?.[name] === 'internal_only'

  push('currency', orig.currency, d.currency.trim().toUpperCase())
  push('validity_days', orig.validity_days, d.validity_days)
  push('authority.max_discount_pct', orig.authority.max_discount_pct, d.authority_cap)

  d.materials.forEach((m, i) => {
    const o = orig.material_base_prices[i]
    if (!o || o.name !== m.name) return
    push(`${m.name}.base_price`, o.base_price, m.base)
    push(`${m.name}.bulk_price`, o.bulk_price, m.bulk)
    push(`${m.name}.visibility`, wasInternal(m.name) ? 'internal_only' : 'public',
      m.internal ? 'internal_only' : 'public')
  })

  // fees & sizes are keyed by name so adds/removes diff semantically
  const oldFees = new Map(orig.process_fees.map((f) => [f.name.toLowerCase(), f]))
  const seenFees = new Set<string>()
  d.fees.forEach((f) => {
    const n = f.name.trim()
    if (!n) return
    const low = n.toLowerCase()
    seenFees.add(low)
    const o = oldFees.get(low)
    if (!o) out.push({ kind: 'add', path: `process ${n}`, to: `${f.fee} ${d.currency}` })
    else push(`${o.name}.fee`, o.fee, f.fee)
  })
  orig.process_fees.forEach((o) => {
    if (!seenFees.has(o.name.toLowerCase()))
      out.push({ kind: 'remove', path: `process ${o.name}`, from: `${o.fee} ${orig.currency}` })
  })

  const oldSizes = new Map(orig.size_coefficients.map((s) => [s.size.toLowerCase(), s]))
  const seenSizes = new Set<string>()
  d.sizes.forEach((s) => {
    const n = s.size.trim()
    if (!n) return
    const low = n.toLowerCase()
    seenSizes.add(low)
    const o = oldSizes.get(low)
    if (!o) out.push({ kind: 'add', path: `size ${n}`, to: `×${s.coef}` })
    else if (!s.locked) push(`size ${o.size}.coefficient`, o.coefficient, s.coef)
  })
  orig.size_coefficients.forEach((o) => {
    if (!seenSizes.has(o.size.toLowerCase()))
      out.push({ kind: 'remove', path: `size ${o.size}`, from: `×${o.coefficient}` })
  })

  d.ladder.forEach((q, i) => {
    const o = orig.quantity_discounts[i]
    if (!o) return
    push(`tier[${i}].min_qty`, o.min_qty, q.min_qty)
    push(`tier[${i}].discount_pct`, o.discount_pct, q.discount_pct)
  })
  d.tiers.forEach((t, i) => {
    const o = orig.customer_tiers[i]
    if (!o || o.name !== t.name) return
    push(`tier ${t.name}.price_factor`, o.price_factor, t.factor)
  })
  return out
}

export function PricingEditor({
  initial,
  onClose,
}: {
  initial: { path: string; currency: string; rules: PricingRules }
  onClose: () => void
}) {
  const [draft, setDraft] = useState<Draft>(() => toDraft(initial.rules))
  const [saving, setSaving] = useState(false)
  const [problems, setProblems] = useState<string[]>([])
  const [saveError, setSaveError] = useState('')
  const [showDiff, setShowDiff] = useState(false)

  const errors = useMemo(() => validate(draft), [draft])
  const changes = useMemo(() => diff(draft, initial.rules), [draft, initial.rules])
  const dirty = changes.length > 0
  const canSave = dirty && errors.size === 0 && !saving

  function upd(fn: (d: Draft) => void) {
    setDraft((prev) => {
      const next = structuredClone(prev)
      fn(next)
      return next
    })
  }

  async function save() {
    if (!canSave) return
    setSaving(true)
    setProblems([])
    setSaveError('')
    try {
      const rules: PricingRules = structuredClone(initial.rules)
      rules.currency = draft.currency.trim().toUpperCase()
      rules.validity_days = num(draft.validity_days)!
      rules.authority.max_discount_pct = num(draft.authority_cap)!
      const perMaterial: Record<string, string> = {}
      draft.materials.forEach((m, i) => {
        rules.material_base_prices[i].base_price = num(m.base)!
        rules.material_base_prices[i].bulk_price = num(m.bulk)!
        if (m.internal) perMaterial[m.name] = 'internal_only'
      })
      rules.price_visibility = {
        default: 'public',
        ...(Object.keys(perMaterial).length ? { per_material: perMaterial } : {}),
        _note:
          'internal_only materials NEVER enter inline quoting — glue routes them straight to a human quote (B5). The agent cannot leak a number it was never given.',
      }
      rules.size_coefficients = draft.sizes
        .filter((s) => s.size.trim())
        .map((s) => ({
          size: s.size.trim(),
          coefficient: s.locked ? 0 : num(s.coef)!,
          note: initial.rules.size_coefficients.find(
            (o) => o.size.toLowerCase() === s.size.trim().toLowerCase(),
          )?.note,
        }))
      rules.process_fees = draft.fees
        .filter((f) => f.name.trim())
        .map((f) => ({
          name: f.name.trim(),
          fee: num(f.fee)!,
          note: initial.rules.process_fees.find(
            (o) => o.name.toLowerCase() === f.name.trim().toLowerCase(),
          )?.note,
        }))
      draft.ladder.forEach((q, i) => {
        rules.quantity_discounts[i].min_qty = num(q.min_qty)!
        rules.quantity_discounts[i].discount_pct = num(q.discount_pct)!
      })
      draft.tiers.forEach((t, i) => {
        rules.customer_tiers[i].price_factor = num(t.factor)!
      })
      await glueApi.pricingSave(rules)
      onClose()
    } catch (e) {
      const raw = e instanceof Error ? e.message : String(e)
      try {
        const parsed = JSON.parse(raw.slice(raw.indexOf(': ') + 1))
        if (parsed.stage === 'validate' && Array.isArray(parsed.problems)) {
          setProblems(parsed.problems)
          setSaveError('Server rejected the edit — nothing was changed.')
        } else if (parsed.stage === 'reload') {
          setSaveError(
            `Reload failed and the previous rules were restored (${parsed.error}). ` +
              'calc kept serving the last good prices throughout.',
          )
        } else {
          setSaveError(raw)
        }
      } catch {
        setSaveError(raw)
      }
    } finally {
      setSaving(false)
    }
  }

  const errCls = (k: ErrKey) =>
    errors.has(k)
      ? 'border-[#DC2626] bg-[#FEF2F2] focus:border-[#DC2626] focus:ring-[#DC2626]/20'
      : 'border-line bg-surface-card focus:border-brand focus:ring-brand/20'
  const txtCls =
    'h-8 rounded-md border px-2 text-body outline-none transition-colors focus:ring-2'

  function delFee(key: number) { upd((d) => { d.fees = d.fees.filter((f) => f.key !== key) }) }
  function delSize(key: number) { upd((d) => { d.sizes = d.sizes.filter((s) => s.key !== key) }) }

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-lg border border-line bg-surface-base">
      <header className="flex shrink-0 items-center justify-between border-b border-line bg-surface-card px-5 py-3">
        <div>
          <h2 className="text-page font-semibold text-text-primary">Edit pricing rules</h2>
          <p className="mono text-caption text-text-muted">{initial.path}</p>
        </div>
        <Button variant="secondary" size="sm" onClick={onClose}
          aria-label="Close editor" title="Close without saving">
          <X size={14} strokeWidth={1.75} />
          Close
        </Button>
      </header>

      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-5">
        {saveError && <GateBanner tone="danger" title="Save failed" meta={saveError} />}
        {problems.length > 0 && (
          <div className="rounded-md border border-[#DC2626]/30 bg-[#FEF2F2] p-3">
            <p className="text-caption font-medium text-[#B91C1C]">
              calc's validation says:
            </p>
            <ul className="mt-1 list-disc pl-5 text-caption text-[#B91C1C]">
              {problems.map((p) => <li key={p}>{p}</li>)}
            </ul>
          </div>
        )}

        <section className="grid grid-cols-1 gap-4 md:grid-cols-4">
          <label className="block">
            <span className="mb-1 block text-caption uppercase tracking-wide text-text-secondary">Currency (ISO)</span>
            <input
              className={`${txtCls} w-full ${errCls('currency')}`}
              value={draft.currency}
              aria-label="Currency"
              onChange={(e) => upd((dr) => { dr.currency = e.target.value.toUpperCase().slice(0, 3) })}
            />
            {(errors.get('currency')) && (
              <span className="mt-0.5 block text-micro text-[#B91C1C]">{errors.get('currency')}</span>
            )}
          </label>
          <NumField label="Quote validity (days)" error={errors.get('validity')}
            value={draft.validity_days}
            onChange={(v) => upd((d) => { d.validity_days = v })}
            cls={errCls('validity')} />
          <NumField label="Authority cap (%)" error={errors.get('cap')}
            value={draft.authority_cap}
            onChange={(v) => upd((d) => { d.authority_cap = v })}
            cls={errCls('cap')}
            hint="beyond this the agent must ask the boss" />
          <div className="flex items-end pb-1">
            <p className="text-caption text-text-muted">
              Changing currency re-labels every price calc emits — existing saved
              quotes keep their original currency. calc re-validates on save.
            </p>
          </div>
        </section>

        <EditorTable title="Base & bulk prices" head={['Model', `Base (${draft.currency || 'CUR'})`, `Bulk (${draft.currency || 'CUR'})`, 'Visibility', 'Note']}>
          {draft.materials.map((m, i) => (
            <tr key={m.name}>
              <td className="mono px-3 py-2 text-[13px] font-medium">{m.name}</td>
              <td className="px-3 py-2 text-right">
                <input className={`${txtCls} w-32 text-right ${errCls(`mb.${i}.base`)}`}
                  inputMode="decimal" value={m.base} aria-label={`${m.name} base price`}
                  onChange={(e) => { if (NUM_RE.test(e.target.value)) upd((d) => { d.materials[i].base = e.target.value }) }} />
                {errors.get(`mb.${i}.base`) && <ErrTag k={`mb.${i}.base`} errs={errors} />}
              </td>
              <td className="px-3 py-2 text-right">
                <input className={`${txtCls} w-32 text-right ${errCls(`mb.${i}.bulk`)}`}
                  inputMode="decimal" value={m.bulk} aria-label={`${m.name} bulk price`}
                  onChange={(e) => { if (NUM_RE.test(e.target.value)) upd((d) => { d.materials[i].bulk = e.target.value }) }} />
                {errors.get(`mb.${i}.bulk`) && <ErrTag k={`mb.${i}.bulk`} errs={errors} />}
              </td>
              <td className="px-3 py-2">
                <button
                  type="button"
                  onClick={() => upd((d) => { d.materials[i].internal = !d.materials[i].internal })}
                  role="switch"
                  aria-checked={m.internal}
                  aria-label={`${m.name} price visibility`}
                  className={`inline-flex h-7 items-center gap-1.5 rounded-md border px-2 text-micro font-medium transition-colors duration-150 ${
                    m.internal
                      ? 'border-transparent text-white'
                      : 'border-line bg-surface-card text-text-secondary hover:bg-surface-subtle'
                  }`}
                  style={m.internal ? { background: 'var(--ai-fg)' } : undefined}
                  title={
                    m.internal
                      ? 'internal_only — buyers are never given numbers; asks route to a human quote'
                      : 'public — the agent may quote this material inline'
                  }>
                  {m.internal ? (
                    <>
                      <EyeOff size={12} strokeWidth={1.75} /> internal
                    </>
                  ) : (
                    <>
                      <Eye size={12} strokeWidth={1.75} /> public
                    </>
                  )}
                </button>
              </td>
              <td className="px-3 py-2 text-caption text-text-secondary">{m.note}</td>
            </tr>
          ))}
        </EditorTable>

        <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
          <EditorTable title="Quantity ladder" head={['From qty', 'Discount %', 'Label']}>
            {draft.ladder.map((q, i) => (
              <tr key={i}>
                <td className="px-3 py-2">
                  <input className={`${txtCls} w-24 text-right ${errCls(`lq.${i}`)}`}
                    inputMode="numeric" value={q.min_qty} aria-label={`tier ${i + 1} min qty`}
                    onChange={(e) => { if (/^\d*$/.test(e.target.value)) upd((d) => { d.ladder[i].min_qty = e.target.value }) }} />
                  {errors.get(`lq.${i}`) && <ErrTag k={`lq.${i}`} errs={errors} />}
                </td>
                <td className="px-3 py-2">
                  <input className={`${txtCls} w-24 text-right ${errCls(`ld.${i}`)}`}
                    inputMode="decimal" value={q.discount_pct} aria-label={`tier ${i + 1} discount pct`}
                    onChange={(e) => { if (NUM_RE.test(e.target.value)) upd((d) => { d.ladder[i].discount_pct = e.target.value }) }} />
                  {errors.get(`ld.${i}`) && <ErrTag k={`ld.${i}`} errs={errors} />}
                </td>
                <td className="px-3 py-2 text-caption text-text-secondary">{q.label}</td>
              </tr>
            ))}
          </EditorTable>

          <EditorTable title="Customer tier factors" head={['Tier', 'Price ×', 'Payment terms']}>
            {draft.tiers.map((t, i) => (
              <tr key={t.name}>
                <td className="mono px-3 py-2 text-[13px] font-medium">{t.name}</td>
                <td className="px-3 py-2">
                  <input className={`${txtCls} w-24 text-right ${errCls(`tf.${i}`)}`}
                    inputMode="decimal" value={t.factor} aria-label={`${t.name} factor`}
                    onChange={(e) => { if (NUM_RE.test(e.target.value)) upd((d) => { d.tiers[i].factor = e.target.value }) }} />
                  {errors.get(`tf.${i}`) && <ErrTag k={`tf.${i}`} errs={errors} />}
                </td>
                <td className="px-3 py-2 text-caption text-text-secondary">{t.terms}</td>
              </tr>
            ))}
          </EditorTable>
        </div>

        <EditorTable
          title="Process fees"
          head={['Extra', `Fee (${draft.currency || 'CUR'})`, '', '']}
          action={
            <Button variant="ghost" size="sm"
              onClick={() => upd((d) => { d.fees.push({ key: nextKey(), name: '', fee: '' }) })}>
              <Plus size={14} strokeWidth={1.75} /> Add fee
            </Button>
          }
        >
          {draft.fees.map((f, i) => (
            <tr key={f.key}>
              <td className="px-3 py-2">
                <input className={`${txtCls} w-56 ${errCls(`fee.${i}.name`)}`}
                  value={f.name} aria-label={`process ${i + 1} name`} placeholder="Process name…"
                  onChange={(e) => upd((d) => { d.fees[i].name = e.target.value })} />
                {errors.get(`fee.${i}.name`) && <ErrTag k={`fee.${i}.name`} errs={errors} />}
              </td>
              <td className="px-3 py-2 text-right">
                <input className={`${txtCls} w-28 text-right ${errCls(`fee.${i}.val`)}`}
                  inputMode="decimal" value={f.fee} aria-label={`process ${i + 1} fee`}
                  onChange={(e) => { if (NUM_RE.test(e.target.value)) upd((d) => { d.fees[i].fee = e.target.value }) }} />
                {errors.get(`fee.${i}.val`) && <ErrTag k={`fee.${i}.val`} errs={errors} />}
              </td>
              <td className="w-10 px-1 py-2">
                <RowDelete label={`delete process ${f.name || i + 1}`} onClick={() => delFee(f.key)} />
              </td>
              <td />
            </tr>
          ))}
          {!draft.fees.length && (
            <tr><td colSpan={4} className="px-3 py-3 text-caption text-text-muted">
              No process fees — buyers can't order extras.
            </td></tr>
          )}
        </EditorTable>

        <EditorTable
          title="Size coefficients"
          head={['Size', 'Coefficient', '', '']}
          action={
            <Button variant="ghost" size="sm"
              onClick={() => upd((d) => { d.sizes.push({ key: nextKey(), size: '', coef: '1', locked: false }) })}>
              <Plus size={14} strokeWidth={1.75} /> Add size
            </Button>
          }
        >
          {draft.sizes.map((s, i) => (
            <tr key={s.key}>
              <td className="px-3 py-2">
                <input className={`${txtCls} w-32 mono text-[13px] ${errCls(`sz.${i}.name`)}`}
                  value={s.size} aria-label={`size ${i + 1} name`} placeholder="SIZE"
                  onChange={(e) => upd((d) => { d.sizes[i].size = e.target.value.toUpperCase() })} />
                {errors.get(`sz.${i}.name`) && <ErrTag k={`sz.${i}.name`} errs={errors} />}
              </td>
              <td className="px-3 py-2">
                {s.locked ? (
                  <span className="inline-flex h-8 items-center gap-1.5 rounded-md border border-dashed border-line bg-surface-subtle px-2 text-caption text-text-muted"
                    title="coef 0 = manual-quote escape hatch — immutable by design">
                    <AlertTriangle size={12} strokeWidth={1.75} style={{ color: 'var(--st-attention-dot)' }} />
                    {s.coef} · manual-quote hatch
                  </span>
                ) : (
                  <>
                    <input className={`${txtCls} w-24 text-right ${errCls(`sz.${i}.coef`)}`}
                      inputMode="decimal" value={s.coef} aria-label={`${s.size || 'new size'} coefficient`}
                      onChange={(e) => { if (NUM_RE.test(e.target.value)) upd((d) => { d.sizes[i].coef = e.target.value }) }} />
                    {errors.get(`sz.${i}.coef`) && <ErrTag k={`sz.${i}.coef`} errs={errors} />}
                  </>
                )}
              </td>
              <td className="w-10 px-1 py-2">
                <RowDelete label={`delete size ${s.size || i + 1}`} onClick={() => delSize(s.key)}
                  disabled={draft.sizes.length <= 1}
                  title={draft.sizes.length <= 1 ? 'At least one size must remain' : undefined} />
              </td>
              <td />
            </tr>
          ))}
          {errors.get('sizes.empty') && (
            <tr><td colSpan={4} className="px-3 pb-2 text-micro text-[#B91C1C]">{errors.get('sizes.empty')}</td></tr>
          )}
        </EditorTable>

        <p className="pb-2 text-caption text-text-muted">
          The coefficient-0 escape hatch is immutable in VALUE: it is how S2
          tells the agent "never compute this size — escalate". Deleting a
          size or fee removes it from the agent's vocabulary immediately
          (the parser reloads with the same save).
        </p>
      </div>

      <footer className="shrink-0 space-y-2 border-t border-line bg-surface-card p-3">
        {showDiff && (
          <div className="max-h-44 overflow-auto rounded-md border border-line bg-surface-card">
            {changes.length === 0 ? (
              <p className="p-3 text-caption text-text-muted">No changes yet.</p>
            ) : (
              <table className="w-full text-caption">
                <tbody>
                  {changes.map((c, i) => (
                    <tr key={c.path + i} className="border-b border-line last:border-0">
                      <td className="w-4 pl-3 mono">
                        {c.kind === 'add' && <span className="text-[#15803D]">+</span>}
                        {c.kind === 'remove' && <span className="text-[#B91C1C]">−</span>}
                      </td>
                      <td className={`py-1.5 pr-3 font-medium ${c.kind === 'remove' ? 'text-text-muted line-through' : ''}`}>
                        {c.path}
                      </td>
                      <td className="py-1.5 pr-2 text-right mono text-[12px] text-[#B91C1C] line-through">
                        {c.kind === 'add' ? '' : c.from}
                      </td>
                      <td className="py-1.5 pr-3 text-right mono text-[12px] text-[#15803D]">
                        {c.kind === 'remove' ? '' : c.to}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
        <div className="flex flex-wrap items-center justify-end gap-2">
          {!dirty && !errors.size && (
            <span className="mr-auto inline-flex items-center gap-1.5 text-caption text-text-muted">
              <RotateCcw size={13} strokeWidth={1.75} /> Edit values above — diff appears before any save.
            </span>
          )}
          {dirty && errors.size > 0 && (
            <span className="mr-auto inline-flex items-center gap-1.5 text-caption text-[#B91C1C]">
              <AlertTriangle size={13} strokeWidth={1.75} />
              {errors.size} invalid field{errors.size > 1 ? 's' : ''} — fix the red ones.
            </span>
          )}
          <Button variant="ghost" size="sm" onClick={() => setShowDiff((s) => !s)}
            disabled={!dirty}>
            <RotateCcw size={14} strokeWidth={1.75} />
            {showDiff ? 'Hide diff' : `Review changes (${changes.length})`}
          </Button>
          <Button variant="primary" size="sm" onClick={save} loading={saving}
            disabled={!canSave} title={
              !dirty ? 'Nothing changed yet'
              : errors.size ? 'Fix invalid fields first'
              : 'Write .bak, save file, hot-reload calc'}>
            <Save size={14} strokeWidth={1.75} />
            Save & reload calc
          </Button>
        </div>
      </footer>
    </div>
  )
}

function RowDelete({
  label, onClick, disabled = false, title,
}: {
  label: string
  onClick: () => void
  disabled?: boolean
  title?: string
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      title={title ?? label}
      className="rounded-md p-1.5 text-text-secondary transition-colors duration-150 hover:bg-surface-subtle hover:text-[#B91C1C] disabled:cursor-not-allowed disabled:opacity-40"
    >
      <Trash2 size={15} strokeWidth={1.75} />
    </button>
  )
}

function ErrTag({ k, errs }: { k: ErrKey; errs: Map<ErrKey, string> }) {
  return <p className="mt-0.5 text-left text-micro text-[#B91C1C]">{errs.get(k)}</p>
}

function NumField({
  label, value, onChange, error, cls, hint,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  error?: string
  cls: string
  hint?: string
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-caption uppercase tracking-wide text-text-secondary">{label}</span>
      <input className={`h-9 w-full rounded-md border px-2.5 text-body outline-none transition-colors focus:ring-2 ${cls}`}
        inputMode="decimal" value={value}
        onChange={(e) => { if (NUM_RE.test(e.target.value)) onChange(e.target.value) }} />
      {(error || hint) && (
        <span className={`mt-0.5 block text-micro ${error ? 'text-[#B91C1C]' : 'text-text-muted'}`}>
          {error ?? hint}
        </span>
      )}
    </label>
  )
}

function EditorTable({
  title, head, children, action,
}: {
  title: string
  head: string[]
  children: ReactNode
  action?: ReactNode
}) {
  return (
    <section className="overflow-hidden rounded-lg border border-line bg-surface-card">
      <div className="flex items-center justify-between border-b border-line px-4 py-2">
        <h3 className="text-section font-semibold">{title}</h3>
        {action}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[480px]">
          <thead>
            <tr className="border-b border-line bg-surface-subtle">
              {head.map((h, i) => (
                <th key={h + i} className={`px-3 py-2 text-micro font-medium uppercase tracking-wide text-text-muted ${i > 0 && i < head.length - 1 ? 'text-right' : 'text-left'}`}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-line">{children}</tbody>
        </table>
      </div>
    </section>
  )
}
