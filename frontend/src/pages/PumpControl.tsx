import { useState } from 'react'
import { Power, AlertTriangle, CheckCircle, Clock } from 'lucide-react'
import { useTelemetry } from '../hooks/useTelemetry'
import { SimulationBanner } from '../components/ui/SimulationBanner'
import { ConfirmDialog } from '../components/ui/ConfirmDialog'
import { LoadingSpinner } from '../components/ui/LoadingSpinner'
import { sendCommand } from '../services/api'
import type { PumpCommand } from '../types'

const DEVICE_ID = 'esp32-water-controller-01'

export function PumpControl() {
  const { telemetry } = useTelemetry()
  const [lastCommand, setLastCommand] = useState<PumpCommand | null>(null)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [pendingCmd, setPendingCmd] = useState<string | null>(null)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function issueCommand(cmdType: string) {
    setSending(true)
    setError(null)
    try {
      const cmd = await sendCommand(DEVICE_ID, cmdType)
      setLastCommand(cmd)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Command failed')
    } finally {
      setSending(false)
    }
  }

  function handlePumpOn() { setPendingCmd('PUMP_ON'); setConfirmOpen(true) }
  function handlePumpOff() { issueCommand('PUMP_OFF') }
  function handleModeAuto() { issueCommand('SET_MODE_AUTO') }
  function handleModeManual() { issueCommand('SET_MODE_MANUAL') }

  if (!telemetry) return <div className="flex-1 flex items-center justify-center"><LoadingSpinner /></div>

  const isManual = telemetry.mode === 'MANUAL'
  const pumpOn = telemetry.pump_on

  return (
    <div className="flex-1 overflow-auto p-4 md:p-6 space-y-5 pb-24 md:pb-6">
      {telemetry.is_simulated && <SimulationBanner />}

      <h1 className="text-xl font-bold text-text-primary">Pump Control</h1>

      {/* Safety notice */}
      <div className="flex items-start gap-3 bg-amber-900/20 border border-status-warning/30 rounded-xl p-4 text-sm text-status-warning">
        <AlertTriangle size={18} className="shrink-0 mt-0.5" />
        <div>
          <p className="font-bold mb-1">Hardware Safety Notice</p>
          <p className="text-xs leading-relaxed">
            Manual commands are queued and sent to the ESP32. The firmware enforces all hardware interlocks,
            emergency shutdowns, and source-water protection independently. A command issued here does not
            guarantee immediate execution — the device reports its actual state after acknowledgement.
          </p>
        </div>
      </div>

      {/* Pump status */}
      <div className="bg-bg-card border border-border rounded-xl p-6">
        <div className="flex items-center gap-4 mb-6">
          <div className={`w-10 h-10 rounded-full flex items-center justify-center ${pumpOn ? 'bg-status-normal/20' : 'bg-border'}`}>
            <Power size={20} className={pumpOn ? 'text-status-normal' : 'text-text-dim'} />
          </div>
          <div>
            <p className={`text-3xl font-mono font-bold ${pumpOn ? 'text-status-normal' : 'text-text-muted'}`}>
              {pumpOn ? 'RUNNING' : 'STOPPED'}
            </p>
            <p className="text-xs text-text-dim">Controller state: <span className="font-mono text-text-muted">{telemetry.controller_state}</span></p>
          </div>
        </div>

        {/* Mode toggle */}
        <div className="mb-6">
          <p className="text-xs text-text-dim mb-2 font-semibold">Operating Mode</p>
          <div className="flex gap-2">
            <button onClick={handleModeAuto} disabled={sending || !isManual}
              className={`px-5 py-2 rounded-lg text-sm font-bold transition-all ${!isManual ? 'bg-status-water text-white' : 'bg-bg-muted text-text-muted hover:bg-border'}`}>
              AUTO
            </button>
            <button onClick={handleModeManual} disabled={sending || isManual}
              className={`px-5 py-2 rounded-lg text-sm font-bold transition-all ${isManual ? 'bg-purple-600 text-white' : 'bg-bg-muted text-text-muted hover:bg-border'}`}>
              MANUAL
            </button>
          </div>
        </div>

        {/* Manual controls */}
        {isManual && (
          <div>
            <p className="text-xs text-text-dim mb-2 font-semibold">Manual Control</p>
            <div className="flex gap-3">
              <button onClick={handlePumpOn} disabled={sending || pumpOn}
                className="flex-1 py-3 rounded-xl font-bold text-sm bg-status-normal/80 hover:bg-status-normal text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors">
                {sending ? 'Sending…' : 'PUMP ON'}
              </button>
              <button onClick={handlePumpOff} disabled={sending || !pumpOn}
                className="flex-1 py-3 rounded-xl font-bold text-sm bg-status-critical/80 hover:bg-status-critical text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors">
                PUMP OFF
              </button>
            </div>
          </div>
        )}

        {!isManual && (
          <p className="text-xs text-text-dim italic mt-2">
            Switch to MANUAL mode to control the pump directly.
          </p>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 bg-red-900/20 border border-status-critical/30 rounded-lg p-3 text-status-critical text-sm">
          <AlertTriangle size={14} /> {error}
        </div>
      )}

      {/* Last command status */}
      {lastCommand && (
        <div className="bg-bg-card border border-border rounded-xl p-4 space-y-2 text-sm">
          <p className="font-semibold text-text-primary flex items-center gap-2">
            <Clock size={14} className="text-text-dim" /> Last Command Status
          </p>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div><span className="text-text-dim">Type: </span><span className="font-mono text-status-water">{lastCommand.command_type}</span></div>
            <div><span className="text-text-dim">ID: </span><span className="font-mono text-text-muted">{lastCommand.command_id.slice(0, 8)}…</span></div>
            <div><span className="text-text-dim">Issued: </span><span className="font-mono">{new Date(lastCommand.issued_at).toLocaleTimeString()}</span></div>
            <div><span className="text-text-dim">Expires: </span><span className="font-mono">{new Date(lastCommand.expires_at).toLocaleTimeString()}</span></div>
            <div className="col-span-2 flex items-center gap-2">
              <span className="text-text-dim">Acknowledged: </span>
              {lastCommand.acknowledged
                ? <><CheckCircle size={13} className="text-status-normal" /><span className="text-status-normal">Yes</span></>
                : <span className="text-status-warning">Pending ESP32 response…</span>
              }
            </div>
          </div>
          {lastCommand.device_reported_state && (
            <p className="text-xs text-text-dim">
              Device reported: <span className="font-mono text-text-primary">{lastCommand.device_reported_state}</span>
            </p>
          )}
        </div>
      )}

      {/* Confirm dialog */}
      <ConfirmDialog
        isOpen={confirmOpen}
        title="Start Pump"
        message="Are you sure you want to start the pump manually? Hardware safety interlocks remain active and may prevent operation if conditions are not met."
        confirmLabel="Start Pump"
        cancelLabel="Cancel"
        onConfirm={() => { setConfirmOpen(false); if (pendingCmd) issueCommand(pendingCmd) }}
        onCancel={() => { setConfirmOpen(false); setPendingCmd(null) }}
      />
    </div>
  )
}
