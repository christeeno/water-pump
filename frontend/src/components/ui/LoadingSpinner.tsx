interface Props {
  message?: string
}

export function LoadingSpinner({ message = 'Loading...' }: Props) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 p-8 text-text-muted">
      <div className="w-8 h-8 border-2 border-border border-t-status-water rounded-full animate-spin" />
      <span className="text-sm">{message}</span>
    </div>
  )
}
