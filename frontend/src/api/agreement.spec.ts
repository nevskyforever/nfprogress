import { afterEach, describe, expect, it, vi } from 'vitest'

import { contentApi } from './content'
import { settingsApi } from './settings'
import { resetSessionTokenProvider } from './sessionToken'

afterEach(() => {
  resetSessionTokenProvider()
  vi.unstubAllGlobals()
})

function jsonResponse(payload: unknown): Response {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('user agreement API client', () => {
  it('loads the shared agreement for a supported language', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({ id: 'agreement-v1', language: 'pt_BR', html: '<html></html>' }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await contentApi.agreement('pt_BR')

    expect(fetchMock.mock.calls[0]?.[0]).toBe('/api/content/agreement?language=pt_BR')
  })

  it('accepts the exact agreement version instead of patching the legacy flag directly', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({ values: { user_agreement: true } }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await settingsApi.acceptUserAgreement('agreement-v1')

    const [url, options] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('/api/settings/user-agreement/accept')
    expect(options.method).toBe('POST')
    expect(JSON.parse(String(options.body))).toEqual({ agreement_id: 'agreement-v1' })
  })
})
