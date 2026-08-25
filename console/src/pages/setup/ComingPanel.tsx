import type { ReactNode } from 'react'
import { SectionPanel } from '../../components/ui/SectionPanel'

export function ComingPanel({
  milestone,
  children,
}: {
  milestone: string
  children?: ReactNode
}) {
  return (
    <SectionPanel title={`Ships in ${milestone}`}>
      <p className="text-body text-text-muted">
        {children ?? 'Planned — see docs/console-plan.md for the screen spec.'}
      </p>
    </SectionPanel>
  )
}
