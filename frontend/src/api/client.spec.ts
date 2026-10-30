import { afterEach, describe, expect, it, vi } from 'vitest'

import { ApiResponseTooLargeError, apiErrorMessage, apiRequest } from './client'
afterEach(() => {
  vi.unstubAllGlobals()
})

describe('apiRequest', () => {
  it('uses the configured web API base URL without desktop session plumbing', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ status: 'ok' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await apiRequest<{ status: string }>('/health')

    expect(fetchMock).toHaveBeenCalledOnce()
    const [url, options] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('/health')
    expect(new Headers(options.headers).get('X-NFProgress-Token')).toBeNull()
  })

  it('surfaces the backend domain error message and code', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            detail: { code: 'conflict', message: 'Проект с таким именем уже существует.' },
          }),
          { status: 409, headers: { 'Content-Type': 'application/json' } },
        ),
      ),
    )

    const request = apiRequest('/api/projects', {
      method: 'POST',
      body: { name: 'Дом у моря' },
    })

    await expect(request).rejects.toMatchObject({
      status: 409,
      code: 'conflict',
      message: 'Проект с таким именем уже существует.',
    })
  })

  it('does not classify malformed or oversized JSON as a connection error', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response('{bad', { status: 200 }))
      .mockResolvedValueOnce(new Response('{bad', { status: 200 }))
      .mockResolvedValueOnce(new Response('123456', { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)
    await expect(apiRequest('/invalid')).rejects.toBeInstanceOf(SyntaxError)
    await expect(apiRequest('/invalid', { maxResponseBytes: 64 })).rejects.toBeInstanceOf(SyntaxError)
    await expect(apiRequest('/large', { maxResponseBytes: 2 })).rejects.toBeInstanceOf(ApiResponseTooLargeError)
    const damaged = new Response('{}', { status: 200 })
    vi.spyOn(damaged, 'json').mockRejectedValueOnce(new TypeError('invalid content encoding'))
    fetchMock.mockResolvedValueOnce(damaged)
    await expect(apiRequest('/damaged')).rejects.toThrow('invalid content encoding')
  })
})

describe('apiErrorMessage', () => {
  it('preserves native string errors for the startup gate', () => {
    expect(apiErrorMessage('Corrupt SQLite schema: project ordering is incomplete'))
      .toBe('Corrupt SQLite schema: project ordering is incomplete')
  })
})
