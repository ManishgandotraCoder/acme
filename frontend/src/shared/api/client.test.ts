import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, request } from './client'

function mockFetch(status: number, body: unknown) {
  return vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response(body === undefined ? null : JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  )
}

describe('request', () => {
  afterEach(() => vi.restoreAllMocks())

  it('sends JSON and parses the response', async () => {
    const fetchSpy = mockFetch(200, { ok: true })

    const result = await request('/api/thing', { method: 'POST', body: { a: 1 } })

    expect(result).toEqual({ ok: true })
    const [url, init] = fetchSpy.mock.calls[0]
    expect(url).toBe('/api/thing')
    expect(init?.body).toBe('{"a":1}')
    expect(new Headers(init?.headers).get('Content-Type')).toBe('application/json')
  })

  it('builds query strings and skips empty values', async () => {
    const fetchSpy = mockFetch(200, [])
    await request('/api/employees', { query: { country: 'India', search: '', page: 2, x: undefined } })
    expect(fetchSpy.mock.calls[0][0]).toBe('/api/employees?country=India&page=2')
  })

  it('returns undefined for 204 No Content', async () => {
    mockFetch(204, undefined)
    await expect(request('/api/employees/1', { method: 'DELETE' })).resolves.toBeUndefined()
  })

  it('raises ApiError with the server message', async () => {
    mockFetch(409, { detail: "An employee with email 'a@b.com' already exists" })
    await expect(request('/api/employees')).rejects.toMatchObject({
      status: 409,
      message: "An employee with email 'a@b.com' already exists",
    })
  })

  it('flattens FastAPI validation errors into a readable message', async () => {
    mockFetch(422, { detail: [{ loc: ['body', 'country'], msg: 'Value error, Unsupported country' }] })
    const error = await request<never>('/api/employees').catch((e: ApiError) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect(error.message).toBe('country: Value error, Unsupported country')
  })
})
