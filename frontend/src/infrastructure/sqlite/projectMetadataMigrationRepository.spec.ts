import { beforeEach, describe, expect, it, vi } from 'vitest'
vi.mock('@tauri-apps/api/core', () => ({ invoke: vi.fn().mockResolvedValue(undefined) }))
import { invoke } from '@tauri-apps/api/core'
import { SQLiteProjectMetadataMigrationRepository } from './projectMetadataMigrationRepository'
const scope = { account_id: 'local', canonical_user_id: 'user', device_id: 'device' }
describe('metadata native authority adapter', () => {
  beforeEach(() => vi.clearAllMocks())
  it('canonicalizes server UTC descriptors without changing opaque encrypted bytes', async () => {
    await new SQLiteProjectMetadataMigrationRepository().commitV3Page(scope, 0, {
      protocol_version: 3, encrypted_sync_version: 3, next_cursor: 1, has_more: false,
      items: [{ event: { event_id: 'event', device_id: 'peer', server_sequence: 1, project_id: 'project', entity_id: 'project',
        entity_type: 'project_metadata', operation: 'upsert', revision: 2, updated_at: '2026-09-29T00:00:00Z', deleted_at: null },
        object: { crypto_version: 1, aad_version: 1, nonce: new Uint8Array([1]), ciphertext: new Uint8Array([2]) } }],
    })
    expect(invoke).toHaveBeenCalledWith('commit_v3_sync_inbound_page', { command: { ...scope,
      expected_cursor: 0, next_cursor: 1, has_more: false, items: [{ event_id: 'event', server_sequence: 1, source_device_id: 'peer',
        project_id: 'project', entity_id: 'project', entity_type: 'project_metadata', operation: 'upsert', revision: 2,
        updated_at: '2026-09-29T00:00:00.000000Z', deleted_at: null,
        envelope: { crypto_version: 1, aad_version: 1, nonce: 'AQ', ciphertext: 'Ag' } }] } })
  })
  it('persists import cursors and verified pages through account-scoped native commands', async () => {
    const native = new SQLiteProjectMetadataMigrationRepository()
    await native.readImport(scope, 'project', 'bootstrap')
    const page = { expected_cursor: 16, next_cursor: 17, has_more: true, page_events: 1, page_identity: 'a'.repeat(64), events: [] }
    await native.commitImportPage(scope, 'project', 'bootstrap', page)
    expect(invoke).toHaveBeenCalledWith('read_project_metadata_import', { scope, projectId: 'project', bootstrapId: 'bootstrap' })
    expect(invoke).toHaveBeenCalledWith('commit_project_metadata_import_page', { scope, projectId: 'project', bootstrapId: 'bootstrap', page })
  })

})
