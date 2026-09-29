import { useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthProvider'
import { ThemeToggle } from '../components/ThemeToggle'

export function AdminLayout() {
  const { admin, logout } = useAuth()
  const [leaving, setLeaving] = useState(false)
  const navigate = useNavigate()

  const handleLogout = async () => {
    setLeaving(true)
    try {
      await logout()
    } finally {
      navigate('/login', { replace: true })
    }
  }

  return (
    <div className="admin-shell">
      <aside className="sidebar">
        <div className="brand">Mini Shop Admin</div>
        <nav aria-label="主导航">
          <NavLink to="/products" className={({ isActive }) => isActive ? 'active' : ''}>
            <span aria-hidden="true">□</span> 商品管理
          </NavLink>
          <NavLink to="/orders" className={({ isActive }) => isActive ? 'active' : ''}>
            <span aria-hidden="true">≡</span> 订单管理
          </NavLink>
        </nav>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <span className="breadcrumb">商城运营后台</span>
          <div className="topbar-actions">
            <ThemeToggle />
            <span className="admin-name">{admin?.display_name}</span>
            <button className="button text" disabled={leaving} onClick={handleLogout}>
              {leaving ? '退出中' : '退出'}
            </button>
          </div>
        </header>
        <main className="page-content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
