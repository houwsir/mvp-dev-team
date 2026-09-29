import { useEffect, useRef, useState } from 'react'
import type { Product } from '../types/product'

interface StockDialogProps {
  product: Product | null
  busy: boolean
  error: string
  onClose: () => void
  onSave: (stock: number) => void
}

export function StockDialog({
  product,
  busy,
  error,
  onClose,
  onSave,
}: StockDialogProps) {
  const [value, setValue] = useState('')
  const [fieldError, setFieldError] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (product) {
      setValue(String(product.stock))
      setFieldError('')
      requestAnimationFrame(() => inputRef.current?.focus())
    }
  }, [product])

  if (!product) return null

  const submit = () => {
    if (!/^\d+$/.test(value)) {
      setFieldError('库存必须为大于等于 0 的整数')
      inputRef.current?.focus()
      return
    }
    onSave(Number(value))
  }

  return (
    <div className="dialog-backdrop">
      <div className="dialog" role="dialog" aria-modal="true" aria-labelledby="stock-title">
        <h2 id="stock-title">调整库存</h2>
        <p className="muted">当前库存：{product.stock}</p>
        {error && <div className="alert danger">{error}</div>}
        <label className="field">
          <span>新库存</span>
          <input
            ref={inputRef}
            type="number"
            min="0"
            step="1"
            value={value}
            disabled={busy}
            aria-invalid={Boolean(fieldError)}
            onWheel={(event) => event.currentTarget.blur()}
            onChange={(event) => {
              setValue(event.target.value)
              setFieldError('')
            }}
          />
          <span className="field-error">{fieldError}</span>
        </label>
        <div className="dialog-actions">
          <button className="button secondary" disabled={busy} onClick={onClose}>
            取消
          </button>
          <button className="button primary" disabled={busy} onClick={submit}>
            {busy && <span className="spinner small" />}
            {busy ? '保存中' : '保存'}
          </button>
        </div>
      </div>
    </div>
  )
}
