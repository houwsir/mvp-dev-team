import { useEffect, useRef, useState } from 'react'

interface ShipmentDialogProps {
  open: boolean
  busy: boolean
  error: string
  onClose: () => void
  onSubmit: (company: string, trackingNo: string) => void
}

export function ShipmentDialog({
  open,
  busy,
  error,
  onClose,
  onSubmit,
}: ShipmentDialogProps) {
  const [company, setCompany] = useState('')
  const [trackingNo, setTrackingNo] = useState('')
  const [errors, setErrors] = useState<Record<string, string>>({})
  const companyRef = useRef<HTMLInputElement>(null)
  const trackingRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (open) {
      setCompany('')
      setTrackingNo('')
      setErrors({})
      requestAnimationFrame(() => companyRef.current?.focus())
    }
  }, [open])

  if (!open) return null

  const submit = () => {
    const next: Record<string, string> = {}
    if (!company.trim()) next.company = '请输入物流公司'
    if (!trackingNo.trim()) next.trackingNo = '请输入运单号'
    setErrors(next)
    if (next.company) companyRef.current?.focus()
    else if (next.trackingNo) trackingRef.current?.focus()
    else onSubmit(company.trim(), trackingNo.trim())
  }

  return (
    <div className="dialog-backdrop">
      <div className="dialog dialog-wide" role="dialog" aria-modal="true" aria-labelledby="ship-title">
        <h2 id="ship-title">订单发货</h2>
        {error && <div className="alert danger">{error}</div>}
        <label className="field">
          <span>物流公司 <b>*</b></span>
          <input
            ref={companyRef}
            maxLength={100}
            value={company}
            disabled={busy}
            aria-invalid={Boolean(errors.company)}
            onChange={(event) => {
              setCompany(event.target.value)
              setErrors((current) => ({ ...current, company: '' }))
            }}
          />
          <span className="field-error">{errors.company}</span>
        </label>
        <label className="field">
          <span>运单号 <b>*</b></span>
          <input
            ref={trackingRef}
            maxLength={100}
            value={trackingNo}
            disabled={busy}
            aria-invalid={Boolean(errors.trackingNo)}
            onChange={(event) => {
              setTrackingNo(event.target.value)
              setErrors((current) => ({ ...current, trackingNo: '' }))
            }}
          />
          <span className="field-error">{errors.trackingNo}</span>
        </label>
        <div className="dialog-actions">
          <button className="button secondary" disabled={busy} onClick={onClose}>
            取消
          </button>
          <button className="button primary" disabled={busy} onClick={submit}>
            {busy && <span className="spinner small" />}
            {busy ? '发货中' : '确认发货'}
          </button>
        </div>
      </div>
    </div>
  )
}
