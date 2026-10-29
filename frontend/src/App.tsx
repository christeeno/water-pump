import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Sidebar } from './components/layout/Sidebar'
import { TopBar } from './components/layout/TopBar'
import { MobileNav } from './components/layout/MobileNav'
import { Dashboard } from './pages/Dashboard'
import { LiveMonitoring } from './pages/LiveMonitoring'
import { PumpControl } from './pages/PumpControl'
import { FaultsAlerts } from './pages/FaultsAlerts'
import { Analytics } from './pages/Analytics'
import { DeviceStatus } from './pages/DeviceStatus'
import { Settings } from './pages/Settings'
import { useTelemetry, useAlerts } from './hooks/useTelemetry'

function AppShell() {
  const { connectionStatus, lastUpdate, telemetry } = useTelemetry()
  const { unreadCount } = useAlerts()

  return (
    <div className="flex h-screen overflow-hidden bg-bg">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <TopBar
          connectionStatus={connectionStatus}
          lastUpdate={lastUpdate}
          unreadAlerts={unreadCount}
          isSimulated={telemetry?.is_simulated ?? false}
        />
        <main className="flex-1 overflow-hidden flex flex-col">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/monitoring" element={<LiveMonitoring />} />
            <Route path="/pump-control" element={<PumpControl />} />
            <Route path="/faults" element={<FaultsAlerts />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/device" element={<DeviceStatus />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
        <MobileNav />
      </div>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AppShell />
    </BrowserRouter>
  )
}
