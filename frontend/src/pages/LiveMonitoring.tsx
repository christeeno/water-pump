import { useState, useEffect, useCallback } from 'react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts'
import { useTelemetry } from '../hooks/useTelemetry'
import { SimulationBanner } from '../components/ui/SimulationBanner'
import { StatusBadge } from '../components/ui/StatusBadge'
import { LoadingSpinner } from '../components/ui/LoadingSpinner'
import { getTelemetryHistory } from '../services/api'
import type { TelemetryData } from '../types'

const RANGES = [
  { label: '5 min', minutes: 5, limit: 60 },
  { label: '15 min', minutes: 15, limit: 180 },
  { label: '1 hr', minutes: 60, limit: 720 },
  { label: '24 hr', minutes: 1440, limit: 1440 },
]

function fmt(ts: string) {
  const d = new Date(ts)
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

const CHART_STYLE = {
  contentStyle: { background: '#1a1d27', border: '1px solid #2a2d3e', borderRadius: 6, fontSize: 11 },
  labelStyle: { color: '#94a3b8', fontSize: 10 },
}

export function LiveMonitoring() {
  const { telemetry, connectionStatus } = useTelemetry()
  const [range, setRange] = useState(RANGES[1])
  const [history, setHistory] = useState<TelemetryData[]>([])
  const [loading, setLoading] = useState(true)

  const fetchHistory = useCallback(async () => {
    const since = new Date(Date.now() - range.minutes * 60 * 1000).toISOString()
    try {
      const data = await getTelemetryHistory({ since, limit: range.limit })
      setHistory(data.reverse())
    } catch {
      setHistory([])
    } finally {
      setLoading(false)
    }
  }, [range])

  useEffect(() => { fetchHistory() }, [fetchHistory])
  // Append live updates
  useEffect(() => {
    if (telemetry) {
      setHistory(prev => {
        const exists = prev.some(p => p.id === telemetry.id)
        if (exists) return prev
        const cutoff = new Date(Date.now() - range.minutes * 60 * 1000)
        const filtered = prev.filter(p => new Date(p.timestamp) > cutoff)
        return [...filtered, telemetry].slice(-range.limit)
      })
    }
  }, [telemetry, range])

  const chartData = history.map(h => ({
    time: fmt(h.timestamp),
    level: h.tank_level_valid ? h.tank_level_percent : null,
    flow: h.flow_rate_lpm,
    pressure: h.pressure_bar,
    current: h.pump_current_a,
  }))

  const sensorStatus = telemetry
    ? (() => { try { return typeof telemetry.sensor_status === 'object' && telemetry.sensor_status ? telemetry.sensor_status : JSON.parse(telemetry.sensor_status_json) } catch { return {} } })()
    : {}

  if (!telemetry && loading) return <div className="flex-1 flex items-center justify-center"><LoadingSpinner /></div>

  return (
    <div className="flex-1 overflow-auto p-4 md:p-6 space-y-4 pb-24 md:pb-6">
      {telemetry?.is_simulated && <SimulationBanner />}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-xl font-bold text-text-primary">Live Sensor Monitoring</h1>
        <div className="flex gap-1">
          {RANGES.map(r => (
            <button key={r.label} onClick={() => setRange(r)}
              className={`px-3 py-1 text-xs rounded font-mono ${range.label === r.label ? 'bg-status-water text-white' : 'bg-bg-muted text-text-muted hover:bg-border'}`}>
              {r.label}
            </button>
          ))}
        </div>
      </div>

      {/* Sensor Status Row */}
      {telemetry && (
        <div className="flex flex-wrap gap-3">
          {Object.entries(sensorStatus).map(([k, v]) => (
            <div key={k} className="flex items-center gap-2 bg-bg-card border border-border rounded-lg px-3 py-2">
              <span className="text-xs text-text-muted capitalize">{k}</span>
              <StatusBadge status={v as string} />
            </div>
          ))}
          {telemetry.raw_tank_distance_cm !== undefined && (
            <div className="flex items-center gap-2 bg-bg-card border border-border rounded-lg px-3 py-2">
              <span className="text-xs text-text-muted">Raw Distance</span>
              <span className="font-mono text-xs text-text-primary">{telemetry.raw_tank_distance_cm.toFixed(1)} cm</span>
            </div>
          )}
          <div className="flex items-center gap-2 bg-bg-card border border-border rounded-lg px-3 py-2">
            <span className="text-xs text-text-muted">Filtered Distance</span>
            <span className="font-mono text-xs text-text-primary">{telemetry.tank_distance_cm.toFixed(1)} cm</span>
          </div>
        </div>
      )}

      {/* Latest readings bar */}
      {telemetry && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: 'Tank Level', value: `${telemetry.tank_level_percent.toFixed(1)}%`, color: 'text-status-water' },
            { label: 'Flow Rate', value: `${telemetry.flow_rate_lpm.toFixed(2)} L/min`, color: 'text-status-normal' },
            { label: 'Pressure', value: `${telemetry.pressure_bar.toFixed(2)} bar`, color: 'text-purple-400' },
            { label: 'Current', value: `${telemetry.pump_current_a.toFixed(2)} A`, color: 'text-status-electric' },
          ].map(({ label, value, color }) => (
            <div key={label} className="bg-bg-card border border-border rounded-lg p-3">
              <p className="text-xs text-text-dim">{label}</p>
              <p className={`font-mono font-bold text-lg ${color}`}>{value}</p>
            </div>
          ))}
        </div>
      )}

      {chartData.length < 2 ? (
        <div className="bg-bg-card border border-border rounded-xl p-8 text-center text-text-muted text-sm">
          Waiting for data in the selected range…
        </div>
      ) : (
        <div className="space-y-4">
          {[
            { key: 'level', label: 'Tank Level (%)', color: '#06b6d4', domain: [0, 100] as [number, number] },
            { key: 'flow', label: 'Flow Rate (L/min)', color: '#22c55e', domain: [0, 'auto'] as [number, string] },
            { key: 'pressure', label: 'Pressure (bar)', color: '#a78bfa', domain: [0, 'auto'] as [number, string] },
            { key: 'current', label: 'Current (A)', color: '#3b82f6', domain: [0, 'auto'] as [number, string] },
          ].map(({ key, label, color, domain }) => (
            <div key={key} className="bg-bg-card border border-border rounded-xl p-4">
              <p className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">{label}</p>
              <ResponsiveContainer width="100%" height={160}>
                <AreaChart data={chartData} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id={`grad-${key}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={color} stopOpacity={0.25} />
                      <stop offset="95%" stopColor={color} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2a2d3e" />
                  <XAxis dataKey="time" tick={{ fill: '#64748b', fontSize: 10 }} interval="preserveStartEnd" />
                  <YAxis domain={domain} tick={{ fill: '#64748b', fontSize: 10 }} />
                  <Tooltip {...CHART_STYLE} labelFormatter={(v: string) => `Time: ${v}`} />
                  <Area type="monotone" dataKey={key} stroke={color} strokeWidth={1.5}
                    fill={`url(#grad-${key})`} dot={false} connectNulls={false} isAnimationActive={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
