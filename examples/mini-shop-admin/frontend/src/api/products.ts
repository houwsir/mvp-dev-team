import type {
  Product,
  ProductPage,
  ProductPayload,
  ProductQuery,
  ProductStatus,
} from '../types/product'
import { queryString, request } from './client'

const productPath = (productId: number | string) =>
  '/products/' + encodeURIComponent(String(productId))

export function getProducts(query: ProductQuery) {
  return request<ProductPage>(
    '/products' +
      queryString({
        page: query.page,
        page_size: query.page_size,
        keyword: query.keyword,
        status: query.status,
      }),
  )
}

export function getProduct(productId: number | string) {
  return request<Product>(productPath(productId))
}

export function createProduct(payload: ProductPayload) {
  return request<Product>('/products', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateProduct(
  productId: number | string,
  payload: ProductPayload,
) {
  return request<Product>(productPath(productId), {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function updateProductStock(
  productId: number | string,
  stock: number,
) {
  return request<Product>(productPath(productId) + '/stock', {
    method: 'PATCH',
    body: JSON.stringify({ stock }),
  })
}

export function updateProductStatus(
  productId: number | string,
  status: ProductStatus,
) {
  return request<Product>(productPath(productId) + '/status', {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  })
}
