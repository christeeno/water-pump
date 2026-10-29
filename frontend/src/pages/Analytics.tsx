import { useState, useEffect, useCallback } from 'react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts'
import { Download, BarChart3 } from 'lucide-react'
import { useTelemetry } from '../hooks/useTelemetry'
import { SimulationBanner } from '../components/ui/SimulationBanner'
import { LoadingSpinner } from '../components/ui/LoadingSpinner'
import { EmptyState } from '../components/ui/EmptyState'
import { getTelemetryHistory, getAlerts } from '../services/api'
import type { TelemetryData, AlertEvent } from '../types'

function toCSV(rows: TelemetryData[]): string {
  if (!rows.length) return ''
  const header = Object.keys(rows[0]).join(',')
  const data = rows.map(r => Object.values(r).join(',')).join('\n')
  return `${header}\n${data}`
}

function downloadCSV(content: string, filename: string) {
  const blob = new Blob([content], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

const CHART_STYLE = {
  contentStyle: { background: '#1a1d27', border: '1px solid #2a2d3e', borderRadius: 6, fontSize: 11 },
}

export function Analytics() {
  const { telemetry } = useTelemetry()
  const [since, setSince] = useState(() => {
    const d = new Date(); d.setDate(d.getDate() - 1); return d.toISOString().slice(0, 16)
  })
  const [until, setUntil] = useState(() => new Date().toISOString().slice(0, 16))
  const [history, setHistory] = useState<TelemetryData[]>([])
  const [alerts, setAlerts] = useState<AlertEvent[]>([])
  const [loading, setLoading] = useState(false)

  const fetch = useCallback(async () => {
    setLoading(true)
    try {
      const [hist, al] = await Promise.all([
        getTelemetryHistory({ since: new Date(since).toISOString(), until: new Date(until).toISOString(), limit: 2000 }),
        getAlerts({ limit: 200 }),
      ])
      setHistory(hist.reverse())
      setAlerts(al)
    } catch { setHistory([]) }
    finally { setLoading(false) }
  }, [since, until])

  useEffect(() => { fetch() }, [])

  const chartData = history.map(h => ({
    time: new Date(h.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    level: h.tank_level_valid ? h.tank_level_percent : null,
    flow: h.flow_rate_lpm,
    pressure: h.pressure_bar,
    current: h.pump_current_a,
    pump: h.pump_on ? 1 : 0,
  }))

  // Summary stats
  const runtimeMinutes = history.filter(h => h.pump_on).length * 0.5 / 60 // approx, assuming ~2s intervals
  const pumpStarts = history.reduce((acc, h, i) => acc + (i > 0 && h.pump_on && !history[i-1].pump_on ? 1 : 0), 0)
  const avgFlow = history.length ? history.reduce((s, h) => s + h.flow_rate_lpm, 0) / history.length : 0
  const faultCount = alerts.filter(a => a.severity === 'CRITICAL').length

  return (
    <div className="flex-1 overflow-auto p-4 md:p-6 space-y-4 pb-24 md:pb-6">
      {telemetry?.is_simulated && <SimulationBanner />}
      <h1 className="text-xl font-bold text-text-primary">Historical Analytics</h1>

      {/* Date range */}
      <div className="flex flex-wrap items-end gap-3 bg-bg-card border border-border rounded-xl p-4">
        <div>
          <label className="text-xs text-text-dim block mb-1">From</label>
          <input type="datetime-local" value={since} onChange={e => setSince(e.target.value)}
            className="bg-bg-muted border border-border rounded-lg px-3 py-1.5 text-sm text-text-primary focus:outline-none focus:border-status-water" />
        </div>
        <div>
          <label className="text-xs text-text-dim block mb-1">To</label>
          <input type="datetime-local" value={until} onChange={e => setUntil(e.target.value)}
            className="bg-bg-muted border border-border rounded-lg px-3 py-1.5 text-sm text-text-primary focus:outline-none focus:border-status-water" />
        </div>
        <button onClick={fetch}
          className="px-4 py-2 rounded-lg bg-status-water text-white text-sm font-semibold hover:bg-cyan-500 transition-colors">
          Apply
        </button>
        <button onClick={() => downloadCSV(toCSV(history), `telemetry-${since.slice(0,10)}.csv`)}
          disabled={!history.length}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-bg-muted border border-border text-text-muted text-sm hover:bg-border disabled:opacity-40 transition-colors">
          <Download size={14} /> Export CSV
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: 'Est. Runtime', value: `${runtimeMinutes.toFixed(1)}h` },
          { label: 'Pump Starts', value: pumpStarts.toString() },
          { label: 'Avg Flow', value: `${avgFlow.toFixed(2)} L/min` },
          { label: 'Critical Faults', value: faultCount.toString() },
        ].map(({ label, value }) => (
          <div key={label} className="bg-bg-card border border-border rounded-xl p-3">
            <p className="text-xs text-text-dim">{label}</p>
            <p className="font-mono font-bold text-xl text-text-primary">{value}</p>
          </div>
        ))}
      </div>

      {loading ? (
        <LoadingSpinner message="Loading history…" />
      ) : chartData.length < 2 ? (
        <EmptyState icon={<BarChart3 size={40} />} title="No data for selected range" description="Try extending the date range or run the system in simulation mode." />
      ) : (
        <div className="space-y-4">
          {[
            { key: 'level', label: 'Tank Level (%)', color: '#06b6d4' },
            { key: 'flow', label: 'Flow Rate (L/min)', color: '#22c55e' },
            { key: 'pressure', label: 'Pressure (bar)', color: '#a78bfa' },
            { key: 'current', label: 'Current (A)', color: '#3b82f6' },
          ].map(({ key, label, color }) => (
            <div key={key} className="bg-bg-card border border-border rounded-xl p-4">
              <p className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">{label}</p>
              <ResponsiveContainer width="100%" height={160}>
                <AreaChart data={chartData} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id={`hist-${key}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={color} stopOpacity={0.25} />
                      <stop offset="95%" stopColor={color} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2a2d3e" />
                  <XAxis dataKey="time" tick={{ fill: '#64748b', fontSize: 10 }} interval="preserveStartEnd" />
                  <YAxis tick={{ fill: '#64748b', fontSize: 10 }} />
                  <Tooltip {...CHART_STYLE} />
                  <Area type="monotone" dataKey={key} stroke={color} strokeWidth={1.5}
                    fill={`url(#hist-${key})`} dot={false} connectNulls={false} isAnimationActive={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
