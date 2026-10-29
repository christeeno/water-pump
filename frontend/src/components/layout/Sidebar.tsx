import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Activity, Gauge, AlertTriangle,
  BarChart3, Server, Settings, Droplets
} from 'lucide-react'

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/monitoring', label: 'Live Monitoring', icon: Activity },
  { to: '/pump-control', label: 'Pump Control', icon: Gauge },
  { to: '/faults', label: 'Faults & Alerts', icon: AlertTriangle },
  { to: '/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/device', label: 'Device Status', icon: Server },
  { to: '/settings', label: 'Settings', icon: Settings },
]

export function Sidebar() {
  return (
    <aside className="hidden md:flex flex-col w-56 shrink-0 bg-bg-card border-r border-border h-screen sticky top-0">
      {/* Logo */}
      <div className="flex items-center gap-2 px-4 py-5 border-b border-border">
        <Droplets size={22} className="text-status-water" />
        <div>
          <p className="font-bold text-text-primary text-sm leading-tight">AquaMonitor</p>
          <p className="text-[10px] text-text-dim">Water Management</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-3 overflow-y-auto">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-2.5 mx-2 rounded-lg text-sm transition-colors ${
                isActive
                  ? 'bg-status-water/10 text-status-water font-semibold'
                  : 'text-text-muted hover:text-text-primary hover:bg-bg-muted'
              }`
            }
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-border text-[10px] text-text-dim">
        v1.0.0 · Smart Water Mgmt
      </div>
    </aside>
  )
}
