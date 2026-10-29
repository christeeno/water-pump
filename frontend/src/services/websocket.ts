import type { WsMessage } from '../types'

type Listener = (msg: WsMessage) => void

class DashboardWebSocket {
  private ws: WebSocket | null = null
  private listeners: Set<Listener> = new Set()
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private backoffMs = 2000
  private maxBackoffMs = 30000
  private url = ''
  private intentionallyClosed = false
  public isOpen = false

  connect(url: string): void {
    this.url = url
    this.intentionallyClosed = false
    this._open()
  }

  private _open(): void {
    if (this.ws) {
      this.ws.onopen = null
      this.ws.onmessage = null
      this.ws.onclose = null
      this.ws.onerror = null
      this.ws.close()
    }
    try {
      this.ws = new WebSocket(this.url)
    } catch {
      this._scheduleReconnect()
      return
    }

    this.ws.onopen = () => {
      this.isOpen = true
      this.backoffMs = 2000
    }

    this.ws.onmessage = (event: MessageEvent) => {
      try {
        const msg = JSON.parse(event.data as string) as WsMessage
        this.listeners.forEach(fn => fn(msg))
      } catch {
        // ignore malformed frames
      }
    }

    this.ws.onclose = () => {
      this.isOpen = false
      if (!this.intentionallyClosed) {
        this._scheduleReconnect()
      }
    }

    this.ws.onerror = () => {
      this.ws?.close()
    }
  }

  private _scheduleReconnect(): void {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer)
    this.reconnectTimer = setTimeout(() => {
      this.backoffMs = Math.min(this.backoffMs * 1.5, this.maxBackoffMs)
      this._open()
    }, this.backoffMs)
  }

  disconnect(): void {
    this.intentionallyClosed = true
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer)
    this.ws?.close()
    this.isOpen = false
  }

  addListener(fn: Listener): () => void {
    this.listeners.add(fn)
    return () => this.listeners.delete(fn)
  }
}

export const dashboardWS = new DashboardWebSocket()
