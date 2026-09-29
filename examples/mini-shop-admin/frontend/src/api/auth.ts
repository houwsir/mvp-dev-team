import type { Admin, LoginResponse } from '../types/api'
import { request } from './client'

export function login(username: string, password: string) {
  return request<LoginResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
}

export function logout() {
  return request<{ success: true }>('/auth/logout', { method: 'POST' })
}

export function getCurrentAdmin() {
  return request<Admin>('/auth/me')
}
