import { afterEach, describe, expect, it, vi } from 'vitest'

import { documentsApi } from './documents'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('documentsApi', () => {
  it('records progress with the current document snapshot and stage scope', async () => {
    const content = {
      type: 'doc' as const,
      content: [{ type: 'paragraph', content: [{ type: 'text', text: 'Новая глава' }] }],
    }
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ changed: false, symbols: 11, progress: null }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await documentsApi.recordProgress(
      { projectId: 'project one', stageId: 'stage/one' }, content,
    )

    const [url, options] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('/api/documents/project%20one/progress?stage_id=stage%2Fone')
    expect(options.method).toBe('POST')
    expect(JSON.parse(String(options.body))).toEqual({ content })
  })
})
