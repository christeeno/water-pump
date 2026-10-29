import { useEffect, useState } from 'react'
import { Server, Wifi, WifiOff, Clock } from 'lucide-react'
import { useTelemetry } from '../hooks/useTelemetry'
import { SimulationBanner } from '../components/ui/SimulationBanner'
import { StatusBadge } from '../components/ui/StatusBadge'
import { LoadingSpinner } from '../components/ui/LoadingSpinner'
import { getDevice } from '../services/api'
import type { DeviceInfo } from '../types'

const DEVICE_ID = 'esp32-water-controller-01'
const STALE_THRESHOLD_MS = 60000

function secondsAgo(ts: string) {
  return Math.floor((Date.now() - new Date(ts).getTime()) / 1000)
}

export function DeviceStatus() {
  const { telemetry } = useTelemetry()
  const [device, setDevice] = useState<DeviceInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetch = async () => {
      try {
        const d = await getDevice(DEVICE_ID)
        setDevice(d)
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Device not found')
      } finally {
        setLoading(false)
      }
    }
    fetch()
    const t = setInterval(fetch, 10000)
    return () => clearInterval(t)
  }, [])

  if (loading) return <div className="flex-1 flex items-center justify-center"><LoadingSpinner /></div>

  const isStale = device?.last_seen ? secondsAgo(device.last_seen) > STALE_THRESHOLD_MS / 1000 : true
  const connectedAndFresh = device?.is_connected && !isStale
  const sensorHealth = device?.sensor_health ?? (telemetry
    ? (() => { try { return typeof telemetry.sensor_status === 'object' && telemetry.sensor_status ? telemetry.sensor_status : JSON.parse(telemetry.sensor_status_json) } catch { return {} } })()
    : {})

  return (
    <div className="flex-1 overflow-auto p-4 md:p-6 space-y-4 pb-24 md:pb-6">
      {telemetry?.is_simulated && <SimulationBanner />}
      <h1 className="text-xl font-bold text-text-primary">Device Status</h1>

      {error && (
        <div className="bg-red-900/20 border border-status-critical/30 rounded-xl p-4 text-status-critical text-sm">{error}</div>
      )}

      {/* Device info card */}
      <div className={`bg-bg-card border rounded-xl p-5 ${connectedAndFresh ? 'border-status-normal/30' : isStale ? 'border-yellow-500/40' : 'border-status-critical/40'}`}>
        <div className="flex items-center gap-3 mb-4">
          <Server size={22} className="text-status-water" />
          <div>
            <p className="font-mono font-bold text-text-primary">{DEVICE_ID}</p>
            <p className="text-xs text-text-dim">ESP32 Water Controller</p>
          </div>
          <div className="ml-auto">
            {connectedAndFresh
              ? <div className="flex items-center gap-2 text-status-normal text-sm"><Wifi size={16} /><span className="font-bold">CONNECTED</span></div>
              : isStale
              ? <div className="flex items-center gap-2 text-yellow-500 text-sm"><Clock size={16} /><span className="font-bold">STALE</span></div>
              : <div className="flex items-center gap-2 text-status-critical text-sm"><WifiOff size={16} /><span className="font-bold">OFFLINE</span></div>
            }
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 text-sm">
          <div className="bg-bg-muted rounded-lg px-3 py-2">
            <p className="text-text-dim text-xs">Firmware</p>
            <p className="font-mono text-text-primary">{device?.firmware_version ?? 'Unknown'}</p>
          </div>
          <div className="bg-bg-muted rounded-lg px-3 py-2">
            <p className="text-text-dim text-xs">Controller State</p>
            <p className="font-mono text-text-primary">{device?.controller_state ?? telemetry?.controller_state ?? '—'}</p>
          </div>
          <div className="bg-bg-muted rounded-lg px-3 py-2">
            <p className="text-text-dim text-xs">Last Seen</p>
            <p className="font-mono text-text-primary text-xs">
              {device?.last_seen ? new Date(device.last_seen).toLocaleString() : '—'}
            </p>
          </div>
          <div className="bg-bg-muted rounded-lg px-3 py-2">
            <p className="text-text-dim text-xs">Last Telemetry</p>
            <p className="font-mono text-text-primary text-xs">
              {device?.last_telemetry_at ? new Date(device.last_telemetry_at).toLocaleString() : '—'}
            </p>
          </div>
        </div>
      </div>

      {/* Sensor health */}
      <div>
        <h2 className="text-sm font-semibold text-text-muted uppercase tracking-wider mb-3">Sensor Health</h2>
        <div className="grid grid-cols-2 gap-3">
          {Object.entries(sensorHealth).map(([sensor, status]) => (
            <div key={sensor}
              className={`bg-bg-card border rounded-xl p-4 ${status === 'OK' ? 'border-status-normal/20' : status === 'DEGRADED' ? 'border-status-warning/30' : 'border-status-critical/30'}`}>
              <p className="text-xs text-text-dim capitalize mb-2">{sensor} Sensor</p>
              <StatusBadge status={status as string} label={status as string} />
            </div>
          ))}
        </div>
      </div>

      {/* Connectivity legend */}
      <div className="bg-bg-card border border-border rounded-xl p-4">
        <p className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">Connectivity Legend</p>
        <div className="space-y-2 text-xs text-text-muted">
          <div className="flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-status-normal" />Connected — telemetry received within the last 60 seconds</div>
          <div className="flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-yellow-500" />Stale — last telemetry was &gt;60 seconds ago, device may be offline</div>
          <div className="flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-status-critical" />Offline — device not responding</div>
          <div className="flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-status-warning" />Sensors Degraded — device connected but sensor readings unreliable</div>
        </div>
      </div>
    </div>
  )
}
