import { FileUp, PenLine, Trash2 } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { glueApi } from '../../api/glue'
import type { GateLast, KbDoc, QuizJob } from '../../api/glue'
import { Button } from '../../components/ui/Button'
import { ConfirmDialog } from '../../components/ui/ConfirmDialog'
import { DataTable } from '../../components/ui/DataTable'
import type { Column } from '../../components/ui/DataTable'
import { EmptyState } from '../../components/ui/EmptyState'
import { GateBanner } from '../../components/ui/GateBanner'
import { SectionPanel } from '../../components/ui/SectionPanel'
import { Spinner } from '../../components/ui/Skeleton'
import { StatusBadge } from '../../components/ui/StatusBadge'
import type { Tone } from '../../lib/domain'
import { formatDateTime } from '../../lib/format'
import { usePoll } from '../../lib/usePoll'

function docTone(status: string): Tone {
  if (status === 'completed') return 'success'
  if (status === 'indexing' || status === 'parsing' || status === 'waiting') return 'info'
  if (status === 'error') return 'danger'
  return 'neutral'
}

function quizTone(g: GateLast): 'success' | 'danger' | 'attention' {
  if (!g.found) return 'attention'
  return g.gate_pass ? 'success' : 'danger'
}

export function KnowledgePage() {
  const kb = usePoll(() => glueApi.kbDocs(), 8000)
  const gate = usePoll<GateLast>(() => glueApi.gateLast(), 15000)
  const [uploading, setUploading] = useState(false)
  const [notice, setNotice] = useState<{ tone: 'danger' | 'info'; text: string } | null>(null)
  const [deleting, setDeleting] = useState<KbDoc | null>(null)
  const [jobId, setJobId] = useState('')
  const [finished, setFinished] = useState<QuizJob | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)

  // in-console doc writer
  const [writing, setWriting] = useState(false)
  const [docName, setDocName] = useState('')
  const [docText, setDocText] = useState('')
  const [savingDoc, setSavingDoc] = useState(false)

  const job = usePoll<QuizJob>(() => glueApi.quizJob(jobId), 2000, !!jobId)

  const indexing = (kb.data?.items ?? []).some(
    (d) => d.status !== 'completed' && d.status !== 'error',
  )

  useEffect(() => {
    if (!indexing) kb.refresh()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [indexing])

  useEffect(() => {
    if (job.data?.status === 'done' && jobId) {
      setFinished(job.data)
      setJobId('')
      gate.refresh()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [job.data, jobId])

  async function upload(file: File) {
    setNotice(null)
    setUploading(true)
    try {
      await glueApi.kbUpload(file)
      kb.refresh()
    } catch (e) {
      setNotice({ tone: 'danger', text: e instanceof Error ? e.message : String(e) })
    } finally {
      setUploading(false)
      if (fileInput.current) fileInput.current.value = ''
    }
  }

  async function saveDoc() {
    const name = docName.trim()
    if (!name || !docText.trim()) return
    setNotice(null)
    setSavingDoc(true)
    try {
      const res = await glueApi.kbWriteDoc(name, docText)
      setWriting(false)
      setDocName('')
      setDocText('')
      kb.refresh()
      setNotice({
        tone: 'info',
        text: `${res.replaced ? 'Replaced' : 'Created'} ${name.includes('.') ? name : name + '.md'} — indexing runs now; the O2 gate re-checks answers.`,
      })
    } catch (e) {
      setNotice({ tone: 'danger', text: e instanceof Error ? e.message : String(e) })
    } finally {
      setSavingDoc(false)
    }
  }

  async function runQuiz() {
    setFinished(null)
    try {
      const { job_id } = await glueApi.quizStart()
      setJobId(job_id)
    } catch (e) {
      setNotice({ tone: 'danger', text: e instanceof Error ? e.message : String(e) })
    }
  }

  async function remove() {
    if (!deleting) return
    await glueApi.kbDelete(deleting.id).catch(() => undefined)
    setDeleting(null)
    setFinished(null)
    kb.refresh()
  }

  const g = finished
    ? {
        found: true,
        passed: finished.passed,
        total: finished.total,
        required: finished.required,
        fabricated: finished.fabricated,
        gate_pass: finished.gate_pass,
        ts: undefined,
      }
    : gate.data

  return (
    <div className="mx-auto max-w-4xl space-y-4">
      <GateBanner
        tone={quizTone(g ?? { found: false })}
        title={
          g?.found
            ? g.gate_pass
              ? `O2 quiz passed — ${g.passed}/${g.total} correct, ${g.fabricated} fabrications`
              : `O2 quiz FAILED — ${g.passed}/${g.total} correct (need ≥${g.required}, 0 fabrications)`
            : 'O2 verification quiz not run yet — required before go-live'
        }
        meta={
          g?.found && !finished
            ? `last run ${formatDateTime(g.ts)} · ⛔ go-live blocked until this passes`
            : 'the agent quizzes itself against the knowledge base through the live A3-Spec workflow'
        }
        actions={
          <Button variant="primary" size="sm" onClick={runQuiz} loading={!!jobId}>
            Run quiz
          </Button>
        }
      />

      {jobId && (
        <SectionPanel title={`Quiz running · ${job.data?.progress ?? ''}`} bodyClassName="p-4">
          <div className="flex items-center gap-2 text-body text-text-secondary">
            <Spinner /> asking 20 questions — takes about a minute…
          </div>
        </SectionPanel>
      )}

      {finished && (
        <SectionPanel
          title={`Quiz result — ${finished.passed}/${finished.total} (${finished.fabricated} fabricated)`}
          bodyClassName="p-0"
        >
          <div className="max-h-72 overflow-auto">
            <table className="w-full border-collapse">
              <tbody>
                {(finished.results ?? []).map((r, i) => (
                  <tr key={i} className="border-b border-line last:border-b-0">
                    <td className="w-16 px-3 py-2 align-top">
                      <StatusBadge
                        tone={r.hit && !r.fabricated ? 'success' : r.fabricated ? 'danger' : 'attention'}
                        label={r.fabricated ? 'FAB' : r.hit ? 'hit' : 'miss'}
                      />
                    </td>
                    <td className="px-3 py-2 text-caption">
                      <p className="text-body text-text-primary">{r.q}</p>
                      <p className="mt-0.5 line-clamp-2" style={{ color: 'var(--ai-fg)' }}>
                        {r.answer}
                      </p>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="border-t px-4 py-2 text-micro" style={{ color: 'var(--ai-fg)' }}>
            Answers are model output — digits checked against the source facts.
          </p>
        </SectionPanel>
      )}

      <SectionPanel
        title={`Knowledge base${kb.data?.dataset ? ` · ${kb.data.dataset.name}` : ''}`}
        action={
          <>
            <input
              ref={fileInput}
              type="file"
              accept=".md,.txt"
              hidden
              onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])}
            />
            <Button variant="secondary" size="sm" onClick={() => fileInput.current?.click()} loading={uploading}>
              <FileUp size={14} /> Upload .md / .txt
            </Button>
            <Button variant="primary" size="sm"
              onClick={() => setWriting((w) => !w)}
              title="Write a document right here — no file needed">
              {writing ? 'Close writer' : <><PenLine size={14} /> Write a doc</>}
            </Button>
          </>
        }
        bodyClassName="p-0"
      >
        {notice && (
          <div className="px-4 pt-3">
            <GateBanner tone={notice.tone} title={notice.tone === 'danger' ? 'Failed' : 'Note'} meta={notice.text} />
          </div>
        )}

        {writing && (
          <div className="space-y-3 border-b border-line px-4 py-4">
            <p className="text-caption text-text-secondary">
              Write spec sheets or FAQs directly. Same-name documents replace the old version.
            </p>
            <input
              value={docName}
              onChange={(e) => setDocName(e.target.value)}
              placeholder="Document name, e.g. DG-60_spec (adds .md automatically)"
              aria-label="Document name"
              className="h-9 w-full max-w-md rounded-md border border-line bg-surface-card px-2.5 mono text-[13px] outline-none transition-colors focus:border-brand focus:ring-2 focus:ring-brand/20"
            />
            <textarea
              value={docText}
              onChange={(e) => setDocText(e.target.value)}
              rows={10}
              spellCheck={false}
              placeholder={'# Product name (SKU)\n\n- power: …\n- tank: …\n- noise: 70dB @ 7m\n\nFacts only — the agent may quote these verbatim; anything not written here will not be answered.'}
              className="mono w-full rounded-md border border-line bg-surface-card p-3 text-[13px] leading-relaxed outline-none transition-colors focus:border-brand focus:ring-2 focus:ring-brand/20"
            />
            <div className="flex justify-end gap-2">
              <Button variant="secondary" size="sm" onClick={() => setWriting(false)}>Cancel</Button>
              <Button variant="primary" size="sm" onClick={saveDoc}
                loading={savingDoc}
                disabled={!docName.trim() || !docText.trim()}>
                Save & index
              </Button>
            </div>
          </div>
        )}
        {!kb.data?.dataset && !kb.loading ? (
          <EmptyState message="No dataset yet — upload the first document to create it." />
        ) : (
          <DataTable
            columns={[
              ...DOC_COLUMNS,
              {
                key: 'actions',
                header: '',
                width: 60,
                render: (d) => (
                  <button
                    onClick={() => setDeleting(d)}
                    aria-label={`Delete ${d.name}`}
                    title="Delete"
                    className="rounded-md p-1.5 text-text-secondary transition-colors hover:bg-surface-subtle hover:text-[#B91C1C]"
                  >
                    <Trash2 size={15} strokeWidth={1.75} />
                  </button>
                ),
              },
            ]}
            rows={kb.data?.items ?? []}
            rowKey={(d) => d.id}
            loading={kb.loading}
            emptyMessage="Knowledge base is empty — upload spec sheets and FAQs."
          />
        )}
      </SectionPanel>
      <ConfirmDialog
        open={!!deleting}
        title="Delete this document?"
        body={
          <>
            <span className="mono text-[13px]">{deleting?.name}</span> will be removed
            from the knowledge base. The agent will no longer answer questions from it.
          </>
        }
        confirmLabel="Delete"
        onCancel={() => setDeleting(null)}
        onConfirm={remove}
      />
    </div>
  )
}

const DOC_COLUMNS: Column<KbDoc>[] = [
  { key: 'name', header: 'Document', render: (d) => <span className="mono text-[13px]">{d.name}</span> },
  {
    key: 'status',
    header: 'Indexing',
    width: 130,
    render: (d) => <StatusBadge tone={docTone(d.status)} label={d.status} />,
  },
]
