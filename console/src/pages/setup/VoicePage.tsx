import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { glueApi } from '../../api/glue'
import { Button } from '../../components/ui/Button'
import { GateBanner } from '../../components/ui/GateBanner'
import { KeyValue, SectionPanel } from '../../components/ui/SectionPanel'
import { SkeletonRows } from '../../components/ui/Skeleton'
import { useAsync } from '../../lib/useAsync'

const ALWAYS_HUMAN = [
  'Complaints & anger — routed before anything else',
  'Payment terms & legal/contract language',
  'Discounts beyond the authority cap',
  'Classifier confidence < 0.7 on any intent',
  'Anything S2 pricing rules cannot compute (never a guessed price)',
]

export function VoicePage() {
  const samples = useAsync(() => glueApi.voiceSamples(), [])
  const [text, setText] = useState('')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (samples.data) setText(samples.data.text)
  }, [samples.data])

  async function save(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      await glueApi.voiceSave(text)
      setSaved(true)
      setTimeout(() => setSaved(false), 4000)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setSaving(false)
    }
  }

  if (samples.loading) {
    return (
      <div className="mx-auto max-w-3xl">
        <SkeletonRows rows={6} />
      </div>
    )
  }

  return (
    <form onSubmit={save} className="mx-auto max-w-3xl space-y-4">
      <SectionPanel
        title="Brand voice samples (O4-2)"
        action={
          <Button variant="primary" size="sm" type="submit" loading={saving}>
            Save
          </Button>
        }
        bodyClassName="p-4 space-y-3"
      >
        <p className="text-body text-text-secondary">
          Paste 5–10 real messages the client likes, verbatim, one per line,
          tagged by language + situation. These anchor the tone more than any
          rule. Saved into{' '}
          <span className="mono text-[13px]">dify/prompts/voice_guide.md</span>{' '}
          (config-as-code; a .bak lands next to every write).
        </p>
        {samples.error && (
          <GateBanner tone="danger" title="Load failed" meta={samples.error} />
        )}
        {saved && (
          <GateBanner tone="success" title="Samples saved" meta="voice_guide.md updated — backup written" />
        )}
        {error && <GateBanner tone="danger" title="Save failed" meta={error} />}
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={12}
          spellCheck={false}
          className="mono w-full rounded-md border border-line bg-surface-card p-3 text-[13px] leading-relaxed outline-none transition-colors focus:border-brand focus:ring-2 focus:ring-brand/20"
          placeholder={'[en / greeting] Hi! Thanks for reaching out — …\n[zh / quote] 您好，50kVA 静音机组报价如下…\n[id / complaint] Mohon maaf sekali, Bapak/Ibu…'}
        />
      </SectionPanel>

      <SectionPanel title="Always-human list (hardcoded)" bodyClassName="p-4">
        <KeyValue
          rows={ALWAYS_HUMAN.map((h) => [h.split(' — ')[0], h.includes(' — ') ? h.split(' — ')[1] : h])}
        />
        <p className="mt-3 text-caption text-text-muted">
          Not AI discretion — rule #3 of the appliance. This list never changes per client.
        </p>
      </SectionPanel>

      <SectionPanel title="Escalation holding replies (contract rule 8)" bodyClassName="p-4">
        <p className="text-body text-text-secondary">
          When handing off to a human the agent stays NEUTRAL: it never
          confirms, denies, or discusses the buyer's request, and never states
          capabilities beyond <span className="mono text-[13px]">facts</span>.
          One or two lines: needs personal attention + a colleague follows up
          here shortly.
        </p>
        <p className="mt-2 text-caption text-[#6D28D9]">
          This is the Tibet-travel fix — fabricated capabilities are the exact
          failure class the appliance exists to prevent.
        </p>
      </SectionPanel>
    </form>
  )
}
