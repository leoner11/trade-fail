# NaraHome ERP — Design System & Implementation Rules
### Internal Design Reference for MJCX Studio
### Version 1.0 — August 2026
### Derived from the Cooljek Design System v1.0, retuned for NaraHome's deep-green identity and ERP scope

---

## How to read this document

This is not a mood board. It is a **contract between the design intent and the code**. Every rule here maps to a Tailwind token, a component file, or a lint-able pattern in `NARAHOME/frontend/src`.

Two audiences:
- **Building a new screen** → read Philosophy, Color, Typography, Icons, Layout, then the relevant Component Pattern.
- **Fixing an existing screen** → jump to [Part 2: Migration](#part-2--migration-from-the-current-frontend). It lists exactly what is wrong today and the search-and-replace that fixes it.

The system is deliberately **small**. Three radii, six status colors, one accent, six type sizes. If a screen needs something outside this list, the screen is wrong, not the system.

---

# Part 1 — The System

## Design Philosophy

**Sophisticated but minimalistic. Information-dense but breathable. Techy but not tacky.**

NaraHome Powerline is a genset manufacturer. The people using this ERP are sales reps in the field, service managers running assembly lines, technicians on a QC checklist, drivers on a delivery route, and a director who wants one screen that tells him whether the month is going well. None of them want a pretty app. They want the number, the status, and the button that moves the job forward.

Think Meituan's delivery ops console, or a well-built Alipay merchant back office — a lot of information in one view, but every element earns its space. Clear hierarchy: what matters most is the loudest, supporting data is present but receded. No decoration for decoration's sake.

The system should feel like it was designed by engineers who care about aesthetics, not designers pretending to understand genset manufacturing. Every pixel should communicate: **this is a tool built by people who actually understand the workflow from prospek to serah-terima.**

### What we are NOT doing:
- ❌ Emoji as iconography (this is the single biggest polish problem in the current build)
- ❌ Generic AI placeholder avatars (grey silhouette heads)
- ❌ Cookie-cutter card layouts with rounded corners and drop shadows everywhere
- ❌ Icon-heavy empty states ("no data here" with a sad illustration)
- ❌ Overly colorful dashboards that look like a toy
- ❌ Gradients on buttons or headers
- ❌ Glassmorphism, neumorphism, or any trendy effect
- ❌ Stock illustration style (Undraw, Storyset, etc.)
- ❌ Excessive whitespace that makes the app feel empty
- ❌ Cards used to list data — that is what tables are for

### What we ARE doing:
- ✅ Tight, purposeful layouts — dense like Chinese super apps but with clear visual hierarchy
- ✅ Monochrome-forward with a single accent color (Powerline Orange) reserved for actions
- ✅ Tables and lists that feel like a real operations tool, not a consumer app
- ✅ Map views that dominate the screen when GPS data is the point (Lacak Sales, Pengiriman)
- ✅ Status indicators that are functional (small colored dots or tags), never decorative
- ✅ Typography doing the heavy lifting — size, weight, and spacing create hierarchy, not color
- ✅ One consistent icon language (Lucide, outlined, 1.75px stroke)
- ✅ Quiet confidence — the UI doesn't try hard, it just works

### The one philosophical difference from Cooljek

Cooljek is a delivery ops tool: a handful of screens, one core loop, map-heavy. **NaraHome ERP is a 4-phase pipeline plus 3 side streams** — Prospecting → Pipeline/Penawaran → Produksi/Pengiriman → Registry/Garansi, plus Sparepart, Sparepart+Service, and Laser Cutting. Dozens of screens, dozens of FSM states, eleven roles.

That scale changes one thing: **consistency matters more than cleverness here.** A bespoke beautiful screen that doesn't match the other forty is worse than a plain screen that does. When in doubt, reuse the pattern.

---

## Color Palette

### Brand

NaraHome's identity is a deep forest green on a green-black rail, taken from the NaraHome Pamulang wordmark. The brand colour is **strictly an action colour** and never doubles as a status colour — the palette already owns a bright emerald for `status-success`, and a primary button in a similar green would read as "done" rather than "do". The brand green is therefore deliberately darker and less saturated (L 18%, S 43%) than `status-success` (L 29%, S 72%).

| Role | Token | Hex | Usage |
|---|---|---|---|
| **NaraHome Green** | `brand-primary` | `#1B4332` | Primary buttons, focus rings, links, selected states, brand marks. 11.08:1 on white both ways |
| **Green Hover** | `brand-primary-hover` | `#123125` | Hover state on primary buttons only |
| **Green Wash** | `brand-primary-wash` | `#EDF5F1` | Selected table row, active filter chip background, active tab underline bed |
| **Ink Green** | `sidebar-bg` | `#10231A` | Sidebar, dark surfaces |
| **Mint** | `sidebar-active` | `#4FBF8F` | Active nav marker **on the dark rail only** — `brand-primary` is near-invisible there |
| **Ink Green Raised** | `sidebar-hover` | `#1C3A2C` | Sidebar hover, nested dark surfaces |
| **Ink Navy Text** | `sidebar-text` | `#A0AEC0` | Sidebar inactive labels |

**Rule: the brand green never means "success".** Keep `brand-primary` and `status-success` visually apart — that is the green-on-green version of Ducotti's orange bug, where `status-orange` and `brand-primary` shared a hex and "menunggu approval" looked identical to "click me". Pending is amber (`#B45309`).

### Surface

| Role | Token | Hex | Usage |
|---|---|---|---|
| **Canvas** | `surface-base` | `#F8F9FA` | App background behind cards, main content area |
| **Card** | `surface-card` | `#FFFFFF` | Cards, panels, table body, modals, inputs |
| **Subtle** | `surface-subtle` | `#F1F3F5` | Table headers, hover rows, disabled inputs, inactive tabs |
| **Line** | `line` → class `border-line` | `#E5E7EB` | **All** borders — card outlines, input borders, table dividers |
| **Line Strong** | `line-strong` → class `border-line-strong` | `#D1D5DB` | Input borders on focus-adjacent elements, dividers that need to read |

> The color key is `line`, not `border-line` — Tailwind prefixes the utility, so a key of `border-line` would produce the class `border-border-line`.

> `border-line` is deliberately `#E5E7EB` — the exact value of Tailwind's `gray-200`, which the codebase already uses 187 times. Migrating `border-gray-200` → `border-line` is therefore a **pure rename with zero visual change**, and it gives us one place to retune every border in the app later.

### Text

| Role | Token | Hex | Contrast on white | Usage |
|---|---|---|---|---|
| **Primary** | `text-primary` | `#111827` | 16.9:1 | Headings, labels, table data, critical values |
| **Secondary** | `text-secondary` | `#5B6472` | 6.5:1 | Descriptions, supporting info, timestamps, table meta |
| **Muted** | `text-muted` | `#8A929E` | 3.6:1 | Placeholders, disabled, metadata. **Never for data the user must read.** |
| **Inverse** | `text-inverse` | `#FFFFFF` | — | Text on dark-green/brand backgrounds |

> `text-secondary` moves from `#6B7280` to `#5B6472` and `text-muted` from `#9CA3AF` to `#8A929E`. Both are small darkenings that push secondary text over 4.5:1 and stop muted text from disappearing on `surface-subtle`. Visually near-identical; legally and practically better.

### Status Colors — the functional palette

Every status color has **three** values, because a status appears in three forms: a dot, a tag wash, and text. Using one hex for all three is what makes the current badges fail contrast.

| Role | Meaning in NaraHome | `-dot` (marker) | `-wash` (tag bg) | `-fg` (text) |
|---|---|---|---|---|
| **Neutral** | Draft, belum mulai, arsip, tidak berlaku | `#9CA3AF` | `#F3F4F6` | `#4B5563` |
| **Info** | Sedang berjalan, dalam proses, in transit, aktif | `#3B82F6` | `#EFF6FF` | `#1D4ED8` |
| **Attention** | Menunggu approval, perlu tindakan, mendekati jatuh tempo | `#F59E0B` | `#FFFBEB` | `#B45309` |
| **Success** | Selesai, disetujui, lulus QC, lunas, terkirim | `#22C55E` | `#F0FDF4` | `#15803D` |
| **Danger** | Ditolak, gagal QC, overdue, batal, stok habis | `#EF4444` | `#FEF2F2` | `#B91C1C` |
| **Special** | Garansi, klaim, rework, kondisi luar-alur | `#8B5CF6` | `#F5F3FF` | `#6D28D9` |

**Rules:**
- Status colors ONLY for status. Never as decorative fills, never as chart series accents, never as section headers.
- Maximum **two** colors visible in any single component (brand green + one status, or two statuses in a comparison row).
- No color fills on cards. Cards are `#FFFFFF` with `1px solid #E5E7EB`.
- Dark sidebar `#10231A` with light text — flat, no gradient, no texture.
- **Never encode meaning in color alone.** Every status tag carries a text label. Every dot has a label beside it. Colorblind users and greyscale prints must still work.

### Deterministic avatar colors

For user/rep/technician avatars — colored initials on a circle, never a silhouette:

```
Avatar = circle (28px table / 32px header / 40px detail) + up to 2 initials
Background = deterministic from full_name:

  #1B4332  brand green  #3B82F6  blue        #22C55E  status green
  #8B5CF6  violet       #EC4899  pink        #06B6D4  cyan
  #F59E0B  amber

Assignment: hash(full_name) % 7
Text: #FFFFFF, weight 600, size = circle × 0.4
```

Customers/companies use a **neutral** avatar — first initial, `#F1F3F5` background, `#5B6472` text. Customers are less visually important than staff in an internal ops tool.

The existing `getInitials()` in `src/utils/formatters.ts` already produces the initials; only the color hash needs adding.

---

## Typography

### Font Stack

```
Primary:     'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif
Monospace:   'JetBrains Mono', 'SF Mono', 'Fira Code', Consolas, monospace
```

Inter is already loaded via Google Fonts in `index.html` with weights 400/500/600/700. That's correct and stays. Monospace uses the system stack — no extra web font.

### The root font-size decision

**This is the highest-impact fix in this document.**

The current build sets `html { font-size: 14px }` *and* uses Tailwind's default rem-based scale. Because Tailwind sizes are rem, everything silently shrinks by 12.5%:

| Class | Intended | Actual today |
|---|---|---|
| `text-xs` | 12px | **10.5px** |
| `text-sm` | 14px | **12.25px** |
| `text-base` | 16px | 14px (overridden to 14px anyway) |
| `text-xl` | 20px | **17.5px** |
| `p-4` | 16px | **14px** |
| `gap-2` | 8px | **7px** |

That is why the app reads as cramped and slightly off — it isn't a deliberate density choice, it's an accident compounding across every screen. Sub-11px text is also below the practical legibility floor for Indonesian text on a 1080p office monitor.

**Decision: root goes to `16px`, and the type scale is redefined in absolute `px`.** Spacing utilities then mean what the Tailwind docs say (`p-4` = 16px), and font sizes are locked to the scale below regardless of root.

**Migration risk:** every existing screen grows ~14% in padding and gaps. This is a one-time, visually obvious change — do it in a single commit, walk the main screens, and tighten any panel that now overflows. It is not a change to make on a Friday. See [Migration Step 1](#step-1--fix-the-root-font-size-half-a-day-highest-impact).

### Scale

| Level | Size | Weight | Line height | Usage |
|---|---|---|---|---|
| **Data XL** | 24px | 600 | 32px | KPI numbers, the single figure a card exists to show — class `text-data` |
| **Page title** | 20px | 600 | 28px | "Pipeline Penjualan", "Registry Unit" — class `text-page` |
| **Section title** | 16px | 600 | 24px | "Follow-up Hari Ini", "Detail Assembly", modal titles — class `text-section` |
| **Card title** | 14px | 600 | 20px | Customer name, deal name, technician name — class `text-card` |
| **Body** | 14px | 400 | 22px | Table cells, descriptions, form values |
| **Caption** | 12px | 400 | 18px | Timestamps, helper text, secondary metadata |
| **Micro** | 11px | 500 | 16px | Table column headers, status tag text, field labels (uppercase) |

### Rules
- **No text larger than 24px anywhere**, and 24px only for a KPI figure. This is an ops tool, not a landing page.
- Weight `600` creates hierarchy. Never bold inside a body paragraph for emphasis — use a tag or color instead.
- **Monospace for anything ID-shaped**: serial number, nomor penawaran, kode unit, PO number, tracking coordinates, API references. Monospace is a signal that the string is exact and copyable.
- **Numbers in tables are right-aligned**, tabular figures (`font-variant-numeric: tabular-nums`), and currency is always `formatCurrency()` → `Rp 1.250.000.000`. Never render a raw number for money.
- Dates are always `formatDate()` / `formatDateTime()` → WIB, `09 Agu 2026`. Never ISO strings in the UI.
- **Indonesian throughout.** English only for terms that don't translate naturally: dashboard, tracking, approval, invoice, QC, kVA. Never mix within one label.
- Uppercase (`tracking-wide`) is reserved for **Micro** level only — field labels and table headers. Never uppercase a sentence.

---

## Icons

### Style: Lucide, outlined, 1.75px stroke

**Adopt `lucide-react`.** Today the app has no icon library: sidebar nav renders the first letter of each label, and emoji stand in for icons across 73 files. Emoji render differently on every OS, can't be recolored, don't respect stroke weight, and read as unfinished. This is the fastest visible upgrade available.

```bash
npm install lucide-react
```

### Rules
- **Line style only.** Filled icons only for the active/selected navigation item, if at all.
- Sizes: **18px** sidebar nav · **16px** inline beside a label or in a button · **14px** inside table rows and tags
- Stroke width: `1.75` everywhere. Set once in a wrapper, not per-icon.
- Color: `text-secondary` (`#5B6472`) by default, `brand-primary` when active/interactive, status `-fg` when semantic.
- Icons are **never the primary element of an empty state.**
- Icons **never appear inside status tags.** Dot + text only.
- Every icon-only button needs `aria-label` and a `title`.

### Emoji → Lucide mapping

Replace these exactly. Full list of affected files in [Migration Step 3](#step-3--adopt-lucide-and-delete-every-emoji-2-3-days-most-visible).

| Current | Where | Lucide |
|---|---|---|
| `📍` KUNJUNGAN | `InteractionIcon.tsx` | `MapPin` |
| `📞` TELEPON | `InteractionIcon.tsx` | `Phone` |
| `💬` WHATSAPP | `InteractionIcon.tsx` | `MessageCircle` |
| `📧` EMAIL | `InteractionIcon.tsx` | `Mail` |
| `&#128269;` 🔍 | `SearchInput.tsx` | `Search` |
| `✓ ✕ ⚠ ℹ` | `Toast.tsx` | `CheckCircle2` `XCircle` `AlertTriangle` `Info` |
| `‹ ›` | `Sidebar.tsx` collapse | `ChevronLeft` `ChevronRight` |
| `↩` | `Sidebar.tsx` logout | `LogOut` |
| `×` | `Modal.tsx` close | `X` |
| `▲ ▼` | KPI deltas | `TrendingUp` `TrendingDown` |
| `▲ ▼` | expand/collapse rows | `ChevronUp` `ChevronDown` |
| `📷` | media/POD/foto | `Camera` |
| `📄` | dokumen rows | `FileText` |

### Second wave — emoji in action labels

These sit to the left of a button or action label. Same rules (16px, stroke 1.75, 6px gap).

| Emoji | Lucide | Emoji | Lucide |
|---|---|---|---|
| `🖨️` Cetak/Print | `Printer` | `📎` Lampiran/PO | `Paperclip` |
| `👁` Preview | `Eye` | `📥` Import | `FileUp` |
| `📤` Export | `FileDown` | `📋` Checklist | `ClipboardList` |
| `🔧` `🛠` Servis | `Wrench` | `📦` Sparepart/unit | `Package` |
| `📊` Laporan | `BarChart3` | `💳` Pembayaran | `CreditCard` |
| `✂` Laser cutting | `Scissors` | `🧮` Hitung/BQ | `Calculator` |
| `🏭` Produksi | `Factory` | `🚧` Dalam proses | `Construction` |
| `🗄` Arsip | `Archive` | `🕒` Jadwal/riwayat | `Clock` |
| `🔌` Genset/daya | `Zap` | `📱` Aplikasi mobile | `Smartphone` |
| `📅` Tanggal | `Calendar` | `🔔` Pengingat | `Bell` |
| `🔒` Terkunci | `Lock` | `🔄` Muat ulang | `RefreshCw` |
| `📭` Kosong | `Inbox` | `✓` `✕` **on a button** | `Check` `X` |

**The action-vs-state test.** `✓` and `✕` appear in both roles, and they are handled by different migration steps:

| | Example | Step |
|---|---|---|
| **Action** — the user clicks it | `✓ Setujui`, `✓ Tugaskan Teknisi`, `✕ Tutup` | **3b** — becomes a Lucide icon in a `Button` |
| **State** — the system reports it | `✓ QC Lulus`, `✓ Terverifikasi`, `🟠 Menunggu` | **5** — becomes a `StatusBadge` dot + tone |

If it is wrapped in a `<button>` or an `onClick`, it is an action. If it is coloured by a `text-status-*` class, it is a state. Never convert a state glyph in isolation — the glyph and its tone must move together or the badge ends up half-migrated.

### Nav icon assignment

`NavItem.icon` already exists in `src/types` and is populated in `src/utils/constants.ts` (`'dashboard'`, `'people'`, `'description'`…) — it's simply never read. Map those strings to Lucide components in one lookup and render them in `Sidebar.tsx`:

| Nav | Icon | Nav | Icon |
|---|---|---|---|
| Dashboard | `LayoutDashboard` | Produksi / Proyek | `Factory` |
| Dashboard Direksi | `TrendingUp` | Pengiriman | `Truck` |
| Pelanggan Saya | `Users` | Registry Unit | `Server` |
| Penawaran | `FileText` | Maintenance | `Wrench` |
| Pipeline | `GitBranch` | Klaim Garansi | `ShieldCheck` |
| Kunjungan | `MapPin` | Stok | `Package` |
| Lacak Sales | `Navigation` | Katalog | `BookOpen` |
| Approval | `CheckSquare` | Email | `Mail` |
| Laporan Keuangan | `Wallet` | Streams B/C/D | `Boxes` `Headset` `Scissors` |

---

## Layout

### Desktop shell

```
┌────────────────────────────────────────────────────────────┐
│ ┌────────┐ ┌───────────────────────────────────────────────┐│
│ │        │ │ Top Bar (56px)                                ││
│ │        │ │ Page title · breadcrumb   |   search  🔔  AV  ││
│ │ Side-  │ ├───────────────────────────────────────────────┤│
│ │ bar    │ │                                               ││
│ │        │ │ Main Content Area                             ││
│ │ 240px  │ │ Padding: 24px                                 ││
│ │ fixed  │ │ Background: #F8F9FA                           ││
│ │ ↕ 64px │ │                                               ││
│ │        │ │ Cards · tables · maps · two-column detail     ││
│ │ #10231A│ │                                               ││
│ └────────┘ └───────────────────────────────────────────────┘│
└────────────────────────────────────────────────────────────┘
```

### Sidebar
- **240px fixed**, collapsible to **64px** icon-only. Both widths already exist as `w-sidebar` / `w-sidebar-collapsed`. Keep.
- Background `#10231A` solid. No gradient, no texture.
- Logo: `narahome-logo.png` on a white chip — the mark is solid black on transparent, so it needs the chip against the dark rail. Collapsed shows a compact green "N" mark.
- Nav item: 18px Lucide icon + 14px label, `#A0AEC0` default, `#FFFFFF` on hover with `#1C3A2C` background.
- **Active item**: 2px left border in `sidebar-active` (`#4FBF8F`), label turns white, background `#1C3A2C`. One visual treatment, applied consistently.
- Role-filtered nav is already implemented via `NAV_ITEMS[].roles` — keep. A user must never see a nav item they'll get a 403 from.
- Grouped sections (once the nav exceeds ~10 items): 11px uppercase label in `#6B7280`, 16px top margin. Group as **Penjualan · Produksi · Layanan · Data · Sistem**.
- Badge for pending counts: `status-danger` dot with count, right-aligned. Already implemented — keep.
- **No hover animation beyond the 150ms color transition.** No slide, no scale.

### Top Bar
- **56px height**, `#FFFFFF`, bottom border `1px solid #E5E7EB`.
- **Left: the page title.** Today `Header` accepts a `pageTitle` prop that `AppLayout` never passes, so the bar is 56px of empty space with an avatar. Either wire it up via a small `usePageTitle()` store or route metadata, or delete the bar and let `PageHeader` own the title. **Wire it up** — a persistent title bar is worth it once detail panels start scrolling independently.
- Right: global search (⌘K, optional v1.1), notification bell with a `status-danger` dot when unread, then the user avatar + role label.
- Breadcrumbs only at 3+ levels deep (e.g. Proyek › PRJ-0142 › Test Load).

### Content Area
- Background `#F8F9FA`, padding `24px` (the existing `p-card` token).
- **No max-width.** This is an ops tool — use the monitor.
- Gap between cards/sections: `16px` (`gap-section`).
- Cards: `#FFFFFF`, `1px solid #E5E7EB`, `8px` radius, **no shadow**.

### The two-column list + detail pattern

This is the signature NaraHome layout — used by Pipeline, Pelanggan, Streams B/C/D, Proyek, Registry Unit, Klaim. `TwoColumnLayout.tsx` already implements it well (45/55 split with a collapse toggle on the divider). Formalize it:

```
┌───────────────────────────┬──────────────────────────────────┐
│ LIST PANEL  45%           │ DETAIL PANEL  55%                │
│                           │                                  │
│ PageHeader + actions      │ Entity title + status tag        │
│ SearchInput               │ ── tabs ─────────────────        │
│ FilterChips               │                                  │
│ ─────────────────────     │ Tab content, scrolls             │
│ ▸ row (selected: green    │ independently of the list        │
│   wash + 2px left border) │                                  │
│ ▸ row                     │                                  │
│ ▸ row                     │ Sticky action bar at the bottom  │
│   scrolls independently   │ when the tab has a primary CTA   │
└───────────────────────────┴──────────────────────────────────┘
                            ↑ collapse toggle on the divider
```

- The two panels scroll **independently**. Neither scrolls the page.
- The selected row gets `brand-primary-wash` background + 2px left `brand-primary` border. Not a full green fill.
- Selection is reflected in the URL (`/pipeline/:dealId`) so it's shareable and survives refresh. Already done in `PipelineList` — do it everywhere.
- Below 1280px viewport: the detail panel becomes a full-screen overlay with a back button rather than squeezing to 300px.
- Empty detail panel: one line of `text-muted`, vertically centered — "Pilih deal untuk melihat detail." No illustration.

---

## Component Patterns

### 1. Tables — the backbone

NaraHome is a table-first application. Tables are where the density philosophy earns its keep. **21 files currently hand-roll `<table>` markup while only 3 use `DataTable`** — that divergence is the single biggest source of visual inconsistency in the app.

**Rule: no raw `<table>` in a page file.** If `DataTable` can't do it, extend `DataTable`.

```
┌──────────────────────────────────────────────────────────────────────┐
│ PELANGGAN         KVA      NILAI          STATUS         UPDATE      │ ← 11px upper, #5B6472, bg #F1F3F5
├──────────────────────────────────────────────────────────────────────┤
│ PT Sinar Abadi    250      Rp 1.250.000.000  ● Negosiasi   09 Agu    │ ← 14px, #111827, bg #FFFFFF
│ CV Karya Mandiri  100      Rp   485.000.000  ● Survey      08 Agu    │   hover → #F1F3F5
│ PT Griya Nusa     500      Rp 2.100.000.000  ● PO Diterima 07 Agu    │
└──────────────────────────────────────────────────────────────────────┘
```

- Row height `48px`; `56px` only if a row carries an avatar + two lines
- Header: `11px`, uppercase, `#5B6472`, `letter-spacing: 0.5px`, background `#F1F3F5`, sticky on scroll
- Cell padding `12px 16px`
- Row hover: background → `#F1F3F5`. Subtle. No transform, no shadow, no border color change.
- **No alternating row colors.** Borders and hover only.
- Numeric and currency columns right-aligned with tabular figures
- Status column: dot + label tag (see below), never a colored row background
- Clickable rows: `cursor-pointer`, no underline; click opens the detail panel, not a new page
- Empty: `EmptyState`, one line, no illustration
- Loading: **skeleton rows**, not a centered spinner. A spinner where a table will appear causes a layout jump; 5 grey skeleton rows at the real row height do not.
- Long tables paginate at 50 rows with a simple `‹ 1 2 3 ›` control — never infinite scroll on desktop

**`DataTable` needs these additions to absorb the 21 hand-rolled tables:** column alignment (`align: 'left' | 'right'`), column width, sticky header, skeleton loading, row selection state, and a `footer` slot for totals.

### 2. Status tags

The most-used component in the app — 53 files import `StatusBadge`.

```
┌──────────────┐
│ ● Negosiasi  │   height 22px · radius 4px · padding 2px 8px
└──────────────┘   bg = status -wash · text = status -fg · dot = status -dot
```

- Height `22px`, radius `4px`, padding `2px 8px`, text `11px/500`
- Dot: `6px` circle, `-dot` color, `6px` right margin
- **No border, no icon, no gradient.** Dot + text.
- Always a text label. Never a bare colored dot with no label in a table cell.

**The taxonomy problem.** `StatusBadge`'s map currently holds ~30 generic English keys (`active`, `pending`, `done`) while the ERP's real states are Indonesian FSM values across a dozen apps — `AWAITING_SURVEY_APPROVALS`, `READY_DELIVERY`, `LUNAS`, `REWORK`, `TIDAK_TERCOVER`. Anything unmapped falls through to grey, which is why so many pages hand-roll their own pill classes.

**Fix:** invert the model. `StatusBadge` should take a **semantic tone**, not guess from a string:

```tsx
<StatusBadge tone="attention" label={STAGE_LABELS[deal.stage]} />
```

Each domain owns its own `STAGE → tone` map next to its labels — `types/deals.ts` already has `STAGE_LABELS` and `STAGE_BADGE_STATUS`, which is exactly the right shape. Replicate that for projects, units, claims, streams, stock, payment. The mapping lives with the domain; the component stays dumb. Keep the old string-guessing signature as a deprecated fallback so the migration can be incremental.

Tone assignment guide:

| Tone | Assign when the state means… |
|---|---|
| `neutral` | Nothing is happening yet or ever again — draft, arsip, batal, belum mulai |
| `info` | Work is actively in progress and on track |
| `attention` | **A human must do something.** Approval pending, dokumen kurang, jatuh tempo dekat |
| `success` | Terminal and good — selesai, disetujui, lunas, lulus |
| `danger` | Terminal and bad, or overdue — ditolak, gagal, overdue, habis |
| `special` | Outside the happy path — garansi, klaim, rework |

`attention` is the most important tone in this system. It is the color of "your queue has something in it."

### 3. Buttons

Four variants, three sizes. `Button.tsx` already has the right shape — it needs its styles retuned and, more importantly, **enforcement**: there are 126 raw `<button>` elements against 83 files importing `Button`.

| Variant | Style | Usage |
|---|---|---|
| **primary** | `#1B4332` bg, white text, no border, no shadow | **One per screen section.** "Simpan", "Kirim Penawaran", "Selesaikan QC" |
| **secondary** | `#FFFFFF` bg, `#111827` text, `1px solid #E5E7EB` | Everything else. "Batal", "Filter", "Export" |
| **ghost** | transparent, `#5B6472` text, no border | Tertiary actions, table row actions, toolbar icons |
| **danger** | `#EF4444` bg, white text | Destructive only, and always behind `ConfirmDialog` |

| Size | Height | Padding | Text |
|---|---|---|---|
| `sm` | 28px | `0 10px` | 12px/500 |
| `md` | 36px | `0 16px` | 14px/500 |
| `lg` | 44px | `0 20px` | 14px/600 |

- Radius `6px` (`rounded-md`) for all sizes
- **Remove `shadow-sm` from primary and danger.** Buttons in this system do not float.
- Hover: darken background 6%. That's it. No lift, no scale, no shadow, no color change on secondary beyond `#F1F3F5`.
- Focus: `2px` `brand-primary` ring at 40% opacity, `2px` offset. Never remove focus rings.
- Icons in buttons: 16px, left of the label, 6px gap — only when the icon adds meaning (`Plus`, `Download`, `Send`). Icon-only buttons need `aria-label`.
- Disabled: 45% opacity, `cursor-not-allowed`. Where the reason isn't obvious, wrap in a tooltip explaining why — "Lengkapi checklist QC dulu" beats a dead grey button.
- Loading: spinner replaces the icon, label stays, button disabled. Already implemented — keep.

### 4. Cards and panels

Three distinct things that all look like "a card" today:

**KPI tile** — a number and its label. Max 4 per row.
```
┌────────────────────┐
│ Deal Aktif         │  label  12px #5B6472
│ 18                 │  value  24px/600 #111827
│ ▲ 3 dari bulan lalu│  delta  12px, success/danger -fg
└────────────────────┘
```
No icon. No colored background. The number is the content.

**Section panel** — a titled container for a form, a table, or a list.
```
┌────────────────────────────────────────┐
│ Detail Assembly              [Ubah]    │ ← 16px/600 + optional action, 12px 16px padding
├────────────────────────────────────────┤ ← 1px #E5E7EB
│ content, 16px padding                  │
└────────────────────────────────────────┘
```

**Key-value block** — for entity attributes. Label left `12px #5B6472`, value right `14px #111827`, 8px row gap, no borders between rows. Two columns on wide panels, one on narrow.

All three: `#FFFFFF`, `1px solid #E5E7EB`, `8px` radius, **no shadow**.

### 5. Tabs

Used heavily in detail panels (`DealDetailTabs`, `projects/tabs`, `units/tabs`, `streams/*/tabs`).

- Underline style. Active: `#111827` text, `2px` `brand-primary` bottom border. Inactive: `#5B6472`, no border, hover → `#111827`.
- Height `40px`, gap `24px`, text `14px/500`, container bottom border `1px #E5E7EB` spanning the full width.
- Counts in tabs: `(3)` in `text-muted` after the label, not a colored badge — unless the count is an action queue, in which case a `attention` dot.
- Tab state belongs in the URL when the tab is a real sub-view.
- **Never more than 7 tabs.** Beyond that the entity needs splitting.

### 6. Forms and inputs

| Property | Desktop | Mobile web |
|---|---|---|
| Height | 36px | 48px |
| Font | 14px | 16px (prevents iOS zoom on focus) |
| Padding | `0 12px` | `0 14px` |
| Radius | 6px | 6px |
| Border | `1px solid #E5E7EB` | same |
| Focus | `1px solid #1B4332` + 2px green ring at 20% | same |
| Error | `1px solid #EF4444`, message below in `11px danger-fg` | same |

- Label **above** the input, `11px/500` uppercase `#5B6472`, 4px gap. `FormField.tsx` already does this — keep and use it everywhere.
- Required marker: `*` in `danger-dot` after the label.
- Placeholders describe format, never repeat the label: `"cth. 250"` not `"Masukkan kVA"`.
- Helper text `12px #8A929E` below the field; it is replaced by the error message when invalid, never stacked.
- **Validate on blur, not on keystroke.** Nobody wants to be told their email is invalid while typing it.
- Currency inputs: prefix `Rp` inside the field, thousands separators live, right-aligned.
- Numeric fields with units (kVA, jam, km): unit as a static suffix inside the field.
- Form actions: bottom-right, `[Batal] [Simpan]`, primary rightmost. Long forms get a sticky action bar with a top border.

### 7. Modals, dialogs, sheets

- Overlay `rgba(17, 24, 39, 0.45)`. **Remove `backdrop-blur-sm`** from `Modal.tsx` — blur costs a compositing layer on every open and reads as consumer-app trendy.
- Container: `#FFFFFF`, `10px` radius, `max-width: 560px` (or `720px` for form-heavy), shadow `0 12px 32px rgba(17,24,39,0.16)`.
- Title `16px/600`, close button is a 16px `X` in `ghost` styling top-right.
- Footer: top border `1px #E5E7EB`, actions right-aligned, `[Batal] [Konfirmasi]`.
- Radix Dialog is already the base — good, keep it. Focus trap and Esc come free.
- **Destructive confirmations** (`ConfirmDialog`) must name the object and the consequence: "Hapus penawaran QT-2026-0042? Tindakan ini tidak bisa dibatalkan." — not "Apakah Anda yakin?"
- On mobile web, modals become bottom sheets: `16px` top radius, `40×4px` drag handle in `#E5E7EB`, full-width stacked buttons with primary on top.

### 8. Toasts

- Position top-right, `320px` wide, stacked with 8px gap, max 3 visible.
- **Restyle from the current solid-color fill to a white card:** `#FFFFFF` background, `1px solid #E5E7EB`, `4px` left border in the status `-dot` color, 16px Lucide icon in `-fg`, text `#111827`. A wall of saturated green is loud; a white card with a green edge reads as professional and is far more legible.
- Auto-dismiss: success 4s, info 5s, error **never** — errors require an explicit close so the user can read the reason.
- Errors carry the actual backend message via `ApiError` (already the pattern in `PipelineList`) — never "Terjadi kesalahan" when the API told you what went wrong.
- Toasts are for **outcomes**, not progress. Progress belongs to the button's loading state.

### 9. Empty and loading states

**Empty:** one line of `#8A929E`, centered, `14px`, plus a primary button if there's an obvious next action. No icon, no illustration, no heading + subheading pair.

```
        Belum ada kunjungan minggu ini.

              [ Catat Kunjungan ]
```

Write the specific empty message — "Belum ada deal di tahap Negosiasi." beats "Tidak ada data."

Distinguish the three empty cases, because they need different words:
- **Nothing exists yet** → invite the action: "Belum ada pelanggan. Tambah pelanggan pertama."
- **Filters excluded everything** → offer the escape: "Tidak ada hasil untuk filter ini. [Reset filter]"
- **Load failed** → state it and offer retry: "Gagal memuat data. [Coba lagi]" — never render an error as an empty state.

**Loading:**
- Tables and lists → **skeleton rows** at the real row height
- KPI cards → skeleton block at the real card height
- Detail panels → skeleton of the key-value layout
- Spinner **only** for in-button loading and full-page route transitions
- Never a spinner where content will appear — it guarantees a layout jump

### 10. Timeline

Used in interaction history, deal activity, project timeline, stream timeline.

```
 ●───  Penawaran dikirim                      09 Agu 2026, 14:32
 │     QT-2026-0042 · Rp 1.250.000.000
 │     Budi Santoso
 │
 ●───  Survey disetujui Service Manager       08 Agu 2026, 09:15
 │     Catatan: "Lokasi butuh crane"
 │
 ○───  Menunggu approval Sales Head           —
```

- 2px vertical connector in `#E5E7EB`, dots `10px` on the line
- Completed: solid `-dot` color · Current: `brand-primary`, subtle CSS pulse · Future: hollow, `1.5px #E5E7EB` border
- Event title `14px/500 #111827`, meta `12px #5B6472`, timestamp right-aligned `12px #8A929E`
- Actor shown as a 20px initials avatar + name, never a silhouette
- Group by day with a sticky `11px` uppercase day divider when a timeline exceeds ~15 entries

### 11. FSM stage rail

NaraHome's pipeline and production stages are long finite state machines. Give them a horizontal rail above the detail tabs so the user always knows where the entity sits:

```
 ✓ Survey ──── ✓ BQ/DQ ──── ● Negosiasi ──── ○ PO ──── ○ Produksi ──── ○ Kirim
```

- Completed: `success-dot` fill + `Check` icon, label `#111827`
- Current: `brand-primary` fill, label `#111827/600`, connector to the right turns `#E5E7EB`
- Future: hollow `#E5E7EB`, label `#8A929E`
- Connector: `2px`, `success-dot` behind current, `#E5E7EB` ahead
- Compresses on narrow viewports to "Tahap 3 dari 6 · Negosiasi"
- **Read-only.** Clicking a stage never advances the FSM — that always happens through an explicit action button with its own confirmation.

### 12. Approval banner

For dual-approval and blocked states (`DualFSMStatusBanner` and friends):

```
┌────────────────────────────────────────────────────────────────┐
│ ⏳ Menunggu approval Service Manager            [Setujui] [Tolak]│
│    Diajukan Budi Santoso · 08 Agu 2026, 09:15                  │
└────────────────────────────────────────────────────────────────┘
```

- Full-width, `attention-wash` background, `1px solid` at 30% `attention-dot`, `8px` radius, `12px 16px` padding
- 16px icon in `-fg`, title `14px/600`, meta line `12px`
- Action buttons right-aligned, only rendered for the role that can act — everyone else sees the state without dead buttons
- Same component with `danger` tone for rejections (showing the rejection reason) and `success` for a recently-granted approval that then fades from the layout on next load
- **One banner maximum per panel.** Multiple pending approvals collapse into "2 approval menunggu" with a link to the queue.

### 13. Maps

Leaflet + react-leaflet, used in Lacak Sales (live + riwayat), delivery journey, and visit confirmation.

- When GPS is the point, the map takes **≥60%** of the content area. The list panel is 40% and scrolls.
- Rep/driver marker: the **initials avatar** on the map, not a generic pin. Instantly identifies who's who.
- Route line: `brand-primary`, `3px`, `0.75` opacity
- Visit/stop pins: numbered circles; completed `success-dot`, upcoming `neutral-dot`
- Live position: pulsing `brand-primary` dot — **this is the only permitted looping animation in the system**
- Controls: zoom bottom-right only. No layer switcher unless satellite is genuinely needed.
- Tile layer: OSM standard. Consistent across web and Flutter.
- Loading a map: grey `#F1F3F5` block at final dimensions, never a spinner
- GPS unavailable: inline `attention` banner over the map — "Sinyal GPS tidak tersedia" — not a modal

### 14. Media, evidence, and documents

Photo evidence appears throughout — kunjungan, QC, test load, BAST, klaim.

- Thumbnails: `72px` squares, `6px` radius, `1px #E5E7EB`, `object-cover`, 8px gap, wrapping grid
- Click → full-screen lightbox with counter ("3 / 8") and arrow-key navigation
- Upload slot: dashed `1.5px #E5E7EB`, `#F8F9FA` fill, centered 20px `Camera` icon + `12px #8A929E` label
- Upload progress: a `2px` `brand-primary` bar across the bottom of the thumbnail, not a spinner overlay
- All media URLs go through `mediaUrl()` — never construct `/media/` paths inline
- Document rows: 16px `FileText` icon + filename (`14px`) + size and date (`12px #8A929E`) + a ghost `Download` button, `48px` row height, divider between rows

### 15. Signature pad

Used in survey, BAST, serah-terima.

- Canvas `#FFFFFF`, `1px solid #E5E7EB`, `6px` radius, aspect ratio 3:1, min height 140px
- Stroke `#111827`, 2px, smoothed
- Dashed baseline at 75% height in `#E5E7EB` with a `11px #8A929E` label beneath: "Tanda tangan pelanggan"
- Actions: ghost "Hapus" left, primary "Simpan" right, below the canvas
- Captured signatures render as a plain image on the same bordered canvas with name + timestamp underneath

### 16. Wizards

Multi-step flows (email campaign, kunjungan, opname).

- Step rail at the top: numbered circles + labels, same treatment as the FSM rail
- One step per screen. Never two steps side by side.
- Footer: `[Kembali]` left, `[Lanjut]`/`[Selesai]` right, sticky, with a top border
- Forward is blocked until the step validates; the disabled button is accompanied by the reason
- Backward never loses entered data
- Leaving mid-wizard prompts once: "Keluar dari wizard? Data yang belum disimpan akan hilang."

### 20. Full-width editor mode

A line-item editor is not a detail panel. `QuotationItemsTable` in edit mode has **13 editable columns** (No · Nama Produk · Kode Internal · Merk · Engine Type · KVA · KW · Spesifikasi · Qty · Satuan · Harga Satuan · Diskon % · Total). Inside the 45% detail panel those inputs collapsed to ~45px — "Perkins" rendered as `/erli` — and widening the split to 68% did not fix it. **No split ratio fixes 13 columns in a side panel.**

**Rule: when a line-item editor opens, it takes the full content area.** It is already a distinct mode with its own explicit close control, so it should behave like one.

```
┌──────────┬──────────────────────────────────────────┐
│ sidebar  │ top bar                                  │
│          ├──────────────────────────────────────────┤
│          │ ╔══════════════════════════════════════╗ │
│          │ ║  Editor — fills the content area,    ║ │  ← absolutely positioned
│          │ ║  above the two-column layout.        ║ │    over <main>, its own
│          │ ║  Full width for the items table.     ║ │    scroll, explicit close
│          │ ╚══════════════════════════════════════╝ │
└──────────┴──────────────────────────────────────────┘
```

- The editor is `absolute inset-0 z-20 bg-surface-base`. No prop drilling, no change to `TwoColumnLayout`, and the list panel simply isn't competing for space.
- **Containing block, precisely:** inside a two-column page the overlay resolves against **`TwoColumnLayout`'s root**, which is already `relative` and already spans list + detail — so it covers the whole content area. `<main>` in `AppLayout` is also `relative`, which is *redundant on that path*; it is kept as the fallback so this pattern also works on a page that has no `TwoColumnLayout`. The detail panel's own `overflow-hidden` does not clip the overlay, because that div is static and therefore not in the containing-block chain.
- The overlay sits above the divider's collapse toggle (`z-10`).
- The editor keeps a single unambiguous exit ("Tutup"), and the sticky action bar stays pinned to its bottom.
- Wide editable tables declare **explicit column widths** — an editable cell must never be allowed to collapse below the width of its own content. Give every input a `min-w`.

Reference widths for the 13-column quotation table (≈1530px, inside a horizontal scroller for narrow screens):

| No. | Nama Produk | Kode | Merk | Engine Type | KVA | KW | Spesifikasi | Qty | Satuan | Harga Satuan | Disk % | Total |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 44 | 210 | 120 | 120 | 140 | 80 | 80 | 180 | 70 | 100 | 160 | 80 | 150 |

**Applies to the quotation editor only.** The Stream B/C/D penawaran editors were checked and do **not** qualify — B has 8 columns, C has 5, D has 6, only Qty/Harga/Diskon are editable, and none is a distinct mode with its own close control (they are inline tab content with per-row "Ubah"). They have no collapse problem at a 68% detail width, and the overlay treatment would not fit their interaction model.

*(An earlier draft of this pattern claimed the streams "share the shape". That was asserted from the shared name, not from the code, and was wrong. Revisit only if a stream editor ever becomes a true multi-column all-rows editor.)*

---

## Motion

Motion in this system is nearly absent, and that is deliberate.

| Element | Transition |
|---|---|
| Hover (color/background) | `150ms ease` |
| Sidebar collapse | `200ms ease` |
| Modal / sheet enter-exit | `180ms ease-out` (fade + 2% scale) |
| Panel collapse | `200ms ease` |
| Skeleton shimmer | `1.5s` loop |
| Live GPS dot | `2s` pulse loop |

**Nothing else animates.** No page transitions on desktop, no staggered list entrances, no number count-ups, no scroll-triggered reveals, no parallax. Everything except the skeleton shimmer and the GPS dot is a one-shot ≤200ms transition. Respect `prefers-reduced-motion` by disabling the two loops.

---

## Accessibility floor

Non-negotiable, and cheap if done from the start:

- Body text ≥ 4.5:1, large text and UI borders ≥ 3:1. The status `-fg` values in this document are chosen to pass on their `-wash`.
- **Never color alone.** Every status has a label. Every chart series has a direct label.
- Visible focus ring on everything focusable. Never `outline: none` without a replacement.
- Every icon-only button has `aria-label`; every input has a bound `<label>`; every image has meaningful `alt` (or `alt=""` if decorative).
- Modals trap focus and restore it on close — Radix handles this; don't build custom modals that don't.
- Tables use real `<th scope="col">`.
- The full primary flow — login, search, select, act — must be completable by keyboard.
- Minimum click target 32px desktop, 48px mobile.

---

## Mobile — Flutter app

The Flutter app serves sales reps, technicians, and drivers in the field. Same tokens, adjusted ergonomics. Mirror this palette into the Flutter theme file rather than re-picking colors — a divergence between web and mobile orange is exactly the kind of thing that makes a product feel unowned.

### Global rules
- Base viewport 375px, scale up
- Respect notch and home-indicator safe areas
- **Touch targets ≥ 48px.** No exceptions — these users are wearing gloves in a workshop.
- Buttons stack full-width. No side-by-side buttons.
- No horizontal scroll anywhere
- Body text ≥ 14px, never below 12px
- **Every screen works offline-degraded:** show the last known data with a `attention` "Data offline · terakhir diperbarui 10:32" strip rather than an error page

### Structure
```
┌─────────────────────────┐
│ Status bar (system)     │
├─────────────────────────┤
│ Top bar 56px            │  Powerline mark left, title center, bell right
├─────────────────────────┤
│                         │
│ Content, bg #F8F9FA     │  16px horizontal padding
│ scrolls                 │
│                         │
├─────────────────────────┤
│ Bottom tabs 56px        │  max 4 tabs, #FFFFFF, top border #E5E7EB
├─────────────────────────┤
│ Home indicator          │
└─────────────────────────┘
```

- Tabs by role — Sales: Beranda · Pelanggan · Kunjungan · Profil. Teknisi: Beranda · Tugas · Scan · Profil. Driver: Beranda · Pengiriman · Rute · Profil.
- Tab icon 22px Lucide-equivalent, label 10px/500, active `brand-primary`, inactive `#8A929E`
- Lists are **continuous with dividers**, not stacks of floating cards — WeChat/Alipay style. Row min height 72px, padding `12px 16px`.
- Pull-to-refresh yes; infinite scroll for history; no swipe actions — tap only
- Bottom sheets for all modals: 16px top radius, 40×4px handle
- Page transitions slide right on push, back on pop, ≤250ms. No fades, no scales.
- Camera capture shows the preview immediately, uploads in the background with a progress bar on the thumbnail, and **queues the upload if offline** — the technician must never be blocked by signal

---

## Printed documents (PDF)

Out of the token system's scope but part of the visual identity: quotations, Surat Tugas, Surat Jalan, BAST, laporan keuangan. These already share `quotations/assets/pdf_header+footer.png` via `draw_letterhead` — keep that as the single source.

Rules: letterhead on page 1 of every official document; monospace for document numbers; `formatCurrency` for all money with a terbilang line where the client format requires it; tables use hairline `#E5E7EB` rules and no fills; signature blocks bottom-right with name, role, and date; page numbering `Halaman N dari M` bottom-center from page 2. Never reuse screen status colors in print — greyscale printers turn them all into the same mud.

---

# Part 2 — Migration from the current frontend

The audit that produced this list, with counts from the current `src/`:

| # | Finding | Scale |
|---|---|---|
| 1 | `html { font-size: 14px }` compounds with Tailwind's rem scale — every size is 12.5% below its class name | Global |
| 2 | No icon library; nav icons are `label.charAt(0)`; emoji as icons | 73 files |
| 3 | `border-gray-200` used directly; no border token exists | 187 uses |
| 4 | Seven radii in circulation (`lg` 308, `md` 239, `full` 105, `rounded` 81, `xl` 48, `sm`, `2xl`) | ~780 uses |
| 5 | Status `-fg` colors fail AA on their washes (`#22C55E` ≈ 2.2:1) | `StatusBadge`, 53 importers |
| 6 | `status-orange` was the same hex as the old brand orange — pending looked like a CTA | Palette |
| 7 | Raw `<button>` instead of `Button` | 126 vs 83 |
| 8 | Hand-rolled `<table>` instead of `DataTable` | 21 vs 3 |
| 9 | `StatusBadge` maps generic English keys; most Indonesian FSM states fall through to grey | 53 importers |
| 10 | `Header` renders no title — `AppLayout` never passes `pageTitle` | Every screen |
| 11 | `App.css` is unimported Vite template boilerplate (`.hero`, `.vite`, `#next-steps`) | 184 dead lines |
| 12 | Ad-hoc tint pairs (`bg-orange-50`, `bg-amber-50`, `bg-green-50`…) invented per page | ~40 uses |
| 13 | Inconsistent shadows (`shadow-sm` on buttons, `shadow-2xl` on modal) | 27 uses |

### The new `tailwind.config.ts`

```ts
import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
        mono: ['JetBrains Mono', 'SF Mono', 'Fira Code', 'Consolas', 'monospace'],
      },
      // Absolute px — immune to the root font-size
      fontSize: {
        micro:   ['11px', { lineHeight: '16px', fontWeight: '500' }],
        caption: ['12px', { lineHeight: '18px' }],
        body:    ['14px', { lineHeight: '22px' }],
        section: ['16px', { lineHeight: '24px', fontWeight: '600' }],
        page:    ['20px', { lineHeight: '28px', fontWeight: '600' }],
        data:    ['24px', { lineHeight: '32px', fontWeight: '600' }],
      },
      colors: {
        'brand-primary':       '#1B4332',
        'brand-primary-hover': '#123125',
        'brand-primary-wash':  '#EDF5F1',

        'sidebar-bg':     '#10231A',
        'sidebar-hover':  '#1C3A2C',
        'sidebar-text':   '#A0AEC0',
        'sidebar-active': '#4FBF8F',

        'surface-base':   '#F8F9FA',
        'surface-card':   '#FFFFFF',
        'surface-subtle': '#F1F3F5',

        line:            '#E5E7EB',   // class: border-line
        'line-strong':   '#D1D5DB',   // class: border-line-strong

        'text-primary':   '#111827',
        'text-secondary': '#5B6472',
        'text-muted':     '#8A929E',
        'text-inverse':   '#FFFFFF',

        status: {
          'neutral-dot':  '#9CA3AF', 'neutral-wash':  '#F3F4F6', 'neutral-fg':  '#4B5563',
          'info-dot':     '#3B82F6', 'info-wash':     '#EFF6FF', 'info-fg':     '#1D4ED8',
          'attention-dot':'#F59E0B', 'attention-wash':'#FFFBEB', 'attention-fg':'#B45309',
          'success-dot':  '#22C55E', 'success-wash':  '#F0FDF4', 'success-fg':  '#15803D',
          'danger-dot':   '#EF4444', 'danger-wash':   '#FEF2F2', 'danger-fg':   '#B91C1C',
          'special-dot':  '#8B5CF6', 'special-wash':  '#F5F3FF', 'special-fg':  '#6D28D9',
        },

        // DEPRECATED — keep until Step 5 migrates the call sites.
        // Deleting these does not error: Tailwind simply stops generating the
        // classes, and every badge silently loses its color. Remove only after
        // the tone API has landed everywhere. See the warning below.
        //
        // 'status-orange' is REPOINTED, not deleted. It was #F97316 — identical
        // to the old brand orange, which made "menunggu" look like a CTA. Pointing it at
        // the attention hue fixes that with zero call-site edits.
        'status-orange': '#F59E0B',
        'status-green':  '#22C55E',
        'status-yellow': '#EAB308',
        'status-red':    '#EF4444',
        'status-blue':   '#3B82F6',
        'status-gray':   '#6B7280',

        avatar: {
          1: '#F97316', 2: '#3B82F6', 3: '#22C55E', 4: '#8B5CF6',  // decorative hash ramp — NOT brand
          5: '#EC4899', 6: '#06B6D4', 7: '#F59E0B',
        },
      },
      borderRadius: {
        DEFAULT: '6px',   // controls: buttons, inputs, tags
        md:      '6px',
        lg:      '8px',   // containers: cards, panels, tables
        xl:      '10px',  // modals only
      },
      boxShadow: {
        // The only three shadows in the system
        popover: '0 4px 12px rgba(17, 24, 39, 0.08)',
        modal:   '0 12px 32px rgba(17, 24, 39, 0.16)',
        sticky:  '0 -1px 0 0 #E5E7EB',
        none:    'none',
      },
      spacing: {
        sidebar: '240px',
        'sidebar-collapsed': '64px',
        card: '24px',
        section: '16px',
      },
    },
  },
  plugins: [],
}

export default config
```

### The new `index.css` base layer

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  html {
    font-size: 16px;          /* was 14px — see the root font-size decision */
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }

  body {
    margin: 0;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-size: 14px;          /* Body level */
    line-height: 22px;
    background-color: #F8F9FA;
    color: #111827;
  }

  #root { width: 100%; height: 100vh; }

  /* Tabular figures for all numeric data */
  td, th, .tabular { font-variant-numeric: tabular-nums; }

  /* Focus ring, applied once, globally */
  :focus-visible {
    outline: 2px solid rgba(249, 115, 22, 0.45);
    outline-offset: 2px;
  }

  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
      animation-duration: 0.01ms !important;
      animation-iteration-count: 1 !important;
      transition-duration: 0.01ms !important;
    }
  }
}
```

### Sequenced migration

Ordered by impact-per-hour. Steps 1–4 are mechanical and safe; 5–8 are per-screen work that can proceed incrementally while features ship.

#### Step 1 — Fix the root font-size (half a day, highest impact)
Set `html { font-size: 16px }` and swap the type scale to the px tokens above. Then walk the eight densest screens — `StockDashboard`, `DirDashboard`, `ClaimsTab`, `DeliveryTab`, `PipelineList`, `KunjunganPage`, `BqDqPanel`, `TestLoadTab` — and fix anything that now overflows. Do it as one commit so it can be reverted cleanly. Everything else in this document assumes it's done.

#### Step 2 — Land the tokens ✅ APPLIED in `frontend_glm/`
Drop in the new config, then:
```
border-gray-200  →  border-line          (187 occurrences, identical hex)
border-gray-300  →  border-line-strong   (8, identical hex)
border-border    →  border-line          (30 — BROKEN, see below)
bg-surface       →  bg-surface-card      (19 — BROKEN, see below)
```
The first two are a pure rename with no visual diff. Delete `App.css` while you're in there — it is unimported Vite template boilerplate.

**Two broken classes found during this step.** `TrackPage.tsx` and `DirDashboard.tsx` used `bg-surface` and `border-border`, neither of which is a defined token — the config has `surface-base/card/subtle` and no bare `surface` or `border` key. Tailwind emits nothing for an undefined color, with no error and no type warning:
- `bg-surface` → **no background at all**; those panels rendered transparent against the grey canvas
- `border-border` → invalid, but accidentally looked right because Tailwind v3's preflight defaults `border-color` to `gray-200`

This is the exact failure mode the token layer exists to prevent, and it is the argument for the ESLint rule banning non-token colors. Both are fixed by the rename above.

#### Step 3 — Adopt Lucide and delete every emoji ✅ APPLIED in `frontend_glm/` (26 files)
`npm i lucide-react`, then work the mapping table above through the 73 affected files. Priority order, because these are seen on every screen:
1. `Sidebar.tsx` — real nav icons, kill `label.charAt(0)`, `ChevronLeft/Right`, `LogOut`
2. `SearchInput.tsx` — `Search`
3. `Toast.tsx` — the four status icons, plus the white-card restyle
4. `Modal.tsx` — `X`, and drop `backdrop-blur-sm`
5. `InteractionIcon.tsx` — `MapPin` `Phone` `MessageCircle` `Mail`
6. The remaining 68 page files

A single `<Icon>` wrapper that fixes `strokeWidth={1.75}` and maps `size` to the 18/16/14 scale will keep this consistent and make the sweep faster.

**Gotcha — emoji held in string-typed maps.** Several files store the emoji in a `Record<K, string>`, which means this is a *type* change, not a value swap. `InteractionIcon.tsx` and `Toast.tsx` both do this; expect others.

```tsx
// BEFORE
const ICON_MAP: Record<InteractionType, string> = { KUNJUNGAN: '📍', ... }
<span className="... text-sm">{ICON_MAP[type]}</span>

// AFTER
import { MapPin, type LucideIcon } from 'lucide-react'
const ICON_MAP: Record<InteractionType, LucideIcon> = { KUNJUNGAN: MapPin, ... }
const Icon = ICON_MAP[type]              // must be capitalized to render as JSX
<span className="..."><Icon size={14} strokeWidth={1.75} /></span>
```

Where the parent carried a `text-*` size class that existed only to size the emoji, drop it — the icon is sized by its `size` prop.

#### Step 3b — Emoji in action labels ✅ APPLIED in `frontend_glm/` (11 files, 25 glyphs + 5 follow-ups)
Step 3 converted emoji used as standalone icons (26 files). It deliberately left emoji sitting inside labels, because the protocol's "don't touch copy" rule was originally worded as "labels" — too broad. See the second-wave mapping table and the action-vs-state test in the Icons section.

Scope: emoji prefixing a **clickable action** — `🖨️ Cetak PDF`, `📧 Kirim ke Customer`, `📎 Terima PO`, `👁 Preview PDF`, `📥 Import dari Excel`, `✓ Setujui`. Roughly 30 occurrences.

Explicitly **not** in scope:
- Status glyphs coloured by `text-status-*` (`✓ QC Lulus`, `🟠 Menunggu`) → **Step 5**
- `EmptyState icon="…"` call sites (~55) → **Step 4** deletes the prop
- `KpiCard icon='trending_up'` → Material-icon names, a separate system
- Sentences (`"Data tersimpan ✅"`), `×` as multiplication, `→` in comments → leave permanently

#### Step 4 — Retune the primitives ✅ APPLIED in `frontend_glm/`
`Button` (px-exact heights 28/36/44, no shadows, `focus-visible` ring, 45% disabled), `StatusBadge` (three-value tones + `tone` prop, legacy string map retained), `FormField` (11px label, error *replaces* helper so height never jumps), `Modal` (`backdrop-blur` dropped, flat 45% ink overlay, `wide` variant), `Toast` (white card with a coloured left edge, Lucide icons), `EmptyState` (**`icon` prop deleted** — 53 call sites stripped), `LoadingSpinner`, plus a new `Skeleton` / `SkeletonTable` / `SkeletonDetail`. `DataTable` gained alignment, widths, sticky header, selection, footer slot, and skeleton loading.

Also landed the base rules that don't depend on Step 1: `tabular-nums` on table cells, a single global `:focus-visible` ring, and `prefers-reduced-motion`.

**Deliberate deviation:** the doc asks empty states to be a single line, but 53 call sites pass both `title` and `message`. Both still render — as two quiet lines, no bold heading, no icon. Collapsing each to one sentence is copy work, not a primitives concern.

**Found during this step: the Material Icons font is never loaded.** `index.html` loads only Inter, yet 20 `<span className="material-icons">` elements existed across `DirDashboard`, `EmailCampaignWizard`, and `TrackPage`. They were rendering their icon *names as literal English text* — "location_off", "person_off", "arrow_upward", "leaderboard", "check_circle" — visible on three whole pages. Both emoji sweeps missed them because they are not emoji. All 20 are now Lucide; **zero `material-icons` references remain.** `KpiCard` lost its icon entirely, which fixes the bug and matches the "no icons in KPI cards" rule.

The lesson generalises: **grep for the icon *system*, not for the glyphs.** A missing webfont fails silently and looks like copy.

#### Step 5 — Status taxonomy ✅ APPLIED in `frontend_glm/`

> ⚠️ **Learn from the `status-orange` incident.** During Step 2 this token was *deleted* from the config on the correct design reasoning that orange must not double as "pending". It was still referenced **151 times across 40 files**. Tailwind does not error on an undefined color — it silently stops emitting the class, so every pending indicator in the app rendered with no background and no text color. It was caught only because an unrelated Step 3b review happened to look at one of those banners.
>
> **Never delete a color token while call sites reference it.** Repoint it (a one-line hue change delivers the design fix with zero risk), migrate the call sites, *then* delete. Verify with the built CSS, not the source:
> ```bash
> npx vite build && grep -o "status-orange" dist/assets/*.css | wc -l   # 0 = broken
> ```
> Use `grep -o | wc -l`, not `grep -c` — the latter counts lines, and minified CSS will under-report.
**Decide half ✅ DONE in `frontend_glm/`.** `StatusTone` now lives in `types/status.ts`, and all **28 `*_BADGE` maps across 10 domain type files** emit `Record<X, StatusTone>` instead of `Record<X, string>`. Because `StatusBadge` resolves a tone arriving through the deprecated `status` prop as itself, the app renders correctly *today* — the apply half below is safe to land incrementally.

**Apply half — mechanical, delegable.** Four passes, in this order:

**1 · `StatusBadge` call sites (83).** `status=` → `tone=`. 77 already pass a `*_BADGE[...]` lookup and are a pure rename. The 16 literals map as:

| Literal | Tone | Literal | Tone |
|---|---|---|---|
| `"done"` | `success` | `"overdue"` | `danger` |
| `"pending"` | `attention` | `"rejected"` | `danger` |
| `"in-progress"` | `info` | `"habis"` | `danger` |
| `"aktif"` | `success` | | |

**2 · Ad-hoc colour classes (617 across 91 files).** This is the bulk. Legacy token → three-value token, by *role*:

| Legacy | Tone | | Role | Rewrite |
|---|---|---|---|---|
| `status-green` | success | | `bg-X/5` `/10` `/15` `/20` | `bg-status-<tone>-wash` (drop the opacity) |
| `status-red` | danger | | `text-X` | `text-status-<tone>-fg` |
| `status-yellow` | attention | | `bg-X` (solid dot/pill) | `bg-status-<tone>-dot` |
| `status-orange` | attention | | `border-X/N` | `border-status-<tone>-dot/N` (keep opacity) |
| `status-blue` | info | | | |
| `status-gray` | neutral | | | |

**3 · Status glyphs (~25).** `✓ ✕ ⏳ 🟠 ● ○` that are coloured by a `text-status-*` class. Deferred here from Steps 3/3b precisely so glyph and tone migrate together. A glyph+label pair (`✓ QC Lulus`) becomes a `StatusBadge` with the right tone; a lone decorative glyph becomes a Lucide icon in `text-status-<tone>-fg`.

**4 · Only then, delete the six legacy tokens** from `tailwind.config.ts` and verify against the **built CSS** — see the warning above. This pass is what finally retires them.

**Outcome:** 85 `tone=` call sites, **zero** `status=`, zero legacy classes in source, zero legacy tokens in the built CSS. The deprecated `status` prop and its string-guessing map are deleted — `StatusBadge` now takes `tone` + `label`, both required.

Two lessons from the finish:
- **Removing the optional prop is what found the last six sites.** A grep for `<StatusBadge ... status=` misses multi-line JSX; making `tone` required turned every straggler into a compile error. Retire a deprecated prop by deleting it, not by leaving it optional.
- **String-guessing hid real gaps.** Four domains (`CustomerStatus`, `CampaignStatus`, kunjungan approvals, commissioning attempts) never had a `*_BADGE` map and reached the badge via `.toLowerCase()`. Unmapped values silently resolved to grey — `PROSPEK_BARU`, `WARMING`, `QUALIFIED`, `PIPELINE` had *always* rendered neutral. Those domains now have real tone maps.

#### Step 6 — Consolidate tables ✅ APPLIED in `frontend_glm/` — *approach changed, see below*
`DataTable` was extended in Step 4 (alignment, widths, sticky header, skeleton loading, selection, footer slot). The plan was then to convert all 24 hand-rolled tables onto it.

**That plan was wrong, and the inventory is why.** Of the 24 tables, 3 are editable line-item editors with per-row input state, 5 carry `colSpan` totals or empty rows, and several have bespoke sort headers. Forcing them through `DataTable` meant restructuring surrounding JSX in 20 files — where the failure mode is a silently dropped column that renders as a table which simply *lacks* that column. No compile error, no visual "wrong".

Meanwhile the actual defect was measurable and much narrower: **18 different `<th>` class strings and 11 `<tr>` variants**. The inconsistency was the polish problem — not the hand-rolling.

So Step 6 normalises instead of converts. A `.ds-table` class in `index.css` fixes header type, padding, borders, and hover in **one edit per table**, with a `.ds-table--compact` modifier for nested line-item editors (14 compact / 10 standard). `text-align` is deliberately *not* normalised, so per-column numeric right-alignment survives as a utility.

**The rule going forward:** new read-only tables use `<DataTable>` — it adds skeleton loading, empty states, and row selection that CSS cannot. Existing bespoke tables stay bespoke and carry `ds-table`. The earlier absolute "no raw `<table>` in a page file" is retired as unrealistic.

**Also found:** `bg-surface-alt` — a *fourth* phantom token, 10 uses in `DirDashboard`, absent from the built CSS, so those chips, hover states and the totals row had no background at all.

#### Step 7 — Radius and shadow sweep ✅ APPLIED in `frontend_glm/`
```
rounded, rounded-sm, rounded-md      →  rounded-md      (6px, controls)      → 322
rounded-lg, rounded-xl, rounded-2xl  →  rounded-lg      (8px, containers)    → 357
rounded-full                         →  unchanged (dots, avatars, pills)     → 105
rounded-xl                           →  restored on Modal only (10px)

shadow-sm, hover:shadow-sm/md, transition-shadow  →  deleted (nothing floats)
shadow-lg                            →  shadow-popover  (dropdowns, toasts, tooltips)
shadow-2xl                           →  shadow-modal    (Modal only)
```
Two bare `shadow` uses are deliberately left: the toggle knob in `PersiapanVisitPanel` and the inline `box-shadow` on the `LiveTrackingMap` pulse marker (the one permitted looping animation).

#### Step 9 — Typography hierarchy ✅ APPLIED in `frontend_glm/`
71 ad-hoc heading treatments across 7 variants (`text-lg font-bold`, `text-base font-semibold`, `text-2xl font-bold`…) collapsed onto the four type tokens, now real Tailwind classes: `text-card` · `text-section` · `text-page` · `text-data`. A `card` entry (14px/20px/600) was added to the config — the scale had always described it but never shipped it.

The only judgement was `text-2xl`, which was doing two jobs. Split by element: `<h1>/<h2>` carrying text → `text-page` (4 sites); `<p>/<div>` rendering a value → `text-data` (12 sites). Zero ad-hoc heading treatments remain.

#### Step 8 — Layout polish ✅ APPLIED in `frontend_glm/`
- **Top bar title.** Derived from the route by longest-prefix match against `NAV_ITEMS` — **zero page edits**. On a detail route (`/pipeline/:dealId`) the bar shows "Pipeline" while the in-content `PageHeader` shows the entity, so the two are complementary rather than duplicated. Bar is now an exact 56px.
- **Sidebar grouped** into Penjualan · Produksi · Layanan · Keuangan · Sistem, with an unlabelled top group for the dashboards. A `group` field on `NavItem` drives it; a group with no role-visible items renders nothing, heading included. Collapsed mode shows a divider instead of a label.
- **Raw palette eliminated — 0 remaining.** ~60 ad-hoc classes mapped by *role*, not hue: orange/amber notice panels → `attention-*`, blue → `info-*`, green → `success-*`, red → `danger-*`, greys → `surface-*` / `line` / `text-muted`, `slate-800` → `sidebar-bg`. `hover:bg-{green,red}-600` became `hover:brightness-95`.
- **Selected row unified** to `bg-brand-primary-wash border-l-2 border-l-brand-primary` across all 11 list panels (was 3 variants incl. a stray `border-l-4`), and all 20 ad-hoc `bg-brand-primary/5` fills collapsed onto the `brand-primary-wash` token.

**Two more phantom tokens found by the broadened sweep:** `bg-primary` and `border-primary` on the BQ status filter in `DirDashboard` — the selected chip had no background *and* no border colour. Note the earlier narrow sweep missed these because it only matched known token prefixes; the broadened version in Enforcement matches **any** token-shaped class. It now reports clean.

### Enforcement

The system decays without a guard. Add ESLint rules so the next 199 files can't reintroduce the same drift:
- Ban raw Tailwind palette colors in `src/**` (`bg-gray-*`, `text-blue-*`, …) — tokens only
- Ban emoji in `.tsx` via a unicode-range rule
- Ban raw `<table>` outside `components/ui/`
- Warn on raw `<button>` outside `components/ui/`

**Standing check — phantom tokens.** Four undefined tokens (`bg-surface`, `border-border`, `bg-surface-alt`, plus `status-orange` which was deleted mid-migration) shipped silently, because Tailwind emits nothing for an unknown colour and TypeScript never sees a class string. Run this after any token work — it extracts every token-shaped utility from source and asserts each one resolves in the built CSS:

```bash
npx vite build
python3 - <<'EOF'
import re, glob
css = ''.join(open(p).read() for p in glob.glob('dist/assets/*.css'))
src = ''.join(open(f).read() for f in glob.glob('src/**/*.tsx', recursive=True))
pat = re.compile(r'\b((?:bg|text|border|ring|fill|stroke)(?:-[trblxy])?-(?:brand|surface|status|sidebar|line|avatar)[a-z0-9-]*)')
missing = sorted({c.split('/')[0] for c in pat.findall(src) if c.split('/')[0] not in css})
print('MISSING:', missing or 'none ✓')
EOF
```

**Landed in `frontend_glm/`** as `eslint.config.js` rules plus two npm scripts:

```bash
npm run check:tokens   # phantom-token sweep against the built CSS
npm run check:ds       # vite build → token sweep → eslint
```

The rules encode what was actually decided, not the original aspiration: a bespoke `<table>` is allowed if it carries `ds-table`, and emoji in prose is fine — only emoji in a JSX *attribute* is an error. Raw `<button>` is a warning (115 remain by design), raw palette colours and emoji-in-attribute are errors. **They add zero errors to the current tree** — `frontend_glm` and the untouched `frontend` both report the same 95 pre-existing lint errors.

⚠️ `check:ds` deliberately runs `vite build`, **not** `npm run build`. The latter is `tsc -b && vite build`, and with 15 pre-existing type errors it never reaches vite — so the token sweep would inspect a stale `dist/` and report false phantoms. It did exactly that on first run.

**Land these rules before delegating any migration step, not after.** They are what turns a worker's output from "looks right" into "mechanically verified" — the difference between reviewing 73 files by eye and running one command.

### Delegation protocol

Most migration steps are mechanical enough to hand to a worker model (a subagent, or an external model driven separately). These rules apply to **every** delegated step, and exist because the failure mode of a capable worker is not incompetence — it's helpfulness.

**Scope.** Do exactly one numbered step from the sequenced migration. You will read about the other steps in this document; ignore them. Seeing that radii should be consolidated while doing the icon sweep is not permission to consolidate radii.

**Do not:**
- Change business logic, API calls, state, hooks, or control flow. These steps are presentational.
- Restyle, re-layout, or otherwise improve anything beyond the step's stated scope.
- Reformat untouched lines, reorder imports beyond what the step requires, or "tidy" adjacent code.
- Touch **prose**: sentences shown to the user (toast message bodies, helper text, placeholders, empty-state sentences), or code comments.

**"Prose" does not mean "any string."** An emoji prefixing a short action label *is* an icon and must be converted:

| | |
|---|---|
| ✅ Convert | `🖨️ Cetak PDF` → `<Printer size={16}/> Cetak PDF` — button label |
| ✅ Convert | `🗄️ Customer diarsipkan` → icon + text — inline status label |
| ❌ Leave | `"Data berhasil disimpan ✅"` — a sentence |
| ❌ Leave | `× {qty}`, `63,5 × 38,1 mm` — multiplication sign, not a glyph |
| ❌ Leave | `→` inside a code comment |

The test: **if it sits to the left of ≤4 words and could be swapped for an `<svg>` without rewriting the sentence, it is an icon.**
- Rename files or change exported component signatures.

**When a case is ambiguous, skip the file and report it.** A skipped file costs a minute of review. A plausibly-wrong guess merged into 199 files costs a month of not noticing.

**Batch and verify.** Work in batches of ~10 files. After each batch run `npx tsc -b` and the lint rules above, and fix before continuing. Do not present a 73-file diff that has never been type-checked.

⚠️ **The codebase does not type-check clean.** As of August 2026 there are **15 pre-existing `tsc` errors** (in `BqDqPanel`, `DealDetail`, `RingkasanTab`, `AssemblyTab`, `QCTab`, `TestLoadTab`, `OpenClaimModal`, `ClaimsTab`) — unrelated to design, and `npm run build` (`tsc -b && vite build`) therefore already fails on `main`. `npx vite build` alone succeeds.

So the verification bar is **"no NEW errors against the baseline"**, never "passes clean":
```bash
# capture the baseline BEFORE touching anything
npx tsc -b --force 2>&1 | grep "error TS" | sort > /tmp/baseline.txt
# after each batch
npx tsc -b --force 2>&1 | grep "error TS" | sort > /tmp/after.txt
diff /tmp/baseline.txt /tmp/after.txt    # must be empty
```
A worker told to make `tsc` pass will "helpfully" start fixing unrelated type errors, which is exactly the scope creep this protocol exists to stop.

**Report:** files changed, every judgement call made where this document didn't give an exact answer, and every file skipped with the reason.

**Steps that should not be delegated to a model at all:**
- **Steps 2 and 7** are find-and-replace over known-identical values. A shell command does this faster, cheaper, and without drift.
- **Step 5** (status tones) requires knowing what a state *means* in the business flow. A wrong tone still renders as a perfectly good-looking badge — it passes type-check, lint, and screenshot review. The tone maps get written by someone who knows the FSM; only the call-site flips are delegable.
- **Step 6** (table consolidation) has the same invisible-failure property: a dropped column looks like a table that simply doesn't have that column.

The general test: **delegate the steps where a wrong answer looks wrong.**

---

## Do's and Don'ts

### Do
- Use data density. If a table can show 15 rows without scrolling, show 15 rows.
- Use monospace for serial numbers, nomor penawaran, kode unit, PO numbers.
- Use initials avatars, never silhouettes.
- Let the map be big when GPS is the feature.
- Use the sidebar for navigation, never for data.
- Keep hover effects to a background shift.
- Show the real backend error message, not "Terjadi kesalahan".
- Reserve `attention` amber for "a human must act" — it's the color of a queue.
- Write specific empty-state copy naming what's missing.
- Use realistic Indonesian genset data in every mockup.

### Don't
- Don't use emoji as icons. Ever. This is rule zero.
- Don't use illustrations or decorative graphics anywhere.
- Don't use more than one primary button per section.
- Don't use cards to list data — use tables.
- Don't add shadows to anything except modals and popovers.
- Don't animate anything except the two permitted loops and ≤200ms state transitions.
- Don't use a hamburger menu on desktop — the sidebar is always there.
- Don't encode meaning in color alone.
- Don't put a spinner where content will appear — use a skeleton.
- Don't invent a color, a radius, or a shadow that isn't in this document. If you need one, the document is wrong — change it here first.

---

## Mockup data rules

Every mockup uses realistic NaraHome operational data. No Lorem ipsum, no "John Doe", no `$1,234.00`.

**Customers:** PT Sinar Abadi Sejahtera · CV Karya Mandiri Teknik · PT Griya Nusantara Property · UD Berkah Jaya · PT Mitra Industri Cikarang · RS Harapan Bunda · Hotel Grand Kencana

**Staff:**
- Sales: Budi Santoso (BS) · Rina Wijaya (RW) · Agus Prakoso (AP)
- Service Manager: Hendra Gunawan (HG)
- Teknisi: Dedi Kurniawan (DK) · Slamet Riyadi (SR) · Yusuf Maulana (YM)
- Driver: Joko Purnomo (JP) · Wahyu Setiawan (WS)
- Admin: Sri Lestari (SL) · Direktur: Ir. Tanto Wijaya

**Products:** Genset 100 kVA Open · Genset 250 kVA Silent · Genset 500 kVA Silent · Genset 1000 kVA Silent — engine Perkins / Cummins / Mitsubishi, alternator Stamford / Leroy Somer

**Money:** `Rp 485.000.000` · `Rp 1.250.000.000` · `Rp 2.100.000.000` — always `formatCurrency`, always `id-ID`, no decimals

**Document numbers:** Penawaran `QT-2026-0042` · Proyek `PRJ-2026-0117` · Surat Jalan `SJ-2026-0089` · Klaim `KLM-2026-0031` · Serial `DPL-250-2026-014` — monospace, always

**Addresses (Jabodetabek + Jawa Barat):** Kawasan Industri Jababeka Blok C-12, Cikarang · Jl. Raya Serang Km. 24, Balaraja, Tangerang · Jl. Soekarno-Hatta No. 412, Bandung · Kawasan Industri Pulogadung, Jakarta Timur · Jl. Raya Bogor Km. 30, Depok

**Dates:** `09 Agu 2026` · `09 Agu 2026, 14:32 WIB`

---

## Changelog

**v1.0 — August 2026** — Initial system. Derived from Cooljek Design System v1.0 (July 2026), retuned for NaraHome Powerline: orange accent replaces ice blue; three-value status colors replace flat ones; `status-orange` removed to stop pending reading as a CTA; root font-size corrected from 14px to 16px with an absolute px type scale; Lucide adopted to replace emoji; ERP-specific patterns added (two-column list+detail, FSM stage rail, approval banner, media evidence, signature pad, wizards) alongside the migration plan for the existing 199-file frontend.

---

*MJCX Studio — Building Products that Actually Ship*
