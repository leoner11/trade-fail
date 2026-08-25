import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: 'var(--brand-primary)',
          hover: 'var(--brand-primary-hover)',
          wash: 'var(--brand-primary-wash)',
        },
        ai: {
          fg: 'var(--ai-fg)',
          dot: 'var(--ai-dot)',
          wash: 'var(--ai-wash)',
        },
        surface: {
          base: 'var(--surface-base)',
          card: 'var(--surface-card)',
          subtle: 'var(--surface-subtle)',
        },
        line: 'var(--line)',
        'line-strong': 'var(--line-strong)',
        'text-primary': 'var(--text-primary)',
        'text-secondary': 'var(--text-secondary)',
        'text-muted': 'var(--text-muted)',
        'text-inverse': 'var(--text-inverse)',
        rail: {
          bg: 'var(--sidebar-bg)',
          hover: 'var(--sidebar-hover)',
          active: 'var(--sidebar-active)',
          text: 'var(--sidebar-text)',
        },
      },
      fontSize: {
        data: ['24px', '32px'],
        page: ['20px', '28px'],
        section: ['16px', '24px'],
        card: ['14px', '20px'],
        body: ['14px', '22px'],
        caption: ['12px', '18px'],
        micro: ['11px', '16px'],
      },
      width: {
        sidebar: '240px',
        'sidebar-collapsed': '64px',
      },
    },
  },
  plugins: [],
} satisfies Config
