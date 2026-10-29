import type { TelemetryData, AlertEvent, DeviceInfo, SystemSettings, PumpCommand, HealthResponse } from '../types'

const BASE_URL = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000'
const FRONTEND_TOKEN = (import.meta.env.VITE_FRONTEND_TOKEN as string) || ''

// Never put the device API key here — it lives only on the backend and the ESP32.

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${BASE_URL}${path}`
  const res = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? `HTTP ${res.status}`)
  }
  return res.json() as Promise<T>
}

function authHeader(): Record<string, string> {
  return FRONTEND_TOKEN ? { Authorization: `Bearer ${FRONTEND_TOKEN}` } : {}
}

// ─── Telemetry ─────────────────────────────────────────────────────────────

export const getLatestTelemetry = (deviceId?: string): Promise<TelemetryData> =>
  request<TelemetryData>(`/api/v1/telemetry/latest${deviceId ? `?device_id=${deviceId}` : ''}`)

export interface HistoryParams {
  device_id?: string
  limit?: number
  offset?: number
  since?: string
  until?: string
}

export const getTelemetryHistory = (params: HistoryParams = {}): Promise<TelemetryData[]> => {
  const q = new URLSearchParams()
  if (params.device_id) q.set('device_id', params.device_id)
  if (params.limit) q.set('limit', String(params.limit))
  if (params.offset) q.set('offset', String(params.offset))
  if (params.since) q.set('since', params.since)
  if (params.until) q.set('until', params.until)
  return request<TelemetryData[]>(`/api/v1/telemetry/history?${q}`)
}

// ─── Devices ───────────────────────────────────────────────────────────────

export const getDevices = (): Promise<DeviceInfo[]> =>
  request<DeviceInfo[]>('/api/v1/devices')

export const getDevice = (deviceId: string): Promise<DeviceInfo> =>
  request<DeviceInfo>(`/api/v1/devices/${deviceId}`)

// ─── Alerts ────────────────────────────────────────────────────────────────

export interface AlertParams {
  device_id?: string
  severity?: string
  acknowledged?: boolean
  limit?: number
}

export const getAlerts = (params: AlertParams = {}): Promise<AlertEvent[]> => {
  const q = new URLSearchParams()
  if (params.device_id) q.set('device_id', params.device_id)
  if (params.severity) q.set('severity', params.severity)
  if (params.acknowledged !== undefined) q.set('acknowledged', String(params.acknowledged))
  if (params.limit) q.set('limit', String(params.limit))
  return request<AlertEvent[]>(`/api/v1/alerts?${q}`)
}

export const acknowledgeAlert = (eventId: string): Promise<unknown> =>
  request(`/api/v1/alerts/${eventId}/ack`, {
    method: 'POST',
    headers: authHeader(),
  })

// ─── Settings ──────────────────────────────────────────────────────────────

export const getSettings = (deviceId: string): Promise<SystemSettings> =>
  request<SystemSettings>(`/api/v1/settings/${deviceId}`)

export const updateSettings = (deviceId: string, data: Partial<SystemSettings>): Promise<SystemSettings> =>
  request<SystemSettings>(`/api/v1/settings/${deviceId}`, {
    method: 'PUT',
    headers: authHeader(),
    body: JSON.stringify(data),
  })

// ─── Commands ──────────────────────────────────────────────────────────────

export const sendCommand = (deviceId: string, commandType: string): Promise<PumpCommand> =>
  request<PumpCommand>(`/api/v1/devices/${deviceId}/commands`, {
    method: 'POST',
    headers: authHeader(),
    body: JSON.stringify({ command_type: commandType }),
  })

export const getPendingCommands = (deviceId: string): Promise<PumpCommand[]> =>
  request<PumpCommand[]>(`/api/v1/devices/${deviceId}/commands/pending`)

// ─── Health ────────────────────────────────────────────────────────────────

export const getHealth = (): Promise<HealthResponse> =>
  request<HealthResponse>('/api/v1/health')
