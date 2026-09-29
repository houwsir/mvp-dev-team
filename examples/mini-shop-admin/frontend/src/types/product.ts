import type { PageResponse } from './api'

export type ProductStatus = 'active' | 'inactive'

export interface Product {
  id: number
  name: string
  main_image_url: string
  price: string
  stock: number
  description: string | null
  status: ProductStatus
  created_at: string
  updated_at: string
}

export interface ProductPayload {
  name: string
  main_image_url: string
  price: string
  stock: number
  description: string | null
}

export interface ProductQuery {
  page: number
  page_size: 20 | 50
  keyword?: string
  status?: ProductStatus
}

export type ProductPage = PageResponse<Product>
