import { afterEach, describe, expect, it, vi } from 'vitest'

import { notesApi } from './notes'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('notesApi', () => {
  it('uses stable encoded IDs and preserves the selected stage scope', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ id: 'project:one:note/id' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await notesApi.update(
      { projectId: 'project one', stageId: 'stage/one' },
      'project:one:note/id',
      { pinned: true, tags: ['герои'] },
    )

    const [url, options] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe(
      '/api/projects/project%20one/notes/project%3Aone%3Anote%2Fid?stage_id=stage%2Fone',
    )
    expect(options.method).toBe('PATCH')
    expect(JSON.parse(String(options.body))).toEqual({ pinned: true, tags: ['герои'] })
  })

  it('sends map data through the shared API client rather than a local mock', async () => {
    const response = {
      project_id: 'project-id',
      stage_id: null,
      name: 'Проект',
      data: { nodeData: { id: 'root', topic: 'Проект', children: [] } },
      combined: false,
      read_only: false,
      has_empty_completed_stage_map: false,
    }
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(response), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await notesApi.saveMindMap(
      { projectId: 'project-id' },
      { nodeData: { id: 'root', topic: 'Проект', children: [] } },
    )

    const [url, options] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('/api/projects/project-id/mindmap')
    expect(options.method).toBe('PUT')
    expect(JSON.parse(String(options.body))).toHaveProperty('data.nodeData.id', 'root')
  })
})
