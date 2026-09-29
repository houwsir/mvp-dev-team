import type { ApiErrorBody } from '../types/api'

export const baseURL =
  import.meta.env.VITE_API_BASE ?? 'http://localhost:8000/api'

export class ApiError extends Error {
  readonly status: number
  readonly code: string

  constructor(status: number, body: Partial<ApiErrorBody>) {
    super(body.detail || '请求失败，请稍后重试')
    this.name = 'ApiError'
    this.status = status
    this.code = body.code || 'UNKNOWN_ERROR'
  }
}

export async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers)
  if (init.body !== undefined && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  let response: Response
  try {
    response = await fetch(baseURL + path, {
      ...init,
      headers,
      credentials: 'include',
    })
  } catch {
    throw new ApiError(0, {
      detail: '网络连接失败，请检查服务是否可用',
      code: 'NETWORK_ERROR',
    })
  }

  const body = await response.json().catch(() => ({}))
  if (!response.ok) {
    if (
      response.status === 401 &&
      !path.startsWith('/auth/login') &&
      !path.startsWith('/auth/logout')
    ) {
      window.dispatchEvent(new CustomEvent('auth:expired'))
    }
    throw new ApiError(response.status, body)
  }

  return body as T
}

export function queryString(
  values: Record<string, string | number | undefined>,
): string {
  const params = new URLSearchParams()
  Object.entries(values).forEach(([key, value]) => {
    if (value !== undefined && value !== '') {
      params.set(key, String(value))
    }
  })
  const value = params.toString()
  return value ? '?' + value : ''
}
