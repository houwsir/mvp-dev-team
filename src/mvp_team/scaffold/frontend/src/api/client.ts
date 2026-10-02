/**
 * API 调用封装（骨架兜底版本，前端工程师应按 API 契约扩展）。
 *
 * 约定：baseURL 固定为同源相对路径 `/api`。
 * 开发态由 vite 的 proxy 转发到本地后端，生产态由 nginx 反代，因此无需处理跨域。
 */
const BASE = '/api'

export class ApiError extends Error {
  status: number
  detail: unknown

  constructor(status: number, detail: unknown) {
    super(typeof detail === 'string' ? detail : `请求失败（HTTP ${status}）`)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

function buildQuery(params?: Record<string, unknown>): string {
  if (!params) return ''
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === '') continue
    search.append(key, String(value))
  }
  const qs = search.toString()
  return qs ? `?${qs}` : ''
}

export async function request<T>(
  path: string,
  options: { method?: string; body?: unknown; params?: Record<string, unknown> } = {},
): Promise<T> {
  const { method = 'GET', body, params } = options
  const response = await fetch(`${BASE}${path}${buildQuery(params)}`, {
    method,
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })

  const text = await response.text()
  let payload: unknown = null
  if (text) {
    try {
      payload = JSON.parse(text)
    } catch {
      payload = text
    }
  }

  if (!response.ok) {
    const detail =
      payload && typeof payload === 'object' && 'detail' in (payload as Record<string, unknown>)
        ? (payload as Record<string, unknown>).detail
        : payload
    throw new ApiError(response.status, detail)
  }

  return payload as T
}

export const api = {
  get: <T>(path: string, params?: Record<string, unknown>) => request<T>(path, { params }),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: 'POST', body }),
  put: <T>(path: string, body?: unknown) => request<T>(path, { method: 'PUT', body }),
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: 'PATCH', body }),
  del: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
}
