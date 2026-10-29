/** Generic paginated response (backend: app/core/pagination.py). */
export interface Page<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}
