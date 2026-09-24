import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@tauri-apps/api/core', () => ({ invoke: vi.fn() }))

import { invoke } from '@tauri-apps/api/core'
import { SQLiteCloudProjectBootstrapRepository } from './cloudProjectBootstrapRepository'

const SCOPE = {
  project_id: 'project', account_id: 'account',
  device_id: '123e4567-e89b-42d3-a456-426614174001',
  bootstrap_id: '123e4567-e89b-42d3-a456-426614174002',
}

describe('cloud project bootstrap SQLite IPC boundary', () => {
  beforeEach(() => vi.mocked(invoke).mockReset().mockResolvedValue({}))

  it('passes only explicit account/device/token scope to state transitions', async () => {
    const repository = new SQLiteCloudProjectBootstrapRepository()
    await repository.confirmRegistration(SCOPE, 'initializing', 7)
    await repository.capture(SCOPE)
    await repository.cohort(SCOPE)
    await repository.markCompleting(SCOPE)
    await repository.markReady(SCOPE)
    await repository.setPaused(SCOPE, true)

    expect(vi.mocked(invoke).mock.calls).toEqual([
      ['confirm_cloud_project_registration', { command: { ...SCOPE, remote_state: 'initializing', remote_high_water: 7 } }],
      ['capture_initial_note_sync_intents', { command: SCOPE }],
      ['read_initial_note_cohort_status', { command: SCOPE }],
      ['mark_cloud_project_bootstrap_completing', { command: SCOPE }],
      ['mark_cloud_project_bootstrap_ready', { command: SCOPE }],
      ['set_cloud_project_bootstrap_paused', { command: SCOPE, paused: true }],
    ])
  })

  it('keeps local creation and explicit remote import as separate operations', async () => {
    const repository = new SQLiteCloudProjectBootstrapRepository()
    await repository.prepare('project', 'account', SCOPE.device_id, 'upload_existing')
    await repository.importRemote('remote-project', 'Remote', 'account', SCOPE.device_id, SCOPE.bootstrap_id, 12)

    expect(invoke).toHaveBeenNthCalledWith(1, 'prepare_cloud_project_bootstrap', { command: {
      project_id: 'project', account_id: 'account', device_id: SCOPE.device_id, mode: 'upload_existing',
    } })
    expect(invoke).toHaveBeenNthCalledWith(2, 'import_remote_cloud_project', { command: {
      project_id: 'remote-project', display_name: 'Remote', account_id: 'account',
      device_id: SCOPE.device_id, bootstrap_id: SCOPE.bootstrap_id, remote_high_water: 12,
    } })
  })
})
