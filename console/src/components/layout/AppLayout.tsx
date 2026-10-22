import {
  Activity,
  BarChart3,
  BookOpen,
  Calculator,
  ChevronLeft,
  FileText,
  LayoutDashboard,
  Library,
  LogOut,
  Megaphone,
  MessageSquare,
  Mic,
  Newspaper,
  QrCode,
  Rocket,
  Shield,
  Truck,
  TrendingUp,
  Users,
} from 'lucide-react'
import { useState } from 'react'
import type { ReactNode } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { spine } from '../../api/spine'
import { licenseApi } from '../../api/glue'
import { useAuth } from '../../auth/AuthContext'
import { T } from '../../i18n/en'
import { usePoll } from '../../lib/usePoll'

interface NavDef {
  to: string
  label: string
  icon: typeof Activity
  /** entitlement id — nav hidden when the license doesn't cover it */
  agent?: string
}

const SETUP_NAV: NavDef[] = [
  { to: '/connect', label: T.nav.connect, icon: QrCode },
  { to: '/catalog', label: T.nav.catalog, icon: BookOpen },
  { to: '/knowledge', label: T.nav.knowledge, icon: Library, agent: 'kb' },
  { to: '/pricing', label: T.nav.pricing, icon: Calculator, agent: 'quoting' },
  { to: '/voice', label: T.nav.voice, icon: Mic },
  { to: '/go-live', label: T.nav.goLive, icon: Rocket },
  { to: '/license', label: T.nav.license, icon: Shield },
]

const RUNTIME_NAV: NavDef[] = [
  { to: '/', label: T.nav.home, icon: LayoutDashboard },
  { to: '/inbox', label: T.nav.inbox, icon: MessageSquare },
  { to: '/quotes', label: T.nav.quotes, icon: FileText },
  { to: '/customers', label: T.nav.customers, icon: Users },
  { to: '/positioning', label: T.nav.positioning, icon: TrendingUp, agent: 'positioning' },
  { to: '/intel', label: T.nav.intel, icon: Newspaper, agent: 'market-intel' },
  { to: '/procurement', label: T.nav.procurement, icon: Truck, agent: 'supplier' },
  { to: '/social', label: T.nav.social, icon: Megaphone, agent: 'social' },
  { to: '/events', label: T.nav.events, icon: Activity },
  { to: '/reports', label: T.nav.reports, icon: BarChart3 },
]

function RailItem({
  def,
  collapsed,
  attention = false,
}: {
  def: NavDef
  collapsed: boolean
  attention?: boolean
}) {
  const Icon = def.icon
  return (
    <NavLink
      to={def.to}
      end={def.to === '/'}
      title={collapsed ? def.label : undefined}
      className={({ isActive }) =>
        `relative flex h-9 items-center gap-3 rounded-md px-3 text-body transition-colors duration-150 ${
          collapsed ? 'justify-center px-0' : ''
        } ${
          isActive
            ? 'bg-rail-hover font-medium text-white'
            : 'text-rail-text hover:bg-rail-hover hover:text-white'
        }`
      }
    >
      {({ isActive }) => (
        <>
          {isActive && (
            <span
              className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-full"
              style={{ background: 'var(--sidebar-active)' }}
              aria-hidden
            />
          )}
          <Icon size={18} strokeWidth={1.75} className="shrink-0" />
          {!collapsed && <span className="truncate">{def.label}</span>}
          {attention && (
            <span
              className={`h-2 w-2 shrink-0 rounded-full ${
                collapsed ? 'absolute right-2 top-1/2 -translate-y-1/2' : 'ml-auto'
              }`}
              style={{ background: 'var(--st-attention-dot)' }}
              aria-label="unread messages"
            />
          )}
        </>
      )}
    </NavLink>
  )
}

function RailGroup({
  label,
  items,
  collapsed,
  attentionFor,
}: {
  label: string
  items: NavDef[]
  collapsed: boolean
  attentionFor?: string
}) {
  return (
    <div className="mt-4 first:mt-1">
      {!collapsed && (
        <p className="mb-1.5 px-3 text-micro font-medium uppercase tracking-wide text-[#6b7280]">
          {label}
        </p>
      )}
      <nav className="flex flex-col gap-0.5" aria-label={label}>
        {items.map((d) => (
          <RailItem key={d.to} def={d} collapsed={collapsed}
            attention={attentionFor === d.to} />
        ))}
      </nav>
    </div>
  )
}

export function AppLayout({ children }: { children: ReactNode }) {
  const [collapsed, setCollapsed] = useState(false)
  const { pathname } = useLocation()
  const { signOut } = useAuth()
  const title = T.titles[pathname as keyof typeof T.titles] ?? ''
  // nav attention badge — light poll; the Threads page itself polls at 5s.
  // v1.2: pending escalations in the spine store, not chatwoot unread.
  const threads = usePoll(() => spine.listThreads('open'), 30_000)
  const unread = (threads.data?.items ?? []).filter((c) => c.escalation_tag).length
  // Phase 1: entitlement-aware nav — hide agents the license doesn't cover.
  // Fail-open display; the server still enforces (glue 403, spine untouched).
  const license = usePoll(() => licenseApi.state(), 30_000)
  const licAgents = license.data?.agents ?? []
  const licMode = license.data?.mode ?? 'open'
  const visible = (items: NavDef[]) =>
    items.filter(
      (d) =>
        !d.agent ||
        licMode !== 'licensed' ||
        licAgents.includes('*') ||
        licAgents.includes(d.agent),
    )

  return (
    <div className="flex h-screen overflow-hidden">
      <aside
        className={`flex shrink-0 flex-col justify-between py-4 transition-all duration-200 ${
          collapsed ? 'w-sidebar-collapsed' : 'w-sidebar'
        }`}
        style={{ background: 'var(--sidebar-bg)' }}
      >
        <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-2">
          <div className={`mb-3 flex items-center gap-2 ${collapsed ? 'justify-center' : 'px-1'}`}>
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-surface-card text-caption font-bold text-text-primary">
              MX
            </span>
            {!collapsed && (
              <span className="truncate text-card font-semibold text-white">Appliance</span>
            )}
          </div>
          <RailGroup label={T.nav.setup} items={visible(SETUP_NAV)} collapsed={collapsed} />
          <RailGroup label={T.nav.runtime} items={visible(RUNTIME_NAV)} collapsed={collapsed}
            attentionFor={unread > 0 ? '/inbox' : undefined} />
        </div>
        <div className="px-2 pt-2">
          <button
            onClick={() => setCollapsed((c) => !c)}
            aria-label="Collapse sidebar"
            title={collapsed ? 'Expand' : 'Collapse'}
            className={`flex h-9 w-full items-center gap-3 rounded-md text-rail-text transition-colors hover:bg-rail-hover hover:text-white ${
              collapsed ? 'justify-center px-0' : 'px-3'
            }`}
          >
            {collapsed ? (
              <ChevronLeft size={18} strokeWidth={1.75} className="rotate-180" />
            ) : (
              <>
                <ChevronLeft size={18} strokeWidth={1.75} />
                <span className="text-body">Collapse</span>
              </>
            )}
          </button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-line bg-surface-card pl-6 pr-4">
          <h1 className="truncate text-page font-semibold text-text-primary">{title}</h1>
          <div className="flex items-center gap-3">
            <button
              onClick={signOut}
              aria-label="Sign out"
              title="Sign out"
              className="rounded-md p-2 text-text-secondary transition-colors hover:bg-surface-subtle hover:text-text-primary"
            >
              <LogOut size={16} strokeWidth={1.75} />
            </button>
            <div className="flex items-center gap-2 border-l border-line pl-3">
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-wash text-caption font-semibold text-brand">
                OP
              </span>
              <span className="hidden text-body text-text-secondary lg:block">{T.app.role}</span>
            </div>
          </div>
        </header>
        <main className="min-h-0 flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  )
}
