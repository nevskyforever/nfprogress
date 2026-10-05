// @vitest-environment node
import { beforeAll, describe, expect, it, vi } from 'vitest'
import { generateAccountMasterKey, type AccountMasterKey } from '@/crypto'
import { NormalUserAuthRuntime } from '@/auth/userAuth'
import { ProjectMetadataMigrationRuntime, metadataImportSnapshot } from './projectMetadataMigrationRuntime'
import { sealProjectMetadataEvent, type ProjectMetadataEvent } from './projectMetadataCodec'
import type { MetadataMigrationStatus, ProjectMetadataMigrationRepository, ReceivedMetadataEvent, SealedMetadataGenesis } from '@/infrastructure/sqlite/projectMetadataMigrationRepository'
import { encryptedSyncV3Api, type V3PullItem, type V3MetadataPushItem } from '@/api/encryptedSyncV3'

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
  async function setup(pageSize = 200) {
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
      readImport: vi.fn<ProjectMetadataMigrationRepository["readImport"]>(),
      commitImportPage: vi.fn<ProjectMetadataMigrationRepository["commitImportPage"]>(),
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
      pull: vi.fn<typeof encryptedSyncV3Api.pull>(async () => ({ protocol_version: 3, encrypted_sync_version: 3, items: [], next_cursor: 0, has_more: false })),
      ack: vi.fn(async () => {}),
    }
    const runtime = new ProjectMetadataMigrationRuntime(auth, bindings as never, identity as never, keys as never,
      native as never, inbox as never, ack as never, api as never, pageSize)
    const capabilities = vi.spyOn((await import('@/api/encryptedSyncV2')).encryptedSyncV2Api, 'capabilities')
      .mockImplementation(async () => ({ supported_transport_version: 2, writer_transport_version: mode, cutover_epoch: 1 }) as never)
    return { runtime, native, api, ack, status, capabilities, mode: (value: number) => { mode = value } }
  }

  it('routes sealed v2 metadata through the all-reader-gated endpoint without altering v1 transport', async () => {
    const h=await setup()
    const push=vi.fn().mockResolvedValue({results:[{event_id:EVENT,server_sequence:1,duplicate:false}],current_cursor:1})
    Object.assign(h.api,{pushCoverMetadata:push})
    h.native.sealed.mockResolvedValue([{event_id:EVENT,project_id:PROJECT,revision:2,updated_at:NOW,nonce:Array(24).fill(1),ciphertext:Array(32).fill(2),metadata_codec_version:2}])
    await h.runtime.uploadOnce('local',DEVICE)
    expect(push).toHaveBeenCalledOnce();expect(h.api.pushMetadata).not.toHaveBeenCalled()
    expect(h.native.commitReceipt).toHaveBeenCalledWith(expect.anything(),EVENT,1,false,expect.anything())
    h.capabilities.mockRestore()
  })

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

  it('continues beyond sixteen pages using durable progress and resumes after a lost persistence response', async () => {
    const h = await setup(1)
    const boot = event().header.bootstrap_id
    const descriptors = vi.spyOn((await import('@/api/cloudProjects')).cloudProjectsApi, 'listBootstraps')
      .mockResolvedValue({ projects: [{ project_id: PROJECT, bootstrap_id: boot, state: 'active' }], current_cursor: 35 } as never)
    const history: ProjectMetadataEvent[] = []
    const wire: V3PullItem[] = []
    for (let i = 0; i < 35; i += 1) {
      const e = event(); e.header.event_id = `123e4567-e89b-42d3-a456-${String(i + 100).padStart(12, '0')}`
      if (i) { e.header.operation = 'update'; e.header.parent_event_ids = [history[i - 1]!.header.event_id]; e.header.revision = i + 1; e.header.generation = i + 1 }
      history.push(e)
      const object = await sealProjectMetadataEvent(amk, e)
      wire.push({ event: { event_id: e.header.event_id, device_id: DEVICE, server_sequence: i + 1, project_id: PROJECT,
        entity_id: PROJECT, entity_type: 'project_metadata', operation: 'upsert', revision: i + 1, updated_at: NOW, deleted_at: null }, object })
    }
    let cursor = 0; let lost = true
    const persisted: ProjectMetadataEvent[] = []
    const progress = () => ({ cursor, state: cursor === 35 ? 'complete' : 'running', blocker: null, event_count: cursor,
      metadata: cursor === 35 ? history[34]!.metadata : null, head: cursor === 35 ? history[34]!.header.event_id : null,
      tips: cursor ? [history[cursor - 1]!.header.event_id] : [] })
    h.native.readImport.mockImplementation(async () => progress() as never)
    h.native.commitImportPage.mockImplementation(async (_scope, _project, _boot, page) => {
      expect(page.expected_cursor).toBe(cursor)
      for (const item of page.events) persisted.push(JSON.parse(new TextDecoder().decode(new Uint8Array(item.plaintext))))
      cursor = page.next_cursor
      if (cursor === 5 && lost) { lost = false; throw new Error('lost_response_after_commit') }
      return progress() as never
    })
    h.api.pull.mockImplementation(async (_token, _device, since) => ({ protocol_version: 3, encrypted_sync_version: 3,
      items: wire.slice(since, since + 1), next_cursor: Math.min(since + 1, 35), has_more: since + 1 < 35 }) as never)
    await expect(h.runtime.importSnapshot('local', DEVICE, PROJECT)).rejects.toThrow('lost_response_after_commit')
    expect(cursor).toBe(5)
    await expect(h.runtime.importSnapshot('local', DEVICE, PROJECT)).rejects.toThrow('metadata_import_continuation_required')
    expect(cursor).toBe(21)
    const result = await h.runtime.importSnapshot('local', DEVICE, PROJECT)
    expect(result).toMatchObject({ cursor: 35, head: history[34]!.header.event_id })
    expect(persisted).toHaveLength(35)
    expect(h.api.pull.mock.calls[5]![2]).toBe(5)
    descriptors.mockRestore(); h.capabilities.mockRestore()
  })

  it('blocks a nonadvancing page or exhausted resource status without inventing import authority', async () => {
    const h = await setup()
    const boot = event().header.bootstrap_id
    const descriptors = vi.spyOn((await import('@/api/cloudProjects')).cloudProjectsApi, 'listBootstraps')
      .mockResolvedValue({ projects: [{ project_id: PROJECT, bootstrap_id: boot, state: 'active' }] } as never)
    h.native.readImport.mockResolvedValue({ cursor: 16, state: 'running', blocker: null, event_count: 0, metadata: null, head: null, tips: [] })
    h.api.pull.mockResolvedValue({ protocol_version: 3, encrypted_sync_version: 3, items: [], next_cursor: 16, has_more: true })
    await expect(h.runtime.importSnapshot('local', DEVICE, PROJECT)).rejects.toThrow('metadata_import_cursor')
    expect(h.native.commitImportPage).not.toHaveBeenCalled()
    h.native.readImport.mockResolvedValue({ cursor: 16, state: 'blocked', blocker: 'metadata_import_resource_limit', event_count: 3200, metadata: null, head: null, tips: [] })
    await expect(h.runtime.importSnapshot('local', DEVICE, PROJECT)).rejects.toThrow('metadata_import_resource_limit')
    descriptors.mockRestore(); h.capabilities.mockRestore()
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
  it('preserves stale subset resolutions across arrival orders and exact replay', () => {
    const first = event()
    const make = (id: number, parents: string[], revision: number, generation: number, operation: 'update' | 'resolution') => {
      const value = event()
      value.header = { ...value.header, event_id: `123e4567-e89b-42d3-a456-${String(id).padStart(12, '0')}`, parent_event_ids: parents, revision, generation, operation }
      return value
    }
    const a = make(101, [EVENT], 2, 2, 'update'), b = make(102, [EVENT], 2, 2, 'update'), c = make(103, [EVENT], 2, 2, 'update')
    const r = make(104, [a.header.event_id, b.header.event_id], 3, 3, 'resolution')
    const r2 = make(105, [c.header.event_id, r.header.event_id], 4, 4, 'resolution')
    for (const race of [[c, r], [r, c]]) {
      const prefix = [first, a, b, ...race]
      expect(metadataImportSnapshot(prefix, first.header.bootstrap_id, PROJECT)).toMatchObject({ head: null, metadata: null, tips: [c.header.event_id, r.header.event_id] })
      expect(metadataImportSnapshot([...prefix, r, r2], first.header.bootstrap_id, PROJECT)?.head).toBe(r2.header.event_id)
    }
    const invalid = structuredClone(r2); invalid.header.generation = 3
    expect(() => metadataImportSnapshot([first, a, b, c, r, invalid], first.header.bootstrap_id, PROJECT)).toThrow('metadata_import_revision')
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
