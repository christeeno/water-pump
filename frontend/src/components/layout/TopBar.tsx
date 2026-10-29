import { useState, useEffect } from 'react'
import { Bell } from 'lucide-react'
import type { ConnectionStatus } from '../../types'
import { ConnectionIndicator } from '../ui/ConnectionIndicator'

interface Props {
  connectionStatus: ConnectionStatus
  lastUpdate: Date | null
  unreadAlerts: number
  isSimulated: boolean
}

export function TopBar({ connectionStatus, lastUpdate, unreadAlerts, isSimulated }: Props) {
  const [now, setNow] = useState(new Date())

  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(t)
  }, [])

  return (
    <header className="sticky top-0 z-30 bg-bg/90 backdrop-blur border-b border-border px-4 py-3 flex items-center justify-between gap-4">
      {/* Left: title on mobile */}
      <div className="flex items-center gap-2 md:hidden">
        <span className="font-bold text-sm text-text-primary">AquaMonitor</span>
      </div>

      {/* Center: simulation badge */}
      {isSimulated && (
        <div className="hidden sm:flex items-center gap-1 px-2 py-1 rounded bg-amber-900/30 border border-status-warning/30 text-status-warning text-xs font-bold">
          SIMULATION
        </div>
      )}

      {/* Right cluster */}
      <div className="flex items-center gap-4 ml-auto">
        <ConnectionIndicator status={connectionStatus} lastUpdate={lastUpdate} />
        <div className="relative">
          <Bell size={18} className="text-text-muted" />
          {unreadAlerts > 0 && (
            <span className="absolute -top-1.5 -right-1.5 w-4 h-4 rounded-full bg-status-critical text-white text-[9px] font-bold flex items-center justify-center">
              {unreadAlerts > 9 ? '9+' : unreadAlerts}
            </span>
          )}
        </div>
        <span className="text-xs font-mono text-text-dim hidden lg:block">
          {now.toLocaleTimeString()}
        </span>
      </div>
    </header>
  )
}
