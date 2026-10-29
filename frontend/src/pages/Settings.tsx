import { useState, useEffect } from 'react'
import { Save, AlertTriangle, CheckCircle } from 'lucide-react'
import { useTelemetry } from '../hooks/useTelemetry'
import { SimulationBanner } from '../components/ui/SimulationBanner'
import { LoadingSpinner } from '../components/ui/LoadingSpinner'
import { getSettings, updateSettings } from '../services/api'
import type { SystemSettings } from '../types'

const DEVICE_ID = 'esp32-water-controller-01'

interface FieldConfig {
  key: keyof SystemSettings
  label: string
  unit: string
  step: string
  min: number
  max?: number
}

const SECTIONS: { title: string; fields: FieldConfig[] }[] = [
  {
    title: 'Tank Geometry',
    fields: [
      { key: 'tank_height_cm', label: 'Tank Height', unit: 'cm', step: '1', min: 1 },
      { key: 'empty_distance_cm', label: 'Empty Reference Distance', unit: 'cm', step: '0.1', min: 0.1 },
      { key: 'full_distance_cm', label: 'Full Reference Distance', unit: 'cm', step: '0.1', min: 0.1 },
    ],
  },
  {
    title: 'Level Thresholds',
    fields: [
      { key: 'low_level_threshold', label: 'Low Level Trigger', unit: '%', step: '1', min: 1, max: 99 },
      { key: 'high_level_threshold', label: 'High Level Stop', unit: '%', step: '1', min: 1, max: 100 },
    ],
  },
  {
    title: 'Flow Settings',
    fields: [
      { key: 'min_flow_lpm', label: 'Min Flow (dry-run check)', unit: 'L/min', step: '0.1', min: 0 },
      { key: 'max_flow_lpm', label: 'Max Flow Rate', unit: 'L/min', step: '0.5', min: 0.5 },
    ],
  },
  {
    title: 'Pressure Settings',
    fields: [
      { key: 'min_pressure_bar', label: 'Min Pressure', unit: 'bar', step: '0.1', min: 0 },
      { key: 'max_pressure_bar', label: 'Max Pressure', unit: 'bar', step: '0.1', min: 0.1 },
    ],
  },
  {
    title: 'Electrical Settings',
    fields: [
      { key: 'max_current_a', label: 'Max Current', unit: 'A', step: '0.1', min: 0.1 },
    ],
  },
  {
    title: 'Advanced',
    fields: [
      { key: 'startup_grace_period_s', label: 'Startup Grace Period', unit: 's', step: '1', min: 0 },
      { key: 'sensor_timeout_s', label: 'Sensor Timeout', unit: 's', step: '1', min: 1 },
      { key: 'invalid_reading_threshold', label: 'Max Invalid Readings', unit: 'count', step: '1', min: 1 },
      { key: 'data_retention_days', label: 'Data Retention', unit: 'days', step: '1', min: 1 },
    ],
  },
]

export function Settings() {
  const { telemetry } = useTelemetry()
  const [settings, setSettings] = useState<SystemSettings | null>(null)
  const [draft, setDraft] = useState<Partial<SystemSettings>>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saved' | 'error'>('idle')
  const [errors, setErrors] = useState<Record<string, string>>({})

  useEffect(() => {
    getSettings(DEVICE_ID)
      .then(s => { setSettings(s); setDraft(s) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  function validate(d: Partial<SystemSettings>): Record<string, string> {
    const errs: Record<string, string> = {}
    const empty = Number(d.empty_distance_cm)
    const full = Number(d.full_distance_cm)
    if (!isNaN(empty) && !isNaN(full) && empty === full) errs['full_distance_cm'] = 'Cannot equal empty distance'
    const low = Number(d.low_level_threshold)
    const high = Number(d.high_level_threshold)
    if (!isNaN(low) && !isNaN(high) && low >= high) errs['high_level_threshold'] = 'Must be > low level threshold'
    const minF = Number(d.min_flow_lpm)
    const maxF = Number(d.max_flow_lpm)
    if (!isNaN(minF) && !isNaN(maxF) && minF >= maxF) errs['max_flow_lpm'] = 'Must be > min flow'
    const minP = Number(d.min_pressure_bar)
    const maxP = Number(d.max_pressure_bar)
    if (!isNaN(minP) && !isNaN(maxP) && minP >= maxP) errs['max_pressure_bar'] = 'Must be > min pressure'
    return errs
  }

  async function handleSave() {
    const errs = validate(draft)
    setErrors(errs)
    if (Object.keys(errs).length > 0) return
    setSaving(true)
    try {
      const updated = await updateSettings(DEVICE_ID, draft)
      setSettings(updated)
      setDraft(updated)
      setSaveStatus('saved')
      setTimeout(() => setSaveStatus('idle'), 4000)
    } catch (e) {
      setSaveStatus('error')
    } finally {
      setSaving(false)
    }
  }

  function onChange(key: keyof SystemSettings, raw: string) {
    const num = parseFloat(raw)
    setDraft(prev => ({ ...prev, [key]: isNaN(num) ? raw : num }))
    setErrors(prev => { const n = { ...prev }; delete n[key as string]; return n })
    setSaveStatus('idle')
  }

  if (loading) return <div className="flex-1 flex items-center justify-center"><LoadingSpinner /></div>

  return (
    <div className="flex-1 overflow-auto p-4 md:p-6 space-y-4 pb-24 md:pb-6">
      {telemetry?.is_simulated && <SimulationBanner />}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-text-primary">System Settings</h1>
        <button onClick={handleSave} disabled={saving}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-status-water text-white text-sm font-semibold hover:bg-cyan-500 disabled:opacity-50 transition-colors">
          <Save size={14} /> {saving ? 'Saving…' : 'Save Settings'}
        </button>
      </div>

      {/* Sync status notice */}
      <div className="flex items-start gap-2 bg-amber-900/20 border border-status-warning/20 rounded-xl p-3 text-xs text-status-warning">
        <AlertTriangle size={13} className="shrink-0 mt-0.5" />
        <p>
          Settings saved here are stored in the backend database. They are only applied to the ESP32 when the device
          polls for a configuration update. A change here does not guarantee immediate effect on the hardware.
        </p>
      </div>

      {saveStatus === 'saved' && (
        <div className="flex items-center gap-2 bg-green-900/20 border border-status-normal/30 rounded-xl p-3 text-xs text-status-normal">
          <CheckCircle size={13} /> Settings saved to backend. Pending ESP32 confirmation on next poll.
        </div>
      )}
      {saveStatus === 'error' && (
        <div className="flex items-center gap-2 bg-red-900/20 border border-status-critical/30 rounded-xl p-3 text-xs text-status-critical">
          <AlertTriangle size={13} /> Save failed. Check validation errors or backend connectivity.
        </div>
      )}

      <div className="space-y-5">
        {SECTIONS.map(section => (
          <div key={section.title} className="bg-bg-card border border-border rounded-xl p-4">
            <h2 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-4">{section.title}</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {section.fields.map(({ key, label, unit, step, min, max }) => (
                <div key={key as string}>
                  <label className="text-xs text-text-muted block mb-1">
                    {label} <span className="text-text-dim">({unit})</span>
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="number"
                      step={step}
                      min={min}
                      max={max}
                      value={draft[key] as number ?? ''}
                      onChange={e => onChange(key, e.target.value)}
                      className={`flex-1 bg-bg-muted border rounded-lg px-3 py-2 text-sm text-text-primary font-mono focus:outline-none focus:border-status-water transition-colors ${
                        errors[key as string] ? 'border-status-critical' : 'border-border'
                      }`}
                    />
                    <span className="flex items-center text-xs text-text-dim">{unit}</span>
                  </div>
                  {errors[key as string] && (
                    <p className="text-xs text-status-critical mt-1">{errors[key as string]}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
