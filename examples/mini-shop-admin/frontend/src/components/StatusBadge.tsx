import type { OrderStatus } from '../types/order'
import type { ProductStatus } from '../types/product'

const labels: Record<OrderStatus | ProductStatus, string> = {
  active: '已上架',
  inactive: '已下架',
  pending_payment: '待付款',
  pending_shipment: '待发货',
  shipped: '已发货',
  completed: '已完成',
  cancelled: '已取消',
}

export function StatusBadge({
  status,
}: {
  status: OrderStatus | ProductStatus
}) {
  return <span className={`status-badge status-${status}`}>{labels[status]}</span>
}
