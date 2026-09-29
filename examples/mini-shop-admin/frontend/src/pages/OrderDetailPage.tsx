import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ApiError } from '../api/client'
import {
  cancelOrder,
  getOrder,
  shipOrder,
  updateInternalNote,
} from '../api/orders'
import { ConfirmDialog } from '../components/ConfirmDialog'
import { ProductImage } from '../components/ProductImage'
import { ShipmentDialog } from '../components/ShipmentDialog'
import { StatusBadge } from '../components/StatusBadge'
import { Toast, type ToastMessage } from '../components/Toast'
import type { OrderDetail, OrderStatusHistory } from '../types/order'
import { formatDate, formatMoney } from '../utils/format'

const eventLabels: Record<OrderStatusHistory['event_type'], string> = {
  created: '订单创建',
  payment_confirmed: '付款确认',
  shipped: '订单发货',
  completed: '订单完成',
  cancelled: '订单取消',
}

export function OrderDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [order, setOrder] = useState<OrderDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notFound, setNotFound] = useState(false)
  const [shipOpen, setShipOpen] = useState(false)
  const [shipBusy, setShipBusy] = useState(false)
  const [shipError, setShipError] = useState('')
  const [cancelOpen, setCancelOpen] = useState(false)
  const [cancelBusy, setCancelBusy] = useState(false)
  const [note, setNote] = useState('')
  const [noteBusy, setNoteBusy] = useState(false)
  const [noteError, setNoteError] = useState('')
  const [toast, setToast] = useState<ToastMessage | null>(null)

  const noteDirty = useMemo(
    () => order !== null && note !== (order.internal_note || ''),
    [note, order],
  )

  const load = useCallback(async () => {
    if (!id) return
    setLoading(true)
    setError('')
    setNotFound(false)
    try {
      const response = await getOrder(id)
      setOrder(response)
      setNote(response.internal_note || '')
    } catch (cause) {
      setOrder(null)
      if (cause instanceof ApiError && cause.status === 404) setNotFound(true)
      else setError(cause instanceof Error ? cause.message : '订单详情加载失败')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    document.title = '订单详情 - Mini Shop Admin'
    void load()
  }, [load])

  useEffect(() => {
    const listener = (event: BeforeUnloadEvent) => {
      if (noteDirty) event.preventDefault()
    }
    window.addEventListener('beforeunload', listener)
    return () => window.removeEventListener('beforeunload', listener)
  }, [noteDirty])

  const submitShipment = async (company: string, trackingNo: string) => {
    if (!id) return
    setShipBusy(true)
    setShipError('')
    try {
      await shipOrder(id, company, trackingNo)
      setShipOpen(false)
      setToast({ type: 'success', text: '订单已发货' })
      await load()
    } catch (cause) {
      setShipError(cause instanceof Error ? cause.message : '发货失败')
    } finally {
      setShipBusy(false)
    }
  }

  const submitCancel = async () => {
    if (!id) return
    setCancelBusy(true)
    try {
      await cancelOrder(id)
      setCancelOpen(false)
      setToast({ type: 'success', text: '订单已取消' })
      await load()
    } catch (cause) {
      setCancelOpen(false)
      setToast({
        type: 'danger',
        text: cause instanceof Error ? cause.message : '取消订单失败',
      })
      await load()
    } finally {
      setCancelBusy(false)
    }
  }

  const saveNote = async () => {
    if (!id) return
    setNoteBusy(true)
    setNoteError('')
    try {
      const response = await updateInternalNote(id, note.trim() || null)
      setOrder(response)
      setNote(response.internal_note || '')
      setToast({ type: 'success', text: '备注已保存' })
    } catch (cause) {
      setNoteError(cause instanceof Error ? cause.message : '备注保存失败')
    } finally {
      setNoteBusy(false)
    }
  }

  if (loading) {
    return <div className="detail-skeleton" role="status">正在加载订单详情</div>
  }

  if (notFound || error || !order) {
    return (
      <div className="page-error">
        <h1>{notFound ? '订单不存在或已被移除' : '订单详情加载失败'}</h1>
        {error && <p>{error}</p>}
        <div>
          {!notFound && <button className="button primary" onClick={() => void load()}>重试</button>}
          <button className="button secondary" onClick={() => navigate('/orders')}>返回订单列表</button>
        </div>
      </div>
    )
  }

  const address = [
    order.receiver.province,
    order.receiver.city,
    order.receiver.district,
    order.receiver.address,
  ].join('')

  return (
    <>
      <button className="back-link" onClick={() => navigate('/orders')}>← 返回订单列表</button>
      <div className="order-summary">
        <div>
          <div className="order-title">
            <h1>{order.order_no}</h1>
            <StatusBadge status={order.status} />
          </div>
          <p>下单时间：{formatDate(order.placed_at)}</p>
        </div>
        <div className="summary-actions">
          {['pending_payment', 'pending_shipment'].includes(order.status) && (
            <button className="button danger-outline" onClick={() => setCancelOpen(true)}>
              取消订单
            </button>
          )}
          {order.status === 'pending_shipment' && (
            <button className="button primary" onClick={() => {
              setShipError('')
              setShipOpen(true)
            }}>
              发货
            </button>
          )}
        </div>
      </div>

      <div className="order-detail-grid">
        <div className="order-main">
          <section className="detail-section">
            <h2>商品明细</h2>
            <table className="data-table item-table">
              <thead>
                <tr><th>商品信息</th><th className="numeric">单价</th><th className="numeric">数量</th><th className="numeric">小计</th></tr>
              </thead>
              <tbody>
                {order.items.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <div className="item-info">
                        <ProductImage src={item.product_image_url} alt={item.product_name} />
                        <span>{item.product_name}</span>
                      </div>
                    </td>
                    <td className="numeric">{formatMoney(item.unit_price)}</td>
                    <td className="numeric">{item.quantity}</td>
                    <td className="numeric">{formatMoney(item.line_amount)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="amount-summary">
              <div><span>商品金额</span><strong>{formatMoney(order.items_amount)}</strong></div>
              <div><span>运费</span><strong>{formatMoney(order.shipping_fee)}</strong></div>
              <div className="payable"><span>实付金额</span><strong>{formatMoney(order.payable_amount)}</strong></div>
            </div>
          </section>

          <section className="detail-section">
            <h2>收货信息</h2>
            <dl className="description-list">
              <dt>收货人</dt><dd>{order.receiver.name}</dd>
              <dt>手机号</dt><dd className="mono">{order.receiver.phone}</dd>
              <dt>收货地址</dt><dd>{address}</dd>
            </dl>
          </section>

          <section className="detail-section">
            <h2>买家留言</h2>
            <p className="multiline">{order.buyer_message || '无'}</p>
          </section>

          <section className="detail-section">
            <h2>物流信息</h2>
            {order.shipment ? (
              <dl className="description-list">
                <dt>物流公司</dt><dd>{order.shipment.logistics_company}</dd>
                <dt>运单号</dt><dd className="mono">{order.shipment.tracking_no}</dd>
                <dt>发货时间</dt><dd>{formatDate(order.shipment.shipped_at)}</dd>
              </dl>
            ) : <p className="muted">暂无物流信息</p>}
          </section>
        </div>

        <aside className="order-side">
          <section className="detail-section">
            <div className="section-heading">
              <h2>内部备注</h2>
              <span>仅后台可见</span>
            </div>
            <textarea
              maxLength={1000}
              value={note}
              disabled={noteBusy}
              placeholder="填写订单处理备注"
              onChange={(event) => {
                setNote(event.target.value)
                setNoteError('')
              }}
            />
            <div className="note-footer">
              <span className={note.length >= 1000 ? 'danger-text' : 'muted'}>{note.length}/1000</span>
              <button
                className="button primary"
                disabled={noteBusy || !noteDirty}
                onClick={() => void saveNote()}
              >
                {noteBusy ? '保存中' : '保存备注'}
              </button>
            </div>
            <span className="field-error">{noteError}</span>
          </section>

          <section className="detail-section">
            <h2>状态记录</h2>
            <ol className="timeline">
              {order.status_history.map((history) => (
                <li key={history.id}>
                  <strong>{eventLabels[history.event_type]}</strong>
                  <span>{history.operator_display_name || (history.operator_type === 'system' ? '系统' : '管理员')}</span>
                  <time>{formatDate(history.created_at)}</time>
                  {history.event_note && <p>{history.event_note}</p>}
                </li>
              ))}
            </ol>
          </section>
        </aside>
      </div>

      <ShipmentDialog
        open={shipOpen}
        busy={shipBusy}
        error={shipError}
        onClose={() => !shipBusy && setShipOpen(false)}
        onSubmit={(company, trackingNo) => void submitShipment(company, trackingNo)}
      />
      <ConfirmDialog
        open={cancelOpen}
        title="确认取消订单？"
        message="取消后订单状态无法在本后台恢复，请确认后继续。"
        confirmText="确认取消"
        danger
        busy={cancelBusy}
        onClose={() => !cancelBusy && setCancelOpen(false)}
        onConfirm={() => void submitCancel()}
      />
      <Toast message={toast} onClose={() => setToast(null)} />
    </>
  )
}
