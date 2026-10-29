import { useState, useEffect, useRef, useCallback } from 'react'
import type { TelemetryData, AlertEvent, ConnectionStatus } from '../types'
import { dashboardWS } from '../services/websocket'
import { getLatestTelemetry } from '../services/api'

const WS_URL = `${(import.meta.env.VITE_WS_URL as string) || 'ws://localhost:8000'}/ws/dashboard`

export function useTelemetry() {
  const [telemetry, setTelemetry] = useState<TelemetryData | null>(null)
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected')
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null)
  const staleTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const pollTimer = useRef<ReturnType<typeof setInterval> | null>(null)

  const markStale = useCallback(() => {
    setConnectionStatus(prev => (prev === 'connected' || prev === 'simulated') ? 'stale' : prev)
  }, [])

  const resetStaleTimer = useCallback(() => {
    if (staleTimer.current) clearTimeout(staleTimer.current)
    staleTimer.current = setTimeout(markStale, 15000)
  }, [markStale])

  const applyTelemetry = useCallback((t: TelemetryData) => {
    // Parse sensor_status from JSON string if not already an object
    if (typeof t.sensor_status_json === 'string' && !t.sensor_status) {
      try {
        t.sensor_status = JSON.parse(t.sensor_status_json)
      } catch { /* ignore */ }
    }
    setTelemetry(t)
    setLastUpdate(new Date())
    setConnectionStatus(t.is_simulated ? 'simulated' : 'connected')
    resetStaleTimer()
  }, [resetStaleTimer])

  // Polling fallback (every 5s) for when WebSocket is unavailable
  const startPolling = useCallback(() => {
    if (pollTimer.current) return
    pollTimer.current = setInterval(async () => {
      try {
        const t = await getLatestTelemetry()
        applyTelemetry(t)
      } catch {
        setConnectionStatus('disconnected')
      }
    }, 5000)
  }, [applyTelemetry])

  useEffect(() => {
    // Initial fetch
    getLatestTelemetry()
      .then(applyTelemetry)
      .catch(() => setConnectionStatus('disconnected'))

    // Connect WebSocket
    dashboardWS.connect(WS_URL)
    const remove = dashboardWS.addListener(msg => {
      if (msg.type === 'telemetry_update' && msg.data) {
        applyTelemetry(msg.data)
      }
    })

    // Start polling as a fallback
    startPolling()

    return () => {
      remove()
      dashboardWS.disconnect()
      if (staleTimer.current) clearTimeout(staleTimer.current)
      if (pollTimer.current) clearInterval(pollTimer.current)
    }
  }, [applyTelemetry, startPolling])

  return { telemetry, connectionStatus, lastUpdate }
}

// ─── Alerts hook ────────────────────────────────────────────────────────────

import { getAlerts, acknowledgeAlert as ackAlertApi } from '../services/api'

export function useAlerts() {
  const [alerts, setAlerts] = useState<AlertEvent[]>([])
  const [loading, setLoading] = useState(true)

  const fetchAlerts = useCallback(async () => {
    try {
      const data = await getAlerts({ limit: 100 })
      setAlerts(data)
    } catch {
      // keep stale data
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchAlerts()
    // Refresh every 10 seconds
    const t = setInterval(fetchAlerts, 10000)
    // Also subscribe to WebSocket for live alerts
    const remove = dashboardWS.addListener(msg => {
      if (msg.type === 'alert' && msg.alert) {
        setAlerts(prev => [msg.alert!, ...prev.slice(0, 99)])
      }
    })
    return () => {
      clearInterval(t)
      remove()
    }
  }, [fetchAlerts])

  const acknowledgeAlert = useCallback(async (eventId: string) => {
    try {
      await ackAlertApi(eventId)
      setAlerts(prev =>
        prev.map(a => a.event_id === eventId ? { ...a, acknowledged: true, acknowledged_at: new Date().toISOString() } : a)
      )
    } catch (e) {
      console.error('Ack failed', e)
    }
  }, [])

  const unreadCount = alerts.filter(a => !a.acknowledged).length

  return { alerts, loading, unreadCount, acknowledgeAlert, refetch: fetchAlerts }
}
