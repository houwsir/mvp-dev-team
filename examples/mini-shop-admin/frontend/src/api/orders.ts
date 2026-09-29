import type {
  OrderDetail,
  OrderPage,
  OrderQuery,
} from '../types/order'
import { queryString, request } from './client'

const orderPath = (orderId: number | string) =>
  '/orders/' + encodeURIComponent(String(orderId))

export function getOrders(query: OrderQuery) {
  return request<OrderPage>(
    '/orders' +
      queryString({
        page: query.page,
        page_size: query.page_size,
        order_no: query.order_no,
        status: query.status,
      }),
  )
}

export function getOrder(orderId: number | string) {
  return request<OrderDetail>(orderPath(orderId))
}

export function shipOrder(
  orderId: number | string,
  logisticsCompany: string,
  trackingNo: string,
) {
  return request<OrderDetail>(orderPath(orderId) + '/ship', {
    method: 'POST',
    body: JSON.stringify({
      logistics_company: logisticsCompany,
      tracking_no: trackingNo,
    }),
  })
}

export function cancelOrder(orderId: number | string) {
  return request<OrderDetail>(orderPath(orderId) + '/cancel', {
    method: 'POST',
    body: JSON.stringify({}),
  })
}

export function updateInternalNote(
  orderId: number | string,
  internalNote: string | null,
) {
  return request<OrderDetail>(orderPath(orderId) + '/internal-note', {
    method: 'PATCH',
    body: JSON.stringify({ internal_note: internalNote }),
  })
}
