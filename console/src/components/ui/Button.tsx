import { Loader2 } from 'lucide-react'
import type { ButtonHTMLAttributes, ReactNode } from 'react'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger'
type Size = 'sm' | 'md' | 'lg'

const VARIANT: Record<Variant, string> = {
  primary: 'bg-brand text-text-inverse hover:bg-brand-hover border-0',
  secondary:
    'bg-surface-card text-text-primary border border-line hover:bg-surface-subtle',
  ghost: 'bg-transparent text-text-secondary border-0 hover:bg-surface-subtle',
  danger: 'bg-[#EF4444] text-text-inverse border-0 hover:bg-[#DC2626]',
}

const SIZE: Record<Size, string> = {
  sm: 'h-7 px-2.5 text-caption font-medium',
  md: 'h-9 px-4 text-body font-medium',
  lg: 'h-11 px-5 text-body font-semibold',
}

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  loading?: boolean
  children: ReactNode
}

export function Button({
  variant = 'secondary',
  size = 'md',
  loading = false,
  disabled,
  className = '',
  children,
  ...rest
}: Props) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-1.5 rounded-md transition-colors duration-150
        focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand/40
        disabled:cursor-not-allowed disabled:opacity-45 ${VARIANT[variant]} ${SIZE[size]} ${className}`}
      disabled={disabled || loading}
      {...rest}
    >
      {loading && <Loader2 size={16} className="animate-spin" />}
      {children}
    </button>
  )
}
