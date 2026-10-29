import { useState, useEffect, useRef } from 'react'
import { Droplets, Wind, Gauge, Zap, Power, ShieldCheck, Clock } from 'lucide-react'
import type { TelemetryData, ConnectionStatus } from '../types'
import { useTelemetry, useAlerts } from '../hooks/useTelemetry'
import { SimulationBanner } from '../components/ui/SimulationBanner'
import { MetricCard } from '../components/ui/MetricCard'
import { TankGraphic } from '../components/ui/TankGraphic'
import { TrendChart } from '../components/ui/TrendChart'
import { StatusBadge } from '../components/ui/StatusBadge'
import { AlertBadge } from '../components/ui/AlertBadge'
import { LoadingSpinner } from '../components/ui/LoadingSpinner'

const MAX_TREND = 30

function useTrend(value: number | undefined) {
  const [history, setHistory] = useState<{ value: number }[]>([])
  useEffect(() => {
    if (value !== undefined) {
      setHistory(prev => [...prev.slice(-(MAX_TREND - 1)), { value }])
    }
  }, [value])
  return history
}

function parseStatus(t: TelemetryData) {
  try {
    return typeof t.sensor_status === 'object' && t.sensor_status
      ? t.sensor_status
      : JSON.parse(t.sensor_status_json ?? '{}')
  } catch { return { ultrasonic: 'OFFLINE', flow: 'OFFLINE', pressure: 'OFFLINE', current: 'OFFLINE' } }
}

function runtimeDisplay(startTime: Date | null): string {
  if (!startTime) return '—'
  const secs = Math.floor((Date.now() - startTime.getTime()) / 1000)
  const h = Math.floor(secs / 3600).toString().padStart(2, '0')
  const m = Math.floor((secs % 3600) / 60).toString().padStart(2, '0')
  const s = (secs % 60).toString().padStart(2, '0')
  return `${h}:${m}:${s}`
}

export function Dashboard() {
  const { telemetry, connectionStatus, lastUpdate } = useTelemetry()
  const { alerts, unreadCount } = useAlerts()

  const levelTrend = useTrend(telemetry?.tank_level_percent)
  const flowTrend = useTrend(telemetry?.flow_rate_lpm)
  const pressureTrend = useTrend(telemetry?.pressure_bar)
  const currentTrend = useTrend(telemetry?.pump_current_a)

  const pumpStartRef = useRef<Date | null>(null)
  const [runtime, setRuntime] = useState('—')
  useEffect(() => {
    if (telemetry?.pump_on) {
      if (!pumpStartRef.current) pumpStartRef.current = new Date()
    } else {
      pumpStartRef.current = null
    }
  }, [telemetry?.pump_on])
  useEffect(() => {
    const t = setInterval(() => setRuntime(runtimeDisplay(pumpStartRef.current)), 1000)
    return () => clearInterval(t)
  }, [])

  if (!telemetry) {
    return (
      <div className="flex-1 flex items-center justify-center">
        {connectionStatus === 'disconnected'
          ? <div className="text-center p-8">
              <p className="text-status-critical font-semibold mb-2">Backend Unavailable</p>
              <p className="text-text-muted text-sm">Ensure the backend is running on port 8000.</p>
            </div>
          : <LoadingSpinner message="Connecting to backend…" />
        }
      </div>
    )
  }

  const sensorStatus = parseStatus(telemetry)
  const levelStatus = telemetry.tank_level_percent >= 90 ? 'normal'
    : telemetry.tank_level_percent <= 20 ? 'critical' : 'normal'
  const allSensorsOk = Object.values(sensorStatus).every(v => v === 'OK')

  return (
    <div className="flex-1 overflow-auto p-4 md:p-6 space-y-4 pb-24 md:pb-6">
      {telemetry.is_simulated && <SimulationBanner />}

      <h1 className="text-xl font-bold text-text-primary">Overview Dashboard</h1>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">

        {/* Water Tank Level */}
        <MetricCard
          title="Water Tank Level"
          icon={<Droplets size={14} />}
          status={levelStatus}
          className="sm:row-span-2"
        >
          <div className="flex items-center gap-6">
            <TankGraphic levelPercent={telemetry.tank_level_percent} isValid={telemetry.tank_level_valid} />
            <div className="space-y-2 text-sm">
              <div>
                <p className="text-text-dim text-xs">Level</p>
                <p className="font-mono font-bold text-2xl text-status-water">{telemetry.tank_level_percent.toFixed(1)}%</p>
              </div>
              <div>
                <p className="text-text-dim text-xs">Distance</p>
                <p className="font-mono text-text-primary">{telemetry.tank_distance_cm.toFixed(1)} cm</p>
              </div>
              {telemetry.raw_tank_distance_cm !== undefined && (
                <div>
                  <p className="text-text-dim text-xs">Raw</p>
                  <p className="font-mono text-text-muted text-sm">{telemetry.raw_tank_distance_cm.toFixed(1)} cm</p>
                </div>
              )}
              <StatusBadge status={sensorStatus.ultrasonic} label={`Ultrasonic: ${sensorStatus.ultrasonic}`} />
            </div>
          </div>
          <TrendChart data={levelTrend} color="#06b6d4" />
        </MetricCard>

        {/* Flow Rate */}
        <MetricCard
          title="Flow Rate"
          icon={<Wind size={14} />}
          value={telemetry.flow_rate_lpm.toFixed(2)}
          unit="L/min"
          status={sensorStatus.flow === 'OK' ? 'normal' : 'warning'}
          badge={<StatusBadge status={sensorStatus.flow} />}
        >
          <TrendChart data={flowTrend} color="#22c55e" />
        </MetricCard>

        {/* Water Pressure */}
        <MetricCard
          title="Water Pressure"
          icon={<Gauge size={14} />}
          value={telemetry.pressure_bar.toFixed(2)}
          unit="bar"
          status={sensorStatus.pressure === 'OK' ? 'normal' : 'warning'}
          badge={<StatusBadge status={sensorStatus.pressure} />}
        >
          <TrendChart data={pressureTrend} color="#a78bfa" />
        </MetricCard>

        {/* Pump Current */}
        <MetricCard
          title="Pump Current"
          icon={<Zap size={14} />}
          value={telemetry.pump_current_a.toFixed(2)}
          unit="A"
          status={sensorStatus.current === 'OK' ? 'normal' : 'warning'}
          badge={<StatusBadge status={sensorStatus.current} />}
        >
          <TrendChart data={currentTrend} color="#3b82f6" />
        </MetricCard>

        {/* Pump Status */}
        <MetricCard title="Pump Status" icon={<Power size={14} />}>
          <div className="flex items-center gap-3">
            <div className={`w-5 h-5 rounded-full ${telemetry.pump_on ? 'bg-status-normal animate-pulse' : 'bg-border'}`} />
            <span className={`text-xl font-mono font-bold ${telemetry.pump_on ? 'text-status-normal' : 'text-text-muted'}`}>
              {telemetry.pump_on ? 'RUNNING' : 'STOPPED'}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs mt-1">
            <div><p className="text-text-dim">Mode</p><p className="font-mono font-bold text-status-water">{telemetry.mode}</p></div>
            <div><p className="text-text-dim">State</p><p className="font-mono font-bold">{telemetry.controller_state}</p></div>
            <div className="flex items-center gap-1"><Clock size={11} className="text-text-dim" /><p className="text-text-dim">Runtime</p></div>
            <p className="font-mono text-text-primary">{runtime}</p>
          </div>
        </MetricCard>

        {/* System Health */}
        <MetricCard title="System Health" icon={<ShieldCheck size={14} />}
          status={allSensorsOk ? 'normal' : 'warning'}>
          <div className="space-y-2">
            <div className="flex justify-between text-xs">
              <span className="text-text-dim">ESP32</span>
              <StatusBadge status={connectionStatus === 'connected' || connectionStatus === 'simulated' ? 'OK' : 'OFFLINE'} />
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-text-dim">Last update</span>
              <span className="font-mono text-text-muted text-[11px]">{lastUpdate?.toLocaleTimeString() ?? '—'}</span>
            </div>
            <div className="grid grid-cols-2 gap-1 mt-2">
              {Object.entries(sensorStatus).map(([k, v]) => (
                <div key={k} className="flex justify-between bg-bg-muted rounded px-2 py-1">
                  <span className="text-text-dim text-[11px] capitalize">{k}</span>
                  <StatusBadge status={v as string} />
                </div>
              ))}
            </div>
            <div className="flex justify-between text-xs mt-1">
              <span className="text-text-dim">Active alerts</span>
              {unreadCount > 0
                ? <AlertBadge severity="WARNING" />
                : <span className="text-status-normal text-xs">None</span>
              }
            </div>
          </div>
        </MetricCard>

      </div>
    </div>
  )
}
