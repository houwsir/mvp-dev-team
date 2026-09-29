import { FormEvent, useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError } from '../api/client'
import {
  getProducts,
  updateProductStatus,
  updateProductStock,
} from '../api/products'
import { Pagination } from '../components/Pagination'
import { ProductImage } from '../components/ProductImage'
import { StatusBadge } from '../components/StatusBadge'
import { StockDialog } from '../components/StockDialog'
import { Toast, type ToastMessage } from '../components/Toast'
import type { Product, ProductStatus } from '../types/product'
import { formatDate, formatMoney } from '../utils/format'

export function ProductListPage() {
  const [items, setItems] = useState<Product[]>([])
  const [keywordInput, setKeywordInput] = useState('')
  const [statusInput, setStatusInput] = useState<'' | ProductStatus>('')
  const [keyword, setKeyword] = useState('')
  const [status, setStatus] = useState<'' | ProductStatus>('')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState<20 | 50>(20)
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [stockProduct, setStockProduct] = useState<Product | null>(null)
  const [stockBusy, setStockBusy] = useState(false)
  const [stockError, setStockError] = useState('')
  const [statusBusy, setStatusBusy] = useState<number | null>(null)
  const [toast, setToast] = useState<ToastMessage | null>(null)
  const requestId = useRef(0)
  const tableRef = useRef<HTMLDivElement>(null)

  const load = useCallback(async () => {
    const id = ++requestId.current
    setLoading(true)
    setError('')
    try {
      const response = await getProducts({
        page,
        page_size: pageSize,
        keyword: keyword || undefined,
        status: status || undefined,
      })
      if (id !== requestId.current) return
      setItems(response.items)
      setTotal(response.total)
      setTotalPages(response.total_pages)
    } catch (cause) {
      if (id !== requestId.current) return
      setItems([])
      setError(cause instanceof Error ? cause.message : '商品加载失败')
    } finally {
      if (id === requestId.current) setLoading(false)
    }
  }, [page, pageSize, keyword, status])

  useEffect(() => {
    document.title = '商品管理 - Mini Shop Admin'
    void load()
  }, [load])

  const search = (event?: FormEvent) => {
    event?.preventDefault()
    setPage(1)
    setKeyword(keywordInput.trim())
    setStatus(statusInput)
  }

  const reset = () => {
    setKeywordInput('')
    setStatusInput('')
    setKeyword('')
    setStatus('')
    setPage(1)
  }

  const saveStock = async (stock: number) => {
    if (!stockProduct) return
    setStockBusy(true)
    setStockError('')
    try {
      await updateProductStock(stockProduct.id, stock)
      setStockProduct(null)
      setToast({ type: 'success', text: '库存已更新' })
      await load()
    } catch (cause) {
      setStockError(cause instanceof Error ? cause.message : '库存保存失败')
    } finally {
      setStockBusy(false)
    }
  }

  const toggleStatus = async (product: Product) => {
    if (product.stock === 0 && product.status === 'inactive') return
    setStatusBusy(product.id)
    try {
      await updateProductStatus(
        product.id,
        product.status === 'active' ? 'inactive' : 'active',
      )
      setToast({
        type: 'success',
        text: product.status === 'active' ? '商品已下架' : '商品已上架',
      })
      await load()
    } catch (cause) {
      const message = cause instanceof ApiError ? cause.message : '状态更新失败'
      setToast({ type: 'danger', text: message })
    } finally {
      setStatusBusy(null)
    }
  }

  return (
    <>
      <div className="page-title-row">
        <div>
          <h1>商品管理</h1>
          <p>维护商品信息、库存和上下架状态</p>
        </div>
        <Link className="button primary" to="/products/new">
          <span aria-hidden="true">＋</span> 新建商品
        </Link>
      </div>

      <form className="filter-bar" onSubmit={search}>
        <input
          className="search-product"
          placeholder="搜索商品名称"
          value={keywordInput}
          onChange={(event) => setKeywordInput(event.target.value)}
        />
        <select
          value={statusInput}
          aria-label="商品状态"
          onChange={(event) => setStatusInput(event.target.value as '' | ProductStatus)}
        >
          <option value="">全部状态</option>
          <option value="active">已上架</option>
          <option value="inactive">已下架</option>
        </select>
        <button className="button primary" disabled={loading}>查询</button>
        <button className="button secondary" type="button" disabled={loading} onClick={reset}>
          重置
        </button>
      </form>

      <div className="table-panel" ref={tableRef}>
        {loading ? (
          <div className="skeleton-table" role="status" aria-label="商品加载中">
            {Array.from({ length: 8 }).map((_, index) => <div key={index} />)}
          </div>
        ) : error ? (
          <div className="table-state error-state">
            <strong>商品加载失败</strong>
            <span>{error}</span>
            <button className="button secondary" onClick={() => void load()}>重试</button>
          </div>
        ) : items.length === 0 ? (
          <div className="table-state">
            <span className="state-icon" aria-hidden="true">□</span>
            <strong>{keyword || status ? '未找到符合条件的商品' : '暂无商品'}</strong>
            {keyword || status ? (
              <button className="button secondary" onClick={reset}>清除筛选</button>
            ) : (
              <Link className="button primary" to="/products/new">新建商品</Link>
            )}
          </div>
        ) : (
          <table className="data-table product-table">
            <thead>
              <tr>
                <th>主图</th>
                <th>商品名称</th>
                <th className="numeric">售价</th>
                <th>库存</th>
                <th>状态</th>
                <th>更新时间</th>
                <th className="actions-column">操作</th>
              </tr>
            </thead>
            <tbody>
              {items.map((product) => (
                <tr key={product.id}>
                  <td><ProductImage src={product.main_image_url} alt={product.name} /></td>
                  <td><span className="product-name" title={product.name}>{product.name}</span></td>
                  <td className="numeric">{formatMoney(product.price)}</td>
                  <td className={product.stock === 0 ? 'stock-zero numeric' : 'numeric'}>
                    {product.stock}
                  </td>
                  <td><StatusBadge status={product.status} /></td>
                  <td className="numeric muted">{formatDate(product.updated_at)}</td>
                  <td className="row-actions">
                    <Link className="text-action" to={`/products/${product.id}/edit`}>编辑</Link>
                    <button className="text-action" onClick={() => {
                      setStockError('')
                      setStockProduct(product)
                    }}>
                      调整库存
                    </button>
                    <button
                      className="text-action"
                      disabled={statusBusy === product.id || (product.stock === 0 && product.status === 'inactive')}
                      title={product.stock === 0 && product.status === 'inactive' ? '库存为 0，无法上架' : ''}
                      onClick={() => void toggleStatus(product)}
                    >
                      {statusBusy === product.id ? '处理中' : product.status === 'active' ? '下架' : '上架'}
                    </button>
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

      <StockDialog
        product={stockProduct}
        busy={stockBusy}
        error={stockError}
        onClose={() => !stockBusy && setStockProduct(null)}
        onSave={(value) => void saveStock(value)}
      />
      <Toast message={toast} onClose={() => setToast(null)} />
    </>
  )
}
