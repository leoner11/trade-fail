import { Plus, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { spine } from '../../api/spine'
import type { POStatus, POLine, PurchaseOrder, Supplier, SupplierItem } from '../../api/spine'
import { Button } from '../../components/ui/Button'
import { DataTable } from '../../components/ui/DataTable'
import type { Column } from '../../components/ui/DataTable'
import { SectionPanel } from '../../components/ui/SectionPanel'
import { StatusBadge } from '../../components/ui/StatusBadge'
import { formatDate, formatMoney } from '../../lib/format'
import { useAsync } from '../../lib/useAsync'
import { usePoll } from '../../lib/usePoll'

const PO_STATUSES: POStatus[] = [
  'draft',
  'approved',
  'sent',
  'confirmed',
  'shipped',
  'received',
  'cancelled',
]

const isOverdue = (po: PurchaseOrder) =>
  !!po.promised_date &&
  po.promised_date < new Date().toISOString().slice(0, 10) &&
  !['received', 'cancelled'].includes(po.status)

export function ProcurementPage() {
  const suppliers = usePoll(() => spine.listSuppliers(), 30_000)
  const [selected, setSelected] = useState<Supplier | null>(null)
  const items = useAsync(
    () => (selected ? spine.listSupplierItems(selected.id) : Promise.resolve({ items: [] as SupplierItem[] })),
    [selected?.id],
  )
  const pos = usePoll(() => spine.listPOs(), 20_000)

  const supplierName = (id: number) =>
    suppliers.data?.items.find((s) => s.id === id)?.name ?? `#${id}`

  // ---- add supplier ----
  const [supForm, setSupForm] = useState(false)
  const [sup, setSup] = useState({ name: '', contact: '', terms: '', lead_time_days: '0', notes: '' })
  const [supBusy, setSupBusy] = useState(false)
  const [supMsg, setSupMsg] = useState('')

  async function addSupplier() {
    setSupBusy(true)
    setSupMsg('')
    try {
      await spine.addSupplier({
        name: sup.name.trim(),
        contact: sup.contact.trim(),
        terms: sup.terms.trim(),
        lead_time_days: Number(sup.lead_time_days) || 0,
        notes: sup.notes.trim(),
      })
      setSup({ name: '', contact: '', terms: '', lead_time_days: '0', notes: '' })
      setSupForm(false)
      await suppliers.refresh()
    } catch (e) {
      setSupMsg(e instanceof Error ? e.message : String(e))
    } finally {
      setSupBusy(false)
    }
  }

  // ---- add supplier item ----
  const [item, setItem] = useState({ sku: '', description: '', price: '', currency: 'USD', moq: '1', capability_note: '' })
  const [itemBusy, setItemBusy] = useState(false)
  const [itemMsg, setItemMsg] = useState('')

  async function addItem() {
    if (!selected) return
    setItemBusy(true)
    setItemMsg('')
    try {
      await spine.addSupplierItem(selected.id, {
        sku: item.sku.trim(),
        description: item.description.trim(),
        price: Number(item.price),
        currency: item.currency || 'USD',
        moq: Number(item.moq) || 1,
        capability_note: item.capability_note.trim(),
      })
      setItem({ sku: '', description: '', price: '', currency: 'USD', moq: '1', capability_note: '' })
      await items.retry()
    } catch (e) {
      setItemMsg(e instanceof Error ? e.message : String(e))
    } finally {
      setItemBusy(false)
    }
  }

  // ---- POs ----
  const [poBusy, setPoBusy] = useState('')
  async function setStatus(po: PurchaseOrder, status: POStatus) {
    setPoBusy(po.po_id)
    try {
      await spine.setPOStatus(po.po_id, status)
      await pos.refresh()
    } finally {
      setPoBusy('')
    }
  }

  const [poForm, setPoForm] = useState(false)
  const [poSupplier, setPoSupplier] = useState('')
  const [poLines, setPoLines] = useState<POLine[]>([{ sku: '', description: '', qty: 1, price: 0 }])
  const [poQuoteId, setPoQuoteId] = useState('')
  const [poDate, setPoDate] = useState('')
  const [poMsg, setPoMsg] = useState('')

  async function createPO() {
    setPoMsg('')
    const lines = poLines.filter((l) => (l.sku || l.description) && l.qty > 0)
    setPoBusy('po')
    try {
      const res = await spine.createPO({
        supplier_id: Number(poSupplier),
        lines,
        quote_id: poQuoteId.trim() || undefined,
        promised_date: poDate || undefined,
      })
      setPoMsg(`${res.po_id} created — ${formatMoney(res.total)} (status draft; approve before sending).`)
      setPoForm(false)
      setPoLines([{ sku: '', description: '', qty: 1, price: 0 }])
      setPoQuoteId('')
      setPoDate('')
      await pos.refresh()
    } catch (e) {
      setPoMsg(e instanceof Error ? e.message : String(e))
    } finally {
      setPoBusy('')
    }
  }

  const supCols: Column<Supplier>[] = [
    { key: 'name', header: 'Supplier' },
    { key: 'contact', header: 'Contact', width: 180 },
    { key: 'terms', header: 'Terms', width: 110 },
    { key: 'lead', header: 'Lead', width: 80, align: 'right', render: (r) => (r.lead_time_days ? `${r.lead_time_days}d` : '—') },
  ]

  const itemCols: Column<SupplierItem>[] = [
    { key: 'sku', header: 'SKU', mono: true, width: 140 },
    { key: 'description', header: 'Description' },
    { key: 'price', header: 'Price', align: 'right', width: 110, render: (r) => formatMoney(r.price, r.currency) },
    { key: 'moq', header: 'MOQ', align: 'right', width: 70 },
  ]

  const poCols: Column<PurchaseOrder>[] = [
    { key: 'po_id', header: 'PO', mono: true, width: 120 },
    { key: 'supplier', header: 'Supplier', width: 170, render: (r) => supplierName(r.supplier_id) },
    { key: 'total', header: 'Total', align: 'right', width: 110, render: (r) => formatMoney(r.total, r.currency) },
    {
      key: 'status',
      header: 'Status',
      width: 150,
      render: (r) => (
        <select
          value={r.status}
          disabled={poBusy === r.po_id}
          aria-label={`status of ${r.po_id}`}
          onChange={(e) => setStatus(r, e.target.value as POStatus)}
          className="h-7 w-full rounded-md border border-line bg-surface-card px-1.5 text-caption outline-none focus:border-brand"
        >
          {PO_STATUSES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      ),
    },
    {
      key: 'promised',
      header: 'Promised',
      width: 130,
      render: (r) =>
        r.promised_date ? (
          <span className="flex items-center gap-1.5">
            {formatDate(r.promised_date)}
            {isOverdue(r) && <StatusBadge tone="danger" label="overdue" />}
          </span>
        ) : (
          '—'
        ),
    },
  ]

  const input =
    'h-9 w-full rounded-md border border-line bg-surface-card px-3 text-body outline-none transition-colors focus:border-brand focus:ring-2 focus:ring-brand/20'

  return (
    <div className="mx-auto max-w-4xl space-y-4">
      <SectionPanel
        title={`Suppliers (${suppliers.data?.items.length ?? 0})`}
        action={
          <Button size="sm" variant={supForm ? 'ghost' : 'primary'} onClick={() => setSupForm((v) => !v)}>
            <Plus size={14} /> Add supplier
          </Button>
        }
        bodyClassName="p-0"
      >
        {supForm && (
          <div className="space-y-2 border-b border-line p-4">
            <div className="grid grid-cols-2 gap-2">
              <input className={input} placeholder="Name *" value={sup.name} onChange={(e) => setSup({ ...sup, name: e.target.value })} />
              <input className={input} placeholder="Contact" value={sup.contact} onChange={(e) => setSup({ ...sup, contact: e.target.value })} />
              <input className={input} placeholder="Terms — e.g. 30% TT" value={sup.terms} onChange={(e) => setSup({ ...sup, terms: e.target.value })} />
              <input className={input} placeholder="Lead time (days)" type="number" min={0} value={sup.lead_time_days} onChange={(e) => setSup({ ...sup, lead_time_days: e.target.value })} />
            </div>
            <input className={input} placeholder="Notes" value={sup.notes} onChange={(e) => setSup({ ...sup, notes: e.target.value })} />
            <div className="flex items-center gap-2">
              <Button variant="primary" size="sm" loading={supBusy} disabled={!sup.name.trim()} onClick={addSupplier}>
                Save supplier
              </Button>
              {supMsg && <span className="text-caption text-[#EF4444]">{supMsg}</span>}
            </div>
          </div>
        )}
        <DataTable
          columns={supCols}
          rows={suppliers.data?.items ?? []}
          rowKey={(r) => String(r.id)}
          loading={suppliers.loading && !suppliers.data}
          onRowClick={(r) => setSelected(r)}
          activeKey={selected ? String(selected.id) : undefined}
          emptyMessage="No suppliers yet — add the first one."
        />
      </SectionPanel>

      {selected && (
        <SectionPanel title={`Supplier items — ${selected.name}`} bodyClassName="p-0">
          <div className="space-y-2 border-b border-line p-4">
            <div className="grid grid-cols-3 gap-2">
              <input className={input} placeholder="SKU" value={item.sku} onChange={(e) => setItem({ ...item, sku: e.target.value })} />
              <input className={input} placeholder="Description" value={item.description} onChange={(e) => setItem({ ...item, description: e.target.value })} />
              <input className={input} placeholder="Price *" type="number" step="0.01" min={0} value={item.price} onChange={(e) => setItem({ ...item, price: e.target.value })} />
              <input className={input} placeholder="Currency" value={item.currency} onChange={(e) => setItem({ ...item, currency: e.target.value })} />
              <input className={input} placeholder="MOQ" type="number" min={1} value={item.moq} onChange={(e) => setItem({ ...item, moq: e.target.value })} />
              <input className={input} placeholder="Capability note" value={item.capability_note} onChange={(e) => setItem({ ...item, capability_note: e.target.value })} />
            </div>
            <div className="flex items-center gap-2">
              <Button size="sm" loading={itemBusy} disabled={!item.price} onClick={addItem}>
                Add item
              </Button>
              {itemMsg && <span className="text-caption text-[#EF4444]">{itemMsg}</span>}
            </div>
          </div>
          <DataTable columns={itemCols} rows={items.data?.items ?? []} rowKey={(r) => String(r.id)} loading={items.loading} emptyMessage="No items for this supplier." />
        </SectionPanel>
      )}

      <SectionPanel
        title={`Purchase orders (${pos.data?.items.length ?? 0})`}
        action={
          <Button
            size="sm"
            variant={poForm ? 'ghost' : 'primary'}
            disabled={!suppliers.data?.items.length}
            onClick={() => setPoForm((v) => !v)}
          >
            <Plus size={14} /> New PO
          </Button>
        }
        bodyClassName="p-0"
      >
        {poForm && (
          <div className="space-y-2 border-b border-line p-4">
            <div className="grid grid-cols-3 gap-2">
              <select className={input} value={poSupplier} onChange={(e) => setPoSupplier(e.target.value)} aria-label="Supplier">
                <option value="">Supplier *</option>
                {(suppliers.data?.items ?? []).map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
              <input className={input} placeholder="Quote ID (optional)" value={poQuoteId} onChange={(e) => setPoQuoteId(e.target.value)} />
              <input className={input} type="date" aria-label="Promised date" value={poDate} onChange={(e) => setPoDate(e.target.value)} />
            </div>
            {poLines.map((l, i) => (
              <div key={i} className="grid grid-cols-[1fr_90px_110px_36px] gap-2">
                <input
                  className={input}
                  placeholder={i === 0 ? 'SKU / description *' : 'SKU / description'}
                  value={l.sku || l.description}
                  onChange={(e) =>
                    setPoLines((ls) => ls.map((x, j) => (j === i ? { ...x, sku: e.target.value, description: e.target.value } : x)))
                  }
                />
                <input
                  className={input}
                  placeholder="Qty"
                  type="number"
                  min={1}
                  value={l.qty || ''}
                  onChange={(e) => setPoLines((ls) => ls.map((x, j) => (j === i ? { ...x, qty: Number(e.target.value) || 0 } : x)))}
                />
                <input
                  className={input}
                  placeholder="Price"
                  type="number"
                  step="0.01"
                  min={0}
                  value={l.price || ''}
                  onChange={(e) => setPoLines((ls) => ls.map((x, j) => (j === i ? { ...x, price: Number(e.target.value) || 0 } : x)))}
                />
                <button
                  aria-label="remove line"
                  className="flex items-center justify-center rounded-md text-text-secondary transition-colors hover:bg-surface-subtle hover:text-text-primary disabled:opacity-40"
                  disabled={poLines.length === 1}
                  onClick={() => setPoLines((ls) => ls.filter((_, j) => j !== i))}
                >
                  <Trash2 size={15} />
                </button>
              </div>
            ))}
            <div className="flex items-center gap-2">
              <Button size="sm" onClick={() => setPoLines((ls) => [...ls, { sku: '', description: '', qty: 1, price: 0 }])}>
                + line
              </Button>
              <Button
                variant="primary"
                size="sm"
                loading={poBusy === 'po'}
                disabled={!poSupplier || !poLines.some((l) => (l.sku || l.description) && l.qty > 0)}
                onClick={createPO}
              >
                Create PO (draft)
              </Button>
              {poMsg && <span className="text-caption text-text-secondary">{poMsg}</span>}
            </div>
          </div>
        )}
        <DataTable
          columns={poCols}
          rows={pos.data?.items ?? []}
          rowKey={(r) => r.po_id}
          loading={pos.loading && !pos.data}
          emptyMessage="No purchase orders yet."
        />
      </SectionPanel>
    </div>
  )
}
