import { FormEvent, useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { getOrders } from '../api/orders'
import { Pagination } from '../components/Pagination'
import { StatusBadge } from '../components/StatusBadge'
import type { OrderStatus, OrderSummary } from '../types/order'
import { formatDate, formatMoney } from '../utils/format'

export function OrderListPage() {
  const [items, setItems] = useState<OrderSummary[]>([])
  const [orderNoInput, setOrderNoInput] = useState('')
  const [statusInput, setStatusInput] = useState<'' | OrderStatus>('')
  const [orderNo, setOrderNo] = useState('')
  const [status, setStatus] = useState<'' | OrderStatus>('')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState<20 | 50>(20)
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const requestId = useRef(0)
  const tableRef = useRef<HTMLDivElement>(null)

  const load = useCallback(async () => {
    const id = ++requestId.current
    setLoading(true)
    setError('')
    try {
      const response = await getOrders({
        page,
        page_size: pageSize,
        order_no: orderNo || undefined,
        status: status || undefined,
      })
      if (id !== requestId.current) return
      setItems(response.items)
      setTotal(response.total)
      setTotalPages(response.total_pages)
    } catch (cause) {
      if (id !== requestId.current) return
      setItems([])
      setError(cause instanceof Error ? cause.message : '订单加载失败')
    } finally {
      if (id === requestId.current) setLoading(false)
    }
  }, [page, pageSize, orderNo, status])

  useEffect(() => {
    document.title = '订单管理 - Mini Shop Admin'
    void load()
  }, [load])

  const search = (event?: FormEvent) => {
    event?.preventDefault()
    setPage(1)
    setOrderNo(orderNoInput.trim())
    setStatus(statusInput)
  }

  const reset = () => {
    setOrderNoInput('')
    setStatusInput('')
    setOrderNo('')
    setStatus('')
    setPage(1)
  }

  return (
    <>
      <div className="page-title-row">
        <div>
          <h1>订单管理</h1>
          <p>查询订单并处理履约状态</p>
        </div>
      </div>

      <form className="filter-bar" onSubmit={search}>
        <input
          className="search-order"
          placeholder="输入完整订单号"
          value={orderNoInput}
          onChange={(event) => setOrderNoInput(event.target.value)}
        />
        <select
          value={statusInput}
          aria-label="订单状态"
          onChange={(event) => setStatusInput(event.target.value as '' | OrderStatus)}
        >
          <option value="">全部状态</option>
          <option value="pending_payment">待付款</option>
          <option value="pending_shipment">待发货</option>
          <option value="shipped">已发货</option>
          <option value="completed">已完成</option>
          <option value="cancelled">已取消</option>
        </select>
        <button className="button primary" disabled={loading}>查询</button>
        <button className="button secondary" type="button" disabled={loading} onClick={reset}>
          重置
        </button>
      </form>

      <div className="table-panel" ref={tableRef}>
        {loading ? (
          <div className="skeleton-table" role="status" aria-label="订单加载中">
            {Array.from({ length: 8 }).map((_, index) => <div key={index} />)}
          </div>
        ) : error ? (
          <div className="table-state error-state">
            <strong>订单加载失败</strong>
            <span>{error}</span>
            <button className="button secondary" onClick={() => void load()}>重试</button>
          </div>
        ) : items.length === 0 ? (
          <div className="table-state">
            <span className="state-icon" aria-hidden="true">≡</span>
            <strong>{orderNo || status ? '未找到该订单' : '暂无订单'}</strong>
            {(orderNo || status) && (
              <button className="button secondary" onClick={reset}>清除筛选</button>
            )}
          </div>
        ) : (
          <table className="data-table order-table">
            <thead>
              <tr>
                <th>订单号</th>
                <th>下单时间</th>
                <th>买家</th>
                <th className="numeric">订单金额</th>
                <th>状态</th>
                <th className="actions-column">操作</th>
              </tr>
            </thead>
            <tbody>
              {items.map((order) => (
                <tr key={order.id}>
                  <td className="mono">{order.order_no}</td>
                  <td className="numeric muted">{formatDate(order.placed_at)}</td>
                  <td>{order.buyer_name}</td>
                  <td className="numeric">{formatMoney(order.payable_amount)}</td>
                  <td><StatusBadge status={order.status} /></td>
                  <td className="row-actions">
                    <Link className="text-action" to={`/orders/${order.id}`}>
                      查看详情 →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {!loading && !error && (
          <Pagination
            page={page}
            pageSize={pageSize}
            total={total}
            totalPages={totalPages}
            onPageChange={(value) => {
              setPage(value)
              tableRef.current?.scrollIntoView({ behavior: 'smooth' })
            }}
            onPageSizeChange={(value) => {
              setPageSize(value)
              setPage(1)
            }}
          />
        )}
      </div>
    </>
  )
}
