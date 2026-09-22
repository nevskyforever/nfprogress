import { beforeEach, describe, expect, it, vi } from 'vitest'

const invoke = vi.hoisted(() => vi.fn())
vi.mock('@tauri-apps/api/core', () => ({ invoke }))

import { SQLiteCloudAccountBindingRepository } from './cloudAccountBindingRepository'

describe('SQLiteCloudAccountBindingRepository', () => {
  beforeEach(() => invoke.mockReset())

  it('maps the opaque local account and canonical backend user separately', async () => {
    invoke.mockResolvedValueOnce('created')
    const repository = new SQLiteCloudAccountBindingRepository()
    await expect(repository.ensure('local-scope', '00000000-0000-0000-0000-000000000101')).resolves.toBe('created')
    expect(invoke).toHaveBeenCalledWith('ensure_cloud_account_binding', {
      command: {
        local_account_id: 'local-scope',
        canonical_user_id: '00000000-0000-0000-0000-000000000101',
      },
    })
  })
})
