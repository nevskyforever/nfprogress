import { beforeEach, describe, expect, it, vi } from 'vitest'

const { apiList, apiGet, invoke } = vi.hoisted(() => ({
  apiList: vi.fn(), apiGet: vi.fn(), invoke: vi.fn(),
}))

vi.mock('@/api/projects', () => ({
  projectsApi: { list: apiList, get: apiGet },
}))
vi.mock('@tauri-apps/api/core', () => ({ invoke }))

import { getProjectReadRepository } from './projectReadRepository'

describe('project read repository resolver', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiList.mockResolvedValue([{ id: 'api' }])
    apiGet.mockResolvedValue({ id: 'api' })
    Object.assign(window, { __TAURI_INTERNALS__: undefined })
  })

  it('uses API outside Tauri', async () => {
    await expect(getProjectReadRepository().getProject('p')).resolves.toMatchObject({ id: 'api' })
    expect(apiGet).toHaveBeenCalledWith('p', undefined)
    expect(invoke).not.toHaveBeenCalled()
  })

  it('returns the native mirror error when it is unhealthy', async () => {
    Object.assign(window, { __TAURI_INTERNALS__: {} })
    invoke.mockResolvedValue({ mirror_status: 'dirty', projects: [], stages: [], progress_entries: [], project_order: [] })
    await expect(getProjectReadRepository().getProject('p')).rejects.toThrow('SQLite mirror is not healthy')
    expect(apiGet).not.toHaveBeenCalled()
  })

  it('uses healthy SQLite for a non-manual list', async () => {
    Object.assign(window, { __TAURI_INTERNALS__: {} })
    invoke.mockResolvedValue({ mirror_status: 'healthy', projects: [], stages: [], progress_entries: [], project_order: [] })
    await expect(getProjectReadRepository().listProjects({ sort: 'name' })).resolves.toEqual([])
    expect(invoke).toHaveBeenCalledWith('read_sqlite_projects')
    expect(apiList).not.toHaveBeenCalled()
  })
})
