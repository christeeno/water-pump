import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Activity, Gauge, AlertTriangle, BarChart3, Server, Settings } from 'lucide-react'

const items = [
  { to: '/', label: 'Home', icon: LayoutDashboard },
  { to: '/monitoring', label: 'Monitor', icon: Activity },
  { to: '/pump-control', label: 'Pump', icon: Gauge },
  { to: '/faults', label: 'Faults', icon: AlertTriangle },
  { to: '/analytics', label: 'Stats', icon: BarChart3 },
  { to: '/device', label: 'Device', icon: Server },
  { to: '/settings', label: 'Settings', icon: Settings },
]

export function MobileNav() {
  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-bg-card border-t border-border flex overflow-x-auto">
      {items.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          end={to === '/'}
          className={({ isActive }) =>
            `flex flex-col items-center gap-0.5 px-3 py-2 flex-1 min-w-[48px] text-[10px] transition-colors ${
              isActive ? 'text-status-water' : 'text-text-dim'
            }`
          }
        >
          <Icon size={18} />
          {label}
        </NavLink>
      ))}
    </nav>
  )
}
