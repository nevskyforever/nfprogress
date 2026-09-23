import { describe, expect, it, vi } from 'vitest'

const { invoke } = vi.hoisted(() => ({ invoke: vi.fn() }))
vi.mock('@tauri-apps/api/core', () => ({ invoke }))

import { SQLiteCloudIdentityRepository } from './cloudIdentityRepository'

describe('SQLiteCloudIdentityRepository', () => {
  it('uses only the typed canonical-user identity command shape', async () => {
    invoke.mockResolvedValueOnce({ local_account_id: 'local', device_id: 'device' })
    const repository = new SQLiteCloudIdentityRepository()
    await expect(repository.provision('123e4567-e89b-42d3-a456-426614174099')).resolves.toEqual({ local_account_id: 'local', device_id: 'device' })
    expect(invoke).toHaveBeenCalledWith('provision_cloud_identity', {
      command: { canonical_user_id: '123e4567-e89b-42d3-a456-426614174099' },
    })
  })

  it('reads an existing identity without accepting caller-selected device data', async () => {
    invoke.mockResolvedValueOnce(null)
    const repository = new SQLiteCloudIdentityRepository()
    await expect(repository.read('123e4567-e89b-42d3-a456-426614174099')).resolves.toBeNull()
    expect(invoke).toHaveBeenCalledWith('read_cloud_identity', {
      command: { canonical_user_id: '123e4567-e89b-42d3-a456-426614174099' },
    })
  })
})
