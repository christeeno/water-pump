import type { LucideIcon } from 'lucide-react'
import type { ConnectionStatus } from '../../types'
import { Wifi, WifiOff, FlaskConical, Clock } from 'lucide-react'

interface Props {
  status: ConnectionStatus
  lastUpdate: Date | null
}

const config: Record<ConnectionStatus, { label: string; color: string; Icon: LucideIcon }> = {
  connected: { label: 'LIVE HARDWARE', color: 'text-status-normal', Icon: Wifi },
  simulated: { label: 'SIMULATION', color: 'text-status-warning', Icon: FlaskConical },
  stale: { label: 'STALE DATA', color: 'text-yellow-500', Icon: Clock },
  disconnected: { label: 'DISCONNECTED', color: 'text-status-critical', Icon: WifiOff },
}

export function ConnectionIndicator({ status, lastUpdate }: Props) {
  const { label, color, Icon } = config[status]
  const dotColor = {
    connected: 'bg-status-normal',
    simulated: 'bg-status-warning',
    stale: 'bg-yellow-500',
    disconnected: 'bg-status-critical',
  }[status]

  return (
    <div className="flex items-center gap-2">
      <div className={`w-2 h-2 rounded-full ${dotColor} ${status === 'connected' ? 'animate-pulse' : ''}`} />
      <Icon size={14} className={color} />
      <span className={`text-xs font-mono font-semibold ${color}`}>{label}</span>
      {lastUpdate && (
        <span className="text-xs text-text-dim hidden sm:block">
          {lastUpdate.toLocaleTimeString()}
        </span>
      )}
    </div>
  )
}
