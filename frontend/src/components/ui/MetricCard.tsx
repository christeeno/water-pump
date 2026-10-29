import type { ReactNode } from 'react'

interface Props {
  title: string
  icon?: ReactNode
  value?: string | number
  unit?: string
  subtitle?: string
  status?: 'normal' | 'warning' | 'critical' | 'offline'
  badge?: ReactNode
  children?: ReactNode
  className?: string
}

const borderColors = {
  normal: 'border-status-normal/20',
  warning: 'border-status-warning/30',
  critical: 'border-status-critical/30 shadow-red-900/20 shadow-md',
  offline: 'border-border',
}

export function MetricCard({ title, icon, value, unit, subtitle, status = 'normal', badge, children, className = '' }: Props) {
  return (
    <div className={`bg-bg-card border ${borderColors[status]} rounded-xl p-4 flex flex-col gap-3 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-text-muted">
          {icon}
          <span className="text-xs font-semibold uppercase tracking-wider">{title}</span>
        </div>
        {badge}
      </div>
      {/* Value */}
      {value !== undefined && (
        <div className="flex items-end gap-1">
          <span className="text-3xl font-mono font-bold text-text-primary leading-none">{value}</span>
          {unit && <span className="text-sm text-text-muted mb-0.5">{unit}</span>}
        </div>
      )}
      {subtitle && <p className="text-xs text-text-dim">{subtitle}</p>}
      {children}
    </div>
  )
}
