interface Props {
  levelPercent: number
  isValid?: boolean
}

export function TankGraphic({ levelPercent, isValid = true }: Props) {
  const clamped = Math.max(0, Math.min(100, levelPercent))

  const fillColor =
    !isValid ? '#6b7280'
    : clamped <= 10 ? '#ef4444'
    : clamped <= 20 ? '#f59e0b'
    : '#06b6d4'

  const status =
    !isValid ? 'INVALID'
    : clamped >= 90 ? 'FULL'
    : clamped <= 20 ? 'LOW'
    : 'NORMAL'

  const statusColor =
    status === 'FULL' ? 'text-status-normal'
    : status === 'LOW' || status === 'INVALID' ? 'text-status-critical'
    : 'text-status-water'

  return (
    <div className="flex flex-col items-center gap-2">
      {/* Tank vessel */}
      <div className="relative w-20 h-36 border-2 border-border rounded-b-lg rounded-t-sm bg-bg overflow-hidden">
        {/* Water fill — animates via CSS transition */}
        <div
          className="absolute bottom-0 left-0 right-0 transition-all duration-700"
          style={{ height: `${clamped}%`, backgroundColor: fillColor, opacity: isValid ? 0.75 : 0.3 }}
        />
        {/* Wave shimmer */}
        {isValid && clamped > 5 && (
          <div
            className="absolute left-0 right-0 h-1 opacity-50"
            style={{ bottom: `${clamped}%`, backgroundColor: fillColor }}
          />
        )}
        {/* Percentage label */}
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-sm font-mono font-bold text-text-primary drop-shadow">
            {isValid ? `${clamped.toFixed(0)}%` : '??'}
          </span>
        </div>
        {/* Level marks */}
        {[25, 50, 75].map(mark => (
          <div
            key={mark}
            className="absolute left-0 right-0 border-t border-border/40"
            style={{ bottom: `${mark}%` }}
          />
        ))}
      </div>
      {/* Status label */}
      <span className={`text-xs font-mono font-bold ${statusColor}`}>{status}</span>
    </div>
  )
}
