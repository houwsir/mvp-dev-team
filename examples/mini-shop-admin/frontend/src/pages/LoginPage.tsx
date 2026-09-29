import { FormEvent, useEffect, useRef, useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthProvider'
import { ThemeToggle } from '../components/ThemeToggle'

export function LoginPage() {
  const { admin, loading, login, sessionExpired } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [requestError, setRequestError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const passwordRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    document.title = '管理员登录 - Mini Shop Admin'
  }, [])

  if (!loading && admin) return <Navigate to="/products" replace />

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    const next: Record<string, string> = {}
    if (!username.trim()) next.username = '请输入账号'
    if (!password) next.password = '请输入密码'
    setErrors(next)
    setRequestError('')
    if (Object.keys(next).length) return

    setSubmitting(true)
    try {
      await login(username.trim(), password)
      const target = (location.state as { from?: string } | null)?.from || '/products'
      navigate(target, { replace: true })
    } catch (error) {
      setPassword('')
      passwordRef.current?.focus()
      if (error instanceof ApiError) {
        if (error.code === 'INVALID_CREDENTIALS') setRequestError('账号或密码错误')
        else if (error.code === 'ACCOUNT_DISABLED') setRequestError('账号已禁用')
        else setRequestError(error.message || '登录失败，请稍后重试')
      } else {
        setRequestError('登录失败，请稍后重试')
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-brand">Mini Shop Admin</div>
      <div className="login-theme"><ThemeToggle /></div>
      <form className="login-panel" onSubmit={submit} noValidate>
        <h1>管理员登录</h1>
        <p className="muted">登录商城运营后台</p>
        {sessionExpired && <div className="alert info">登录状态已失效，请重新登录</div>}
        {requestError && <div className="alert danger">{requestError}</div>}
        <label className="field">
          <span>账号</span>
          <input
            autoFocus
            autoComplete="username"
            maxLength={64}
            value={username}
            disabled={submitting}
            aria-invalid={Boolean(errors.username)}
            onChange={(event) => {
              setUsername(event.target.value)
              setErrors((value) => ({ ...value, username: '' }))
            }}
          />
          <span className="field-error">{errors.username}</span>
        </label>
        <label className="field">
          <span>密码</span>
          <div className="password-control">
            <input
              ref={passwordRef}
              type={showPassword ? 'text' : 'password'}
              autoComplete="current-password"
              maxLength={128}
              value={password}
              disabled={submitting}
              aria-invalid={Boolean(errors.password)}
              onChange={(event) => {
                setPassword(event.target.value)
                setErrors((value) => ({ ...value, password: '' }))
              }}
            />
            <button
              type="button"
              aria-label={showPassword ? '隐藏密码' : '显示密码'}
              title={showPassword ? '隐藏密码' : '显示密码'}
              disabled={submitting}
              onClick={() => setShowPassword((value) => !value)}
            >
              {showPassword ? '◉' : '○'}
            </button>
          </div>
          <span className="field-error">{errors.password}</span>
        </label>
        <button className="button primary login-submit" disabled={submitting}>
          {submitting && <span className="spinner small" />}
          {submitting ? '登录中' : '登录'}
        </button>
      </form>
    </div>
  )
}
