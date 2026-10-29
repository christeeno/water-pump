// ─── Sensor & Telemetry ────────────────────────────────────────────────────

export type SensorStatusValue = 'OK' | 'DEGRADED' | 'OFFLINE';
export type ControllerState = 'IDLE' | 'FILLING' | 'VERIFY' | 'FAULT';
export type PumpMode = 'AUTO' | 'MANUAL';
export type Severity = 'INFO' | 'WARNING' | 'CRITICAL';
export type ConnectionStatus = 'connected' | 'disconnected' | 'simulated' | 'stale';

export interface SensorStatus {
  ultrasonic: SensorStatusValue;
  flow: SensorStatusValue;
  pressure: SensorStatusValue;
  current: SensorStatusValue;
}

export interface TelemetryData {
  id: number;
  device_id: string;
  timestamp: string;
  tank_distance_cm: number;
  tank_level_percent: number;
  flow_rate_lpm: number;
  pressure_bar: number;
  pump_current_a: number;
  pump_on: boolean;
  mode: PumpMode;
  controller_state: ControllerState;
  sensor_status_json: string;
  sensor_status?: SensorStatus;
  is_simulated: boolean;
  raw_tank_distance_cm?: number;
  tank_level_valid: boolean;
}

// ─── Alerts ────────────────────────────────────────────────────────────────

export interface AlertEvent {
  id: number;
  event_id: string;
  timestamp: string;
  severity: Severity;
  fault_category: string;
  description: string;
  sensor_evidence_json: string;
  sensor_evidence?: Record<string, unknown>;
  pump_state: boolean;
  recommended_action: string;
  acknowledged: boolean;
  acknowledged_at?: string;
  device_id: string;
}

// ─── Device ────────────────────────────────────────────────────────────────

export interface DeviceInfo {
  device_id: string;
  firmware_version: string;
  last_seen: string;
  last_telemetry_at: string;
  is_connected: boolean;
  controller_state: ControllerState;
  sensor_health: Record<string, string>;
}

// ─── Settings ──────────────────────────────────────────────────────────────

export interface SystemSettings {
  id: number;
  device_id: string;
  tank_height_cm: number;
  empty_distance_cm: number;
  full_distance_cm: number;
  low_level_threshold: number;
  high_level_threshold: number;
  min_flow_lpm: number;
  max_flow_lpm: number;
  min_pressure_bar: number;
  max_pressure_bar: number;
  max_current_a: number;
  startup_grace_period_s: number;
  sensor_timeout_s: number;
  invalid_reading_threshold: number;
  data_retention_days: number;
  updated_at: string;
}

// ─── Commands ──────────────────────────────────────────────────────────────

export type CommandType = 'PUMP_ON' | 'PUMP_OFF' | 'SET_MODE_AUTO' | 'SET_MODE_MANUAL';

export interface PumpCommand {
  id: number;
  command_id: string;
  device_id: string;
  command_type: CommandType;
  issued_at: string;
  expires_at: string;
  acknowledged: boolean;
  acknowledged_at?: string;
  device_reported_state?: string;
  issued_by: string;
}

// ─── WebSocket message ─────────────────────────────────────────────────────

export interface WsMessage {
  type: 'telemetry_update' | 'alert' | 'ping';
  data?: TelemetryData;
  alert?: AlertEvent;
  timestamp?: string;
}

// ─── API responses ─────────────────────────────────────────────────────────

export interface ApiError {
  detail: string;
}

export interface HealthResponse {
  status: string;
  database: string;
  simulation_mode: boolean;
  timestamp: string;
  active_connections: number;
}
