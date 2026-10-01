// @vitest-environment node
import { beforeAll, describe, expect, it, vi } from 'vitest'
import { generateAccountMasterKey, type AccountMasterKey } from '@/crypto'
import { NormalUserAuthRuntime } from '@/auth/userAuth'
import { ProjectMetadataMigrationRuntime, metadataImportSnapshot } from './projectMetadataMigrationRuntime'
import { sealProjectMetadataEvent, type ProjectMetadataEvent } from './projectMetadataCodec'
import type { MetadataMigrationStatus, ProjectMetadataMigrationRepository, ReceivedMetadataEvent, SealedMetadataGenesis } from '@/infrastructure/sqlite/projectMetadataMigrationRepository'
import type { V3MetadataPushItem } from '@/api/encryptedSyncV3'

const USER = '123e4567-e89b-42d3-a456-426614174099'
const DEVICE = '123e4567-e89b-42d3-a456-426614174003'
const EVENT = '123e4567-e89b-42d3-a456-426614174010'
const NOW = '2026-09-21T00:00:00.000000Z'
const PROJECT = 'project'
const event = (): ProjectMetadataEvent => ({
  version: 1,
  header: { account_id: USER, bootstrap_id: '123e4567-e89b-42d3-a456-426614174002',
    device_id: DEVICE, entity_id: PROJECT, event_id: EVENT, generation: 1, operation: 'create',
    parent_event_ids: [], project_id: PROJECT, revision: 1, updated_at: NOW },
  metadata: { name: 'Private name', goal: null, infinite: true, unit: 'symbols', deadline: null,
    status: 'active', personal_goal: 100, auto_freeze: true, streak_enabled: true,
    work_method: 'manual', stages_enabled: false, combine_stage_mindmaps: false }, deleted_at: null,
})

describe('explicit metadata migration runtime', () => {
  let amk: AccountMasterKey
  beforeAll(async () => { amk = await generateAccountMasterKey() })
  async function setup() {
    const auth = new NormalUserAuthRuntime({
      login: vi.fn().mockResolvedValue({ access_token: 'token', refresh_token: 'refresh', access_expires_in: 60 }),
      refresh: vi.fn(), logout: vi.fn(), me: vi.fn().mockResolvedValue({ id: USER, username: 'u', email: 'u@example.test',
        email_verified: true, role: 'user', status: 'active', created_at: NOW }),
    })
    await auth.login('u', 'p')
    const context = auth.requireContext()
    let mode = 3
    const bindings = { ensureForCurrentUser: vi.fn(async () => ({ context })) }
    const identity = { read: vi.fn(async () => ({ local_account_id: 'local', device_id: DEVICE })) }
    const keys = { leaseForAccount: vi.fn(() => ({ localAccountId: 'local', canonicalUserId: USER,
      authEpoch: context.authEpoch, isCurrent: () => true, use: (action: (key: AccountMasterKey) => Promise<unknown>) => action(amk) })) }
    const status: MetadataMigrationStatus = { state: 'legacy_candidate_present', candidate_id: 'candidate', event_id: null, blockers: [], genesis_tips: 0 }
    const native = {
      capture: vi.fn(async () => 'candidate'), status: vi.fn(async () => status), prepare: vi.fn(async () => EVENT),
      unsealed: vi.fn(async () => [event()]),
      commitSealed: vi.fn<ProjectMetadataMigrationRepository['commitSealed']>(async () => {}),
      sealed: vi.fn<() => Promise<SealedMetadataGenesis[]>>(async () => []),
      commitReceipt: vi.fn(async () => {}),
      received: vi.fn<() => Promise<ReceivedMetadataEvent[]>>(async () => []),
      apply: vi.fn(async () => 'applied'),
      commitV3Page: vi.fn(async () => ({ committed_cursor: 1, new_events: 1, replayed_events: 0, has_more: false })),
    }
    const inbox = { readPullState: vi.fn(async () => ({ pull_cursor: 0, ack_cursor: 0 })) }
    const ack = { prepare: vi.fn(async () => ({ current_ack_cursor: 0, candidate_cursor: 1 })), commit: vi.fn(async () => 'advanced') }
    const api = { readerReady: vi.fn(async () => {}), cutover: vi.fn(async () => ({ writer_transport_version: 3, cutover_epoch: 2 })),
      pushMetadata: vi.fn<(_token: string, _device: string, items: V3MetadataPushItem[]) => Promise<{ protocol_version: number; encrypted_sync_version: number; results: { event_id: string; server_sequence: number; duplicate: boolean }[]; current_cursor: number }>>(async () => ({ protocol_version: 3, encrypted_sync_version: 3, results: [{ event_id: EVENT, server_sequence: 1, duplicate: false }], current_cursor: 1 })),
      pull: vi.fn(async () => ({ protocol_version: 3, encrypted_sync_version: 3, items: [], next_cursor: 0, has_more: false })),
      ack: vi.fn(async () => {}),
    }
    const runtime = new ProjectMetadataMigrationRuntime(auth, bindings as never, identity as never, keys as never,
      native as never, inbox as never, ack as never, api as never)
    const capabilities = vi.spyOn((await import('@/api/encryptedSyncV2')).encryptedSyncV2Api, 'capabilities')
      .mockImplementation(async () => ({ supported_transport_version: 2, writer_transport_version: mode, cutover_epoch: 1 }) as never)
    return { runtime, native, api, ack, status, capabilities, mode: (value: number) => { mode = value } }
  }

  it('prepares the mode-two prerequisite only through a separate explicit action', async () => {
    const h = await setup(); h.mode(1)
    const v2 = (await import('@/api/encryptedSyncV2')).encryptedSyncV2Api
    const prepare = vi.spyOn(v2, 'cutover').mockResolvedValue({ supported_transport_version: 2, writer_transport_version: 2, cutover_epoch: 2 })
    expect(prepare).not.toHaveBeenCalled()
    await h.runtime.prepareTransport('local', DEVICE)
    expect(prepare).toHaveBeenCalledWith('token', 1)
    expect(h.api.readerReady).not.toHaveBeenCalled(); expect(h.api.cutover).not.toHaveBeenCalled()
    expect(h.native.prepare).not.toHaveBeenCalled()
    h.mode(2); await h.runtime.prepareTransport('local', DEVICE)
    expect(prepare).toHaveBeenCalledTimes(1)
    prepare.mockRestore(); h.capabilities.mockRestore()
  })

  it('requires explicit mode and keeps missing-lineage candidate as a visible blocker', async () => {
    const h = await setup()
    h.mode(2)
    await expect(h.runtime.begin('local', DEVICE, PROJECT)).rejects.toThrow('metadata_mode_3_required')
    expect(h.native.capture).not.toHaveBeenCalled()
    h.mode(3)
    h.status.state = 'blocked_missing_bootstrap'
    h.status.blockers.push('bootstrap_lineage_missing')
    expect((await h.runtime.begin('local', DEVICE, PROJECT)).state).toBe('blocked_missing_bootstrap')
    expect(h.native.prepare).not.toHaveBeenCalled()
    h.capabilities.mockRestore()
  })

  it('seals once and retries the same durable event after a lost upload response', async () => {
    const h = await setup()
    h.status.state = 'legacy_local'
    h.status.candidate_id = null
    h.native.capture.mockImplementationOnce(async () => {
      h.status.state = 'legacy_candidate_present'
      h.status.candidate_id = 'candidate'
      return 'candidate'
    })
    expect(await h.runtime.begin('local', DEVICE, PROJECT)).toMatchObject({ candidate_id: 'candidate' })
    expect(h.native.capture).toHaveBeenCalledOnce()
    expect(h.native.prepare).toHaveBeenCalledTimes(1)
    h.status.event_id = EVENT
    await h.runtime.begin('local', DEVICE, PROJECT)
    expect(h.native.capture).toHaveBeenCalledOnce()
    expect(h.native.prepare).toHaveBeenCalledOnce()
    expect(await h.runtime.sealOnce('local', DEVICE)).toBe(1)
    const [,, nonce, ciphertext] = h.native.commitSealed.mock.calls[0]!
    expect(ciphertext).toBeInstanceOf(Uint8Array)
    expect(Buffer.from(ciphertext).includes(Buffer.from('Private name'))).toBe(false)
    h.native.unsealed.mockResolvedValue([])
    h.native.sealed.mockResolvedValue([{ event_id: EVENT, project_id: PROJECT, revision: 1, updated_at: NOW,
      nonce: Array.from(nonce), ciphertext: Array.from(ciphertext) }])
    h.api.pushMetadata.mockRejectedValueOnce(new Error('lost_response'))
    await expect(h.runtime.uploadOnce('local', DEVICE)).rejects.toThrow('lost_response')
    expect(h.native.commitReceipt).not.toHaveBeenCalled()
    expect(await h.runtime.uploadOnce('local', DEVICE)).toBe(1)
    expect(h.api.pushMetadata.mock.calls[0]![2][0]!.event.event_id).toBe(EVENT)
    expect(h.api.pushMetadata.mock.calls[1]![2][0]!.event.event_id).toBe(EVENT)
    expect(h.native.commitReceipt).toHaveBeenCalledTimes(1)
    h.capabilities.mockRestore()
  })

  it('pulls durably, decrypts exact context and leaves malformed metadata ACK-blocked', async () => {
    const h = await setup()
    const sealed = await sealProjectMetadataEvent(amk, event())
    h.native.received.mockResolvedValueOnce([{ event_id: EVENT, server_sequence: 1, source_device_id: DEVICE,
      project_id: PROJECT, entity_id: PROJECT, revision: 1, updated_at: NOW, deleted_at: null,
      operation: 'upsert', crypto_version: 1, aad_version: 1, nonce: Array.from(sealed.nonce),
      ciphertext: Array.from(sealed.ciphertext) } satisfies ReceivedMetadataEvent])
    expect((await h.runtime.applyOnce('local', DEVICE)).applied).toBe(1)
    expect(h.native.apply).toHaveBeenCalledTimes(1)
    h.native.received.mockResolvedValueOnce([{ event_id: EVENT, server_sequence: 1, source_device_id: DEVICE,
      project_id: PROJECT, entity_id: 'wrong', revision: 1, updated_at: NOW, deleted_at: null,
      operation: 'upsert', crypto_version: 1, aad_version: 1, nonce: Array.from(sealed.nonce),
      ciphertext: Array.from(sealed.ciphertext) } satisfies ReceivedMetadataEvent])
    expect((await h.runtime.applyOnce('local', DEVICE)).blocked).toEqual([EVENT])
    expect(h.native.apply).toHaveBeenCalledTimes(1)
    h.capabilities.mockRestore()
  })
})

describe('authenticated second-device metadata import', () => {
  it('derives a sole authenticated head and preserves a concurrent rename conflict', () => {
    const first = event(); const beta = event(); const gamma = event()
    beta.header = { ...first.header, event_id: '123e4567-e89b-42d3-a456-426614174011', operation: 'update', parent_event_ids: [EVENT], revision: 2, generation: 2 }
    gamma.header = { ...beta.header, event_id: '123e4567-e89b-42d3-a456-426614174012', updated_at: '2026-09-22T00:00:00.000000Z' }
    beta.metadata = { ...first.metadata!, name: 'Project Beta' }; gamma.metadata = { ...first.metadata!, name: 'Project Gamma' }
    const boot = first.header.bootstrap_id
    expect(metadataImportSnapshot([first], boot, PROJECT)?.metadata?.name).toBe('Private name')
    expect(metadataImportSnapshot([first, beta], boot, PROJECT)?.metadata?.name).toBe('Project Beta')
    for (const branches of [[beta, gamma], [gamma, beta]]) {
      expect(metadataImportSnapshot([first, ...branches], boot, PROJECT)).toMatchObject({ head: null, metadata: null, tips: [beta.header.event_id, gamma.header.event_id] })
    }
    const resolution = event(); resolution.header = { ...beta.header, event_id: '123e4567-e89b-42d3-a456-426614174013', operation: 'resolution', parent_event_ids: [beta.header.event_id, gamma.header.event_id], revision: 3, generation: 3 }
    resolution.metadata = { ...first.metadata!, name: 'Resolved' }
    expect(metadataImportSnapshot([first, beta, gamma, resolution], boot, PROJECT)?.metadata?.name).toBe('Resolved')
    resolution.header.parent_event_ids = [beta.header.event_id]
    expect(() => metadataImportSnapshot([first, beta, gamma, resolution], boot, PROJECT)).toThrow()
  })
  it('requires complete lineage and retains legacy import when no metadata exists', () => {
    const first = event()
    expect(metadataImportSnapshot([], first.header.bootstrap_id, PROJECT)).toBeNull()
    expect(() => metadataImportSnapshot([first], EVENT, PROJECT)).toThrow('metadata_import_lineage')
    first.header.operation = 'update'; first.header.revision = 2; first.header.generation = 2
    first.header.parent_event_ids = ['123e4567-e89b-42d3-a456-426614174014']
    expect(() => metadataImportSnapshot([first], first.header.bootstrap_id, PROJECT)).toThrow('metadata_import_dependency')
  })
})
