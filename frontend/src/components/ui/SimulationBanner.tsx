import { AlertTriangle } from 'lucide-react'

export function SimulationBanner() {
  return (
    <div className="flex items-center gap-2 px-4 py-2 bg-amber-900/30 border border-status-warning/40 rounded-lg text-status-warning text-sm font-medium">
      <AlertTriangle size={16} className="shrink-0" />
      <span>
        <strong>SIMULATION MODE</strong> — Data shown is synthetically generated for demonstration.
        No physical ESP32 hardware is connected.
      </span>
    </div>
  )
}
