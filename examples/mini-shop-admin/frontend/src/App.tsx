import { Navigate, Route, Routes } from 'react-router-dom'
import { ProtectedRoute } from './auth/ProtectedRoute'
import { AdminLayout } from './layout/AdminLayout'
import { LoginPage } from './pages/LoginPage'
import { OrderDetailPage } from './pages/OrderDetailPage'
import { OrderListPage } from './pages/OrderListPage'
import { ProductFormPage } from './pages/ProductFormPage'
import { ProductListPage } from './pages/ProductListPage'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AdminLayout />}>
          <Route path="/products" element={<ProductListPage />} />
          <Route path="/products/new" element={<ProductFormPage />} />
          <Route path="/products/:id/edit" element={<ProductFormPage />} />
          <Route path="/orders" element={<OrderListPage />} />
          <Route path="/orders/:id" element={<OrderDetailPage />} />
        </Route>
      </Route>
      <Route path="/" element={<Navigate to="/products" replace />} />
      <Route path="*" element={<Navigate to="/products" replace />} />
    </Routes>
  )
}
