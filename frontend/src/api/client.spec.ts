import { afterEach, describe, expect, it, vi } from 'vitest'

import { apiRequest } from './client'
import { resetSessionTokenProvider, setSessionTokenProvider } from './sessionToken'

afterEach(() => {
  resetSessionTokenProvider()
  delete window.__NFPROGRESS_RUNTIME__
  vi.unstubAllGlobals()
})

describe('apiRequest', () => {
  it('uses the runtime base URL and conditionally discovered session token', async () => {
    window.__NFPROGRESS_RUNTIME__ = { apiBaseUrl: 'http://127.0.0.1:43117/' }
    setSessionTokenProvider({
      getSessionToken: async () => 'session-token',
    })
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
    expect(url).toBe('http://127.0.0.1:43117/health')
    expect(new Headers(options.headers).get('X-NFProgress-Token')).toBe('session-token')
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
