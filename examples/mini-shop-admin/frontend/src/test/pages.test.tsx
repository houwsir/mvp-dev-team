import { afterEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import App from '../App'
import { AuthProvider } from '../auth/AuthProvider'

const jsonResponse = (body: unknown, status = 200) =>
  Promise.resolve(
    new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  )

function renderApp(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider>
        <App />
      </AuthProvider>
    </MemoryRouter>,
  )
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe('admin pages', () => {
  it('shows a login validation error before requesting the API', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
      jsonResponse({ detail: '需要登录', code: 'AUTH_REQUIRED' }, 401),
    )

    renderApp('/login')
    await screen.findByRole('heading', { name: '管理员登录' })
    fireEvent.click(screen.getByRole('button', { name: '登录' }))

    expect(screen.getByText('请输入账号')).toBeInTheDocument()
    expect(screen.getByText('请输入密码')).toBeInTheDocument()
  })

  it('registers the product creation route and validates fields', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
      if (String(input).endsWith('/auth/me')) {
        return jsonResponse({ id: 1, username: 'admin', display_name: '商城管理员' })
      }
      return jsonResponse({})
    })

    renderApp('/products/new')
    await screen.findByRole('heading', { name: '新建商品' })
    fireEvent.click(screen.getByRole('button', { name: '创建商品' }))

    expect(screen.getByText('请输入商品名称')).toBeInTheDocument()
    expect(screen.getByText('请输入主图 URL')).toBeInTheDocument()
    expect(screen.getByText('售价必须大于 0，且最多保留两位小数')).toBeInTheDocument()
    expect(screen.getByText('库存必须为大于等于 0 的整数')).toBeInTheDocument()
  })

  it('keeps order cancellation unavailable for shipped orders', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
      const url = String(input)
      if (url.endsWith('/auth/me')) {
        return jsonResponse({ id: 1, username: 'admin', display_name: '商城管理员' })
      }
      if (url.endsWith('/orders/1')) {
        return jsonResponse({
          id: 1,
          order_no: '202501010001',
          buyer_id: 'buyer-1',
          buyer_name: '张三',
          status: 'shipped',
          items_amount: '99.00',
          shipping_fee: '10.00',
          payable_amount: '109.00',
          receiver: {
            name: '张三',
            phone: '13800000000',
            province: '广东省',
            city: '深圳市',
            district: '南山区',
            address: '科技园 1 号',
          },
          buyer_message: null,
          internal_note: null,
          placed_at: '2025-01-01T00:00:00Z',
          created_at: '2025-01-01T00:00:00Z',
          updated_at: '2025-01-01T00:00:00Z',
          items: [],
          shipment: {
            logistics_company: '顺丰速运',
            tracking_no: 'SF123456789',
            shipped_by: 1,
            shipped_by_display_name: '商城管理员',
            shipped_at: '2025-01-01T01:00:00Z',
          },
          status_history: [],
        })
      }
      return jsonResponse({})
    })

    renderApp('/orders/1')
    await screen.findByText('202501010001')
    await waitFor(() => {
      expect(screen.queryByRole('button', { name: '取消订单' })).not.toBeInTheDocument()
      expect(screen.queryByRole('button', { name: '发货' })).not.toBeInTheDocument()
    })
  })
})
