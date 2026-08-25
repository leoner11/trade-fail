import { FileUp, Pencil, Plus, Trash2 } from 'lucide-react'
import { useRef, useState } from 'react'
import { spine } from '../../api/spine'
import type {
  CatalogDetail,
  CatalogItem,
  CatalogItemIn,
  GapReport,
} from '../../api/spine'
import { Button } from '../../components/ui/Button'
import { ConfirmDialog } from '../../components/ui/ConfirmDialog'
import { DataTable } from '../../components/ui/DataTable'
import type { Column } from '../../components/ui/DataTable'
import { GateBanner } from '../../components/ui/GateBanner'
import { SectionPanel } from '../../components/ui/SectionPanel'
import { useAsync } from '../../lib/useAsync'

const COLUMNS: Column<CatalogItem>[] = [
  { key: 'sku', header: 'SKU', mono: true, width: 140 },
  { key: 'name', header: 'Product' },
  { key: 'category', header: 'Category', width: 160 },
]

interface SpecRow { key: number; k: string; v: string }
let specUid = 1

const EMPTY_FORM = {
  sku: '',
  name: '',
  category: '',
  moq: '1',
  hs_code: '',
  certs: '',
}

export function CatalogPage() {
  const catalog = useAsync(() => spine.listCatalog(), [])
  const [uploading, setUploading] = useState(false)
  const [report, setReport] = useState<GapReport | null>(null)
  const [error, setError] = useState('')
  const fileInput = useRef<HTMLInputElement>(null)

  // add/edit form state
  const [formOpen, setFormOpen] = useState(false)
  const [editingSku, setEditingSku] = useState<string | null>(null)
  const [form, setForm] = useState(EMPTY_FORM)
  const [specs, setSpecs] = useState<SpecRow[]>([{ key: ++specUid, k: '', v: '' }])
  const [saving, setSaving] = useState(false)
  const [saveMsg, setSaveMsg] = useState<{ tone: 'success' | 'danger'; text: string } | null>(null)
  const [deleting, setDeleting] = useState<CatalogItem | null>(null)

  function openAdd() {
    setEditingSku(null)
    setForm(EMPTY_FORM)
    setSpecs([{ key: ++specUid, k: '', v: '' }])
    setSaveMsg(null)
    setError('')
    setFormOpen(true)
  }

  async function openEdit(row: CatalogItem) {
    try {
      const detail: CatalogDetail = await spine.getCatalogItem(row.sku)
      setEditingSku(row.sku)
      setForm({
        sku: detail.sku,
        name: detail.name,
        category: detail.category ?? '',
        moq: String(detail.moq ?? ''),
        hs_code: detail.hs_code ?? '',
        certs: detail.certs ?? '',
      })
      setSpecs(
        Object.entries(detail.specs ?? {}).map(([k, v]) => ({ key: ++specUid, k, v: String(v) })),
      )
      if (!specs.length) setSpecs([{ key: ++specUid, k: '', v: '' }])
      setSaveMsg(null)
      setError('')
      setFormOpen(true)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  async function saveForm() {
    if (!form.sku.trim() || !form.name.trim()) return
    setSaving(true)
    setSaveMsg(null)
    try {
      const item: CatalogItemIn = {
        sku: form.sku.trim().toUpperCase(),
        name: form.name.trim(),
        category: form.category.trim(),
        specs: Object.fromEntries(
          specs.filter((s) => s.k.trim()).map((s) => [s.k.trim(), s.v.trim()]),
        ),
        moq: Math.max(0, Math.trunc(Number(form.moq) || 0)),
        hs_code: form.hs_code.trim(),
        certs: form.certs.trim(),
      }
      const res = await spine.upsertCatalogItem(item)
      setSaveMsg({
        tone: 'success',
        text:
          `${editingSku ? 'Updated' : 'Added'} ${res.sku}.` +
          (res.missing.length ? ` Gaps: ${res.missing.join(', ')}` : ' No gaps.'),
      })
      catalog.retry()
      if (!editingSku) {
        // keep the panel open for the next entry? no — close on clean add
        setFormOpen(false)
        setForm(EMPTY_FORM)
        setSpecs([{ key: ++specUid, k: '', v: '' }])
      }
    } catch (e) {
      setSaveMsg({ tone: 'danger', text: e instanceof Error ? e.message : String(e) })
    } finally {
      setSaving(false)
    }
  }

  async function importCsv(file: File) {
    setError('')
    setReport(null)
    setUploading(true)
    try {
      const res = await spine.importCatalog(await file.text())
      setReport(res)
      catalog.retry()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setUploading(false)
      if (fileInput.current) fileInput.current.value = ''
    }
  }

  async function removeItem() {
    if (!deleting) return
    await spine.deleteCatalogItem(deleting.sku).catch(() => undefined)
    setDeleting(null)
    catalog.retry()
  }

  const canSaveForm = form.sku.trim() && form.name.trim() && !saving

  return (
    <div className="mx-auto max-w-4xl space-y-4">
      <SectionPanel
        title={`S1 catalog · ${catalog.data?.items.length ?? '…'} SKUs`}
        action={
          <>
            <input
              ref={fileInput}
              type="file"
              accept=".csv,text/csv"
              hidden
              onChange={(e) => e.target.files?.[0] && importCsv(e.target.files[0])}
            />
            <Button variant="secondary" size="sm" onClick={() => fileInput.current?.click()} loading={uploading}>
              <FileUp size={14} /> Import .csv
            </Button>
            <Button variant="primary" size="sm" onClick={() => (formOpen ? setFormOpen(false) : openAdd())}>
              {formOpen ? 'Close' : <><Plus size={14} /> Add product</>}
            </Button>
          </>
        }
        bodyClassName="p-0"
      >
        {error && (
          <div className="px-4 pt-3">
            <GateBanner tone="danger" title="Failed" meta={error} />
          </div>
        )}
        {saveMsg && (
          <div className="px-4 pt-3">
            <GateBanner
              tone={saveMsg.tone === 'success' ? 'info' : 'danger'}
              title={saveMsg.tone === 'success' ? 'Saved' : 'Save failed'}
              meta={saveMsg.text}
            />
          </div>
        )}

        {formOpen ? (
          <div className="space-y-3 border-b border-line px-4 py-4" data-testid="product-form">
            <p className="text-caption text-text-secondary">
              {editingSku ? (
                <>Editing <span className="mono text-[13px]">{editingSku}</span> — same SKU replaces.</>
              ) : (
                <>New SKU. Specs are what the agent may quote verbatim — empty fields land in the gap report.</>
              )}
            </p>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-6">
              <Field label="SKU *" value={form.sku} onChange={(v) => setForm((f) => ({ ...f, sku: v.toUpperCase() }))} mono />
              <Field label="Name *" value={form.name} onChange={(v) => setForm((f) => ({ ...f, name: v }))} wide />
              <Field label="Category" value={form.category} onChange={(v) => setForm((f) => ({ ...f, category: v }))} />
              <Field label="MOQ" value={form.moq} onChange={(v) => setForm((f) => ({ ...f, moq: v.replace(/\D/g, '') }))} />
              <Field label="HS code" value={form.hs_code} onChange={(v) => setForm((f) => ({ ...f, hs_code: v }))} />
              <Field label="Certs" value={form.certs} onChange={(v) => setForm((f) => ({ ...f, certs: v }))} wide />
            </div>
            <div className="space-y-2">
              <p className="text-caption uppercase tracking-wide text-text-secondary">Specs</p>
              {specs.map((s, i) => (
                <div key={s.key} className="flex items-center gap-2">
                  <input
                    className="h-8 w-40 rounded-md border border-line bg-surface-card px-2 text-body outline-none transition-colors focus:border-brand focus:ring-2 focus:ring-brand/20"
                    placeholder="key (e.g. power)"
                    value={s.k}
                    aria-label={`spec ${i + 1} key`}
                    onChange={(e) => setSpecs((rows) => rows.map((r) => (r.key === s.key ? { ...r, k: e.target.value } : r)))}
                  />
                  <input
                    className="h-8 flex-1 rounded-md border border-line bg-surface-card px-2 text-body outline-none transition-colors focus:border-brand focus:ring-2 focus:ring-brand/20"
                    placeholder="value (e.g. 50kVA / 40kW)"
                    value={s.v}
                    aria-label={`spec ${i + 1} value`}
                    onChange={(e) => setSpecs((rows) => rows.map((r) => (r.key === s.key ? { ...r, v: e.target.value } : r)))}
                  />
                  <button
                    type="button"
                    aria-label={`remove spec ${i + 1}`}
                    onClick={() => setSpecs((rows) => (rows.length > 1 ? rows.filter((r) => r.key !== s.key) : [{ ...s, k: '', v: '' }]))}
                    className="rounded-md p-1.5 text-text-secondary transition-colors hover:bg-surface-subtle hover:text-[#B91C1C]"
                  >
                    <Trash2 size={14} strokeWidth={1.75} />
                  </button>
                </div>
              ))}
              <Button variant="ghost" size="sm"
                onClick={() => setSpecs((rows) => [...rows, { key: ++specUid, k: '', v: '' }])}>
                <Plus size={13} strokeWidth={1.75} /> Add spec row
              </Button>
            </div>
            <div className="flex justify-end gap-2 pt-1">
              <Button variant="secondary" size="sm" onClick={() => setFormOpen(false)}>Cancel</Button>
              <Button variant="primary" size="sm" onClick={saveForm} loading={saving} disabled={!canSaveForm}>
                {editingSku ? 'Update SKU' : 'Add to catalog'}
              </Button>
            </div>
          </div>
        ) : null}

        <DataTable
          columns={[
            ...COLUMNS,
            {
              key: 'actions',
              header: '',
              width: 100,
              render: (r) => (
                <div className="flex items-center justify-end gap-1">
                  <button
                    onClick={() => openEdit(r)}
                    aria-label={`Edit ${r.sku}`}
                    title="Edit"
                    className="rounded-md p-1.5 text-text-secondary transition-colors hover:bg-surface-subtle hover:text-brand"
                  >
                    <Pencil size={15} strokeWidth={1.75} />
                  </button>
                  <button
                    onClick={() => setDeleting(r)}
                    aria-label={`Delete ${r.sku}`}
                    title="Delete"
                    className="rounded-md p-1.5 text-text-secondary transition-colors hover:bg-surface-subtle hover:text-[#B91C1C]"
                  >
                    <Trash2 size={15} strokeWidth={1.75} />
                  </button>
                </div>
              ),
            },
          ]}
          rows={catalog.data?.items ?? []}
          rowKey={(r) => r.sku}
          loading={catalog.loading}
          emptyMessage={
            catalog.data?.items.length
              ? ''
              : 'No SKUs yet — import a CSV or add the first product.'
          }
        />
        {!catalog.loading && !!catalog.data?.items.length && (
          <p className="border-t px-4 py-2 text-micro text-text-muted">
            Click the pencil to edit specs inline; same-SKU CSV imports still replace rows.
          </p>
        )}
      </SectionPanel>

      <ConfirmDialog
        open={!!deleting}
        title="Delete this product?"
        body={
          <>
            <span className="mono text-[13px]">{deleting?.sku}</span> ({deleting?.name}) will be removed from S1.
            The agent will no longer answer spec questions about it; past quotes are unaffected.
          </>
        }
        confirmLabel="Delete"
        onCancel={() => setDeleting(null)}
        onConfirm={removeItem}
      />

      <SectionPanel title="Bulk import (CSV)" bodyClassName="p-0">
        <p className="px-4 py-3 text-caption text-text-secondary">
          Columns: <span className="mono text-[13px]">sku,name,category,specs,moq,hs_code,certs</span> — specs as{' '}
          <span className="mono text-[13px]">key=value;key=value</span>. Same SKU replaces.
        </p>
        {report && (
          <div className="space-y-2 border-t px-4 py-3">
            <GateBanner
              tone="info"
              title={`${report.imported} SKUs imported`}
              meta={
                report.gap_report.length === 0 && report.skipped.length === 0
                  ? 'No gaps found.'
                  : `${report.skipped.length} skipped · gap report below`
              }
            />
            {report.skipped.length > 0 && (
              <p className="text-caption text-[#B91C1C]">
                {report.skipped.map((s) => `line ${s.line}: ${s.reason}`).join(' · ')}
              </p>
            )}
            {report.gap_report.length > 0 && (
              <DataTable
                columns={[
                  { key: 'sku', header: 'SKU', mono: true, width: 140 },
                  { key: 'missing', header: 'Missing fields' },
                ]}
                rows={report.gap_report.map((g) => ({ ...g, missing: g.missing.join(', ') }))}
                rowKey={(g) => g.sku + g.missing}
                emptyMessage=""
              />
            )}
            {report.gap_report.length > 0 && (
              <p className="text-caption text-text-muted">
                This is deliverable #1 of onboarding: exactly what your AI will and won't know.
              </p>
            )}
          </div>
        )}
      </SectionPanel>
    </div>
  )
}

function Field({
  label, value, onChange, mono = false, wide = false,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  mono?: boolean
  wide?: boolean
}) {
  return (
    <label className={`block ${wide ? 'col-span-2' : ''}`}>
      <span className="mb-1 block text-micro uppercase tracking-wide text-text-secondary">{label}</span>
      <input
        className={`h-9 w-full rounded-md border border-line bg-surface-card px-2 text-body outline-none transition-colors focus:border-brand focus:ring-2 focus:ring-brand/20 ${
          mono ? 'mono text-[13px]' : ''
        }`}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </label>
  )
}
