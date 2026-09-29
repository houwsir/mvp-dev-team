import { useEffect, useRef } from 'react'

interface ConfirmDialogProps {
  open: boolean
  title: string
  message: string
  confirmText: string
  busy?: boolean
  danger?: boolean
  onConfirm: () => void
  onClose: () => void
}

export function ConfirmDialog({
  open,
  title,
  message,
  confirmText,
  busy,
  danger,
  onConfirm,
  onClose,
}: ConfirmDialogProps) {
  const cancelRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (open) cancelRef.current?.focus()
  }, [open])

  useEffect(() => {
    if (!open) return
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !busy) onClose()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [open, busy, onClose])

  if (!open) return null

  return (
    <div className="dialog-backdrop" role="presentation">
      <div className="dialog" role="dialog" aria-modal="true" aria-labelledby="confirm-title">
        <h2 id="confirm-title">{title}</h2>
        <p>{message}</p>
        <div className="dialog-actions">
          <button ref={cancelRef} className="button secondary" disabled={busy} onClick={onClose}>
            返回
          </button>
          <button
            className={`button ${danger ? 'danger' : 'primary'}`}
            disabled={busy}
            onClick={onConfirm}
          >
            {busy && <span className="spinner small" />}
            {busy ? '处理中' : confirmText}
          </button>
        </div>
      </div>
    </div>
  )
}
