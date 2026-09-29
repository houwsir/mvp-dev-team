import { useEffect } from 'react'

export interface ToastMessage {
  type: 'success' | 'danger' | 'info'
  text: string
}

export function Toast({
  message,
  onClose,
}: {
  message: ToastMessage | null
  onClose: () => void
}) {
  useEffect(() => {
    if (!message) return
    const timer = window.setTimeout(onClose, message.type === 'danger' ? 6000 : 3000)
    return () => window.clearTimeout(timer)
  }, [message, onClose])

  if (!message) return null

  return (
    <div className={`toast ${message.type}`} role={message.type === 'danger' ? 'alert' : 'status'}>
      <span>{message.text}</span>
      <button type="button" onClick={onClose} aria-label="关闭通知" title="关闭通知">
        ×
      </button>
    </div>
  )
}
