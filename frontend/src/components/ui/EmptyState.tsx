import type { ReactNode } from 'react'

interface Props {
  icon?: ReactNode
  title: string
  description?: string
}

export function EmptyState({ icon, title, description }: Props) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 p-12 text-text-muted">
      {icon && <div className="opacity-40 mb-2">{icon}</div>}
      <p className="font-semibold text-text-primary">{title}</p>
      {description && <p className="text-sm text-center max-w-xs">{description}</p>}
    </div>
  )
}
