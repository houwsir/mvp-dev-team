import type { PageResponse } from './api'

export type OrderStatus =
  | 'pending_payment'
  | 'pending_shipment'
  | 'shipped'
  | 'completed'
  | 'cancelled'

export interface OrderSummary {
  id: number
  order_no: string
  placed_at: string
  buyer_name: string
  payable_amount: string
  status: OrderStatus
}

export interface OrderItem {
  id: number
  product_id: number
  product_name: string
  product_image_url: string
  unit_price: string
  quantity: number
  line_amount: string
}

export interface OrderReceiver {
  name: string
  phone: string
  province: string
  city: string
  district: string
  address: string
}

export interface OrderShipment {
  logistics_company: string
  tracking_no: string
  shipped_by: number
  shipped_by_display_name: string
  shipped_at: string
}

export interface OrderStatusHistory {
  id: number
  from_status: OrderStatus | null
  to_status: OrderStatus
  event_type: 'created' | 'payment_confirmed' | 'shipped' | 'completed' | 'cancelled'
  operator_type: 'system' | 'admin'
  operator_admin_id: number | null
  operator_display_name: string | null
  event_note: string | null
  created_at: string
}

export interface OrderDetail extends OrderSummary {
  buyer_id: string
  items_amount: string
  shipping_fee: string
  receiver: OrderReceiver
  buyer_message: string | null
  internal_note: string | null
  created_at: string
  updated_at: string
  items: OrderItem[]
  shipment: OrderShipment | null
  status_history: OrderStatusHistory[]
}

export interface OrderQuery {
  page: number
  page_size: 20 | 50
  order_no?: string
  status?: OrderStatus
}

export type OrderPage = PageResponse<OrderSummary>
