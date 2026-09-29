import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from './AuthProvider'

export function ProtectedRoute() {
  const { admin, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return (
      <div className="full-page-state" role="status">
        <span className="spinner" />
        正在验证登录状态
      </div>
    )
  }

  if (!admin) {
    return (
      <Navigate
        to="/login"
        replace
        state={{ from: location.pathname + location.search }}
      />
    )
  }

  return <Outlet />
}
