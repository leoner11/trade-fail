import { useState } from 'react'
import { glueApi } from '../../api/glue'
import type { OrganRow, WaStatus } from '../../api/glue'
import { ConfirmDialog } from '../../components/ui/ConfirmDialog'
import { GateBanner } from '../../components/ui/GateBanner'
import { PointerChip } from '../../components/ui/PointerChip'
import { SectionPanel } from '../../components/ui/SectionPanel'
import { SkeletonBlock, Spinner } from '../../components/ui/Skeleton'
import { StatusBadge } from '../../components/ui/StatusBadge'
import { Button } from '../../components/ui/Button'
import type { Tone } from '../../lib/domain'
import { usePoll } from '../../lib/usePoll'

function waToneOf(state?: string): Tone {
  switch (state) {
    case 'open':
      return 'success'
    case 'connecting':
      return 'info'
    case 'close':
    case 'disconnected':
      return 'attention'
    default:
      return 'danger'
  }
}

const STEPS = [
  'Open WhatsApp on the phone that owns the number',
  'Settings → Linked devices → Link a device',
  'Point the camera at this QR (it refreshes every ~20s)',
]

export function ConnectPage() {
  const status = usePoll<WaStatus>(() => glueApi.waStatus(), 5000)
  const organs = usePoll<OrganRow[]>(() => glueApi.organs().then((r) => r.items), 15000)
  const [confirming, setConfirming] = useState(false)
  const [dropping, setDropping] = useState(false)

  const st = status.data?.state
  const connected = st === 'open'
  const qr = usePoll(() => glueApi.waQr(), 3000, !!status.data && !connected && st !== 'unreachable')

  async function dropSession() {
    setDropping(true)
    await glueApi.waLogout().catch(() => undefined)
    setDropping(false)
    setConfirming(false)
    status.refresh()
  }

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <SectionPanel
        title="WhatsApp"
        action={
          status.data ? (
            <StatusBadge tone={waToneOf(st)} label={st ?? ''} />
          ) : (
            <Spinner size={14} />
          )
        }
        bodyClassName="p-4 space-y-4"
      >
        {status.error && (
          <GateBanner tone="danger" title="Glue unreachable" meta={status.error} />
        )}
        {!status.error && connected && (
          <GateBanner
            tone="success"
            title="Session connected"
            meta={`Instance “${status.data?.instance}” is live — send a test message to your own number to confirm replies.`}
          />
        )}
        {!status.error && !connected && st !== 'unreachable' && (
          <>
            <div className="flex min-h-[280px] items-center justify-center rounded-lg border border-line bg-surface-card p-4">
              {qr.data?.qr ? (
                <img
                  src={qr.data.qr}
                  alt="WhatsApp linking QR code"
                  className="max-h-[260px] rounded-md border border-line"
                />
              ) : (
                <div className="flex items-center gap-2 text-body text-text-muted">
                  <Spinner /> Waiting for a QR from evo…
                </div>
              )}
            </div>
            <ol className="list-inside list-decimal space-y-1 text-body text-text-secondary">
              {STEPS.map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ol>
          </>
        )}
        {!status.error && st === 'unreachable' && (
          <GateBanner
            tone="danger"
            title="evo is not answering"
            meta={status.data?.detail}
          />
        )}
      </SectionPanel>

      <SectionPanel title="Danger zone" bodyClassName="p-4 flex items-center justify-between gap-4">
        <p className="text-body text-text-secondary">
          Log out the WhatsApp session. The bot stops replying until someone
          re-scans the QR above (&lt;5 min, see{' '}
          <span className="mono text-[13px]">runbooks/whatsapp-qr-rescan.md</span>).
        </p>
        <Button variant="danger" onClick={() => setConfirming(true)}>
          Log out session
        </Button>
      </SectionPanel>
      <ConfirmDialog
        open={confirming}
        busy={dropping}
        title="Log out WhatsApp session?"
        body={
          <>
            Instance <span className="mono text-[13px]">{status.data?.instance}</span> will
            disconnect. Buyers' messages go unanswered until someone re-scans the
            QR on this page.
          </>
        }
        confirmLabel="Log out"
        onCancel={() => setConfirming(false)}
        onConfirm={dropSession}
      />

      <SectionPanel title="Stack organs" bodyClassName="p-4">
        {organs.data ? (
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
            {organs.data.map((o) => (
              <PointerChip
                key={o.name}
                label={o.name}
                href={o.url}
                health={o.up ? 'up' : 'down'}
              />
            ))}
          </div>
        ) : (
          <SkeletonBlock height={64} />
        )}
        <p className="mt-3 text-caption text-text-muted">
          Pointers only — chatwoot stays the human inbox, postiz the publisher.
          This console never replaces an organ (X1).
        </p>
      </SectionPanel>
    </div>
  )
}
