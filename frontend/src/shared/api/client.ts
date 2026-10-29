export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

type QueryValue = string | number | boolean | null | undefined

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE'
  body?: unknown
  query?: Record<string, QueryValue>
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await fetch(path + toQueryString(options.query), {
    method: options.method ?? 'GET',
    headers: options.body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  })

  if (!response.ok) {
    throw new ApiError(response.status, await errorMessage(response))
  }
  if (response.status === 204) {
    return undefined as T
  }
  return (await response.json()) as T
}

function toQueryString(query: RequestOptions['query']): string {
  if (!query) return ''
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== null && value !== '') params.set(key, String(value))
  }
  const qs = params.toString()
  return qs ? `?${qs}` : ''
}

interface ValidationIssue {
  loc: (string | number)[]
  msg: string
}

async function errorMessage(response: Response): Promise<string> {
  try {
    const { detail } = (await response.json()) as { detail?: string | ValidationIssue[] }
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      return detail.map((d) => `${d.loc[d.loc.length - 1]}: ${d.msg}`).join('; ')
    }
  } catch {
    // fall through to generic message
  }
  return `Request failed with status ${response.status}`
}
