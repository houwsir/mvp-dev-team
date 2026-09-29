export interface ApiErrorBody {
  detail: string
  code: string
}

export interface PageResponse<T> {
  items: T[]
  page: number
  page_size: 20 | 50
  total: number
  total_pages: number
}

export interface Admin {
  id: number
  username: string
  display_name: string
}

export interface LoginResponse {
  admin: Admin
  expires_at: string
}
