import { beforeEach, describe, expect, it, vi } from 'vitest'

import { invoke } from '@tauri-apps/api/core'
import { TauriProgressRepository } from './progressRepository'

vi.mock('@tauri-apps/api/core', () => ({ invoke: vi.fn() }))

describe('TauriProgressRepository', () => {
  beforeEach(() => vi.mocked(invoke).mockReset())

  it('uses separate narrow commands for project and stage progress', async () => {
    vi.mocked(invoke).mockResolvedValue({ project: {}, entry: {}, added_symbols: 1 })
    const repository = new TauriProgressRepository()

    await repository.add({ kind: 'manual', projectId: 'p/1', newTotal: 10 })
    expect(invoke).toHaveBeenLastCalledWith('add_project_progress', {
      projectId: 'p/1',
      newTotal: 10,
    })

    await repository.add({ kind: 'manual', projectId: 'p/1', stageId: 's/1', newTotal: 12 })
    expect(invoke).toHaveBeenLastCalledWith('add_stage_progress', {
      projectId: 'p/1',
      stageId: 's/1',
      newTotal: 12,
    })
  })

  it('passes stable entry identity and optional stage to the delete command', async () => {
    vi.mocked(invoke).mockResolvedValue({})
    await new TauriProgressRepository().remove({
      projectId: 'p', entryId: 'entry/1', stageId: 'stage',
    })
    expect(invoke).toHaveBeenCalledWith('delete_progress', {
      projectId: 'p', entryId: 'entry/1', stageId: 'stage',
    })
  })
})
