import { afterEach, describe, expect, it, vi } from 'vitest'

import { apiRequest } from './client'
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
})
