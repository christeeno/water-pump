import type { SensorStatusValue } from '../../types'

interface Props {
  status: SensorStatusValue | string
  label?: string
}

const styles: Record<string, string> = {
  OK: 'bg-green-900/30 text-status-normal border-status-normal/30',
  DEGRADED: 'bg-amber-900/30 text-status-warning border-status-warning/30',
  OFFLINE: 'bg-red-900/30 text-status-critical border-status-critical/30',
}

export function StatusBadge({ status, label }: Props) {
  const style = styles[status] ?? 'bg-gray-800 text-text-muted border-border'
  return (
    <span className={`inline-flex items-center gap-1 text-xs font-mono font-semibold px-2 py-0.5 rounded border ${style}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${status === 'OK' ? 'bg-status-normal animate-pulse' : status === 'DEGRADED' ? 'bg-status-warning' : 'bg-status-critical'}`} />
      {label ?? status}
    </span>
  )
}
