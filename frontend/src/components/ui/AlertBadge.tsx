import type { Severity } from '../../types'

interface Props {
  severity: Severity
  className?: string
}

const styles: Record<Severity, string> = {
  INFO: 'bg-blue-900/40 text-blue-400 border border-blue-700/40',
  WARNING: 'bg-amber-900/40 text-status-warning border border-status-warning/40',
  CRITICAL: 'bg-red-900/40 text-status-critical border border-status-critical/40',
}

export function AlertBadge({ severity, className = '' }: Props) {
  return (
    <span className={`text-xs font-mono font-bold px-2 py-0.5 rounded ${styles[severity]} ${className}`}>
      {severity}
    </span>
  )
}
