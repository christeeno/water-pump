import { useState } from 'react'
import { Check, Filter, Bell } from 'lucide-react'
import { useAlerts } from '../hooks/useTelemetry'
import { useTelemetry } from '../hooks/useTelemetry'
import { SimulationBanner } from '../components/ui/SimulationBanner'
import { AlertBadge } from '../components/ui/AlertBadge'
import { EmptyState } from '../components/ui/EmptyState'
import { LoadingSpinner } from '../components/ui/LoadingSpinner'
import type { AlertEvent, Severity } from '../types'

function timeAgo(ts: string): string {
  const diff = Math.floor((Date.now() - new Date(ts).getTime()) / 1000)
  if (diff < 60) return `${diff}s ago`
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  return `${Math.floor(diff / 3600)}h ago`
}

export function FaultsAlerts() {
  const { alerts, loading, acknowledgeAlert } = useAlerts()
  const { telemetry } = useTelemetry()
  const [filterSeverity, setFilterSeverity] = useState<Severity | 'ALL'>('ALL')
  const [filterAck, setFilterAck] = useState<'ALL' | 'UNACKED' | 'ACKED'>('ALL')

  const filtered = alerts.filter(a => {
    if (filterSeverity !== 'ALL' && a.severity !== filterSeverity) return false
    if (filterAck === 'UNACKED' && a.acknowledged) return false
    if (filterAck === 'ACKED' && !a.acknowledged) return false
    return true
  })

  const unacked = alerts.filter(a => !a.acknowledged)

  if (loading) return <div className="flex-1 flex items-center justify-center"><LoadingSpinner /></div>

  return (
    <div className="flex-1 overflow-auto p-4 md:p-6 space-y-4 pb-24 md:pb-6">
      {telemetry?.is_simulated && <SimulationBanner />}

      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-text-primary">Faults & Alerts</h1>
          {unacked.length > 0 && (
            <p className="text-xs text-status-critical mt-0.5">{unacked.length} unacknowledged alert{unacked.length !== 1 ? 's' : ''}</p>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2 items-center">
        <Filter size={14} className="text-text-dim" />
        <div className="flex gap-1">
          {(['ALL', 'CRITICAL', 'WARNING', 'INFO'] as const).map(s => (
            <button key={s} onClick={() => setFilterSeverity(s)}
              className={`px-3 py-1 text-xs rounded font-mono transition-colors ${filterSeverity === s ? 'bg-status-water text-white' : 'bg-bg-muted text-text-muted hover:bg-border'}`}>
              {s}
            </button>
          ))}
        </div>
        <div className="flex gap-1 ml-2">
          {(['ALL', 'UNACKED', 'ACKED'] as const).map(f => (
            <button key={f} onClick={() => setFilterAck(f)}
              className={`px-3 py-1 text-xs rounded font-mono transition-colors ${filterAck === f ? 'bg-bg-muted text-text-primary border border-border' : 'text-text-dim hover:bg-bg-muted'}`}>
              {f}
            </button>
          ))}
        </div>
      </div>

      {filtered.length === 0 ? (
        <EmptyState icon={<Bell size={40} />} title="No alerts" description="No alerts matching the current filters." />
      ) : (
        <div className="space-y-2">
          {/* Unacknowledged first */}
          {filtered
            .sort((a, b) => {
              if (a.acknowledged !== b.acknowledged) return a.acknowledged ? 1 : -1
              return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
            })
            .map((alert: AlertEvent) => (
              <div key={alert.event_id}
                className={`bg-bg-card border rounded-xl p-4 transition-all ${
                  !alert.acknowledged
                    ? alert.severity === 'CRITICAL' ? 'border-status-critical/50' : 'border-status-warning/40'
                    : 'border-border opacity-70'
                }`}>
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <AlertBadge severity={alert.severity} />
                      <span className="text-xs font-mono text-text-muted">{alert.fault_category}</span>
                      <span className="text-xs text-text-dim ml-auto">{timeAgo(alert.timestamp)}</span>
                    </div>
                    <p className="text-sm text-text-primary font-medium">{alert.description}</p>
                    <p className="text-xs text-text-muted mt-1">{alert.recommended_action}</p>
                    {alert.sensor_evidence && Object.keys(alert.sensor_evidence).length > 0 && (
                      <div className="mt-2 text-xs text-text-dim font-mono bg-bg-muted rounded px-2 py-1">
                        {JSON.stringify(alert.sensor_evidence)}
                      </div>
                    )}
                  </div>
                  {!alert.acknowledged && (
                    <button onClick={() => acknowledgeAlert(alert.event_id)}
                      className="shrink-0 flex items-center gap-1 px-3 py-1.5 text-xs rounded-lg bg-bg-muted hover:bg-border text-text-muted transition-colors">
                      <Check size={12} /> Ack
                    </button>
                  )}
                  {alert.acknowledged && (
                    <div className="shrink-0 flex items-center gap-1 text-xs text-status-normal">
                      <Check size={12} /> ACK'd
                    </div>
                  )}
                </div>
              </div>
            ))
          }
        </div>
      )}
    </div>
  )
}
