// @vitest-environment node
import { afterEach, expect, it, vi } from 'vitest'
import { cloudProjectsApi } from '@/api/cloudProjects'
import { encryptedSyncV2Api } from '@/api/encryptedSyncV2'
import { encryptedSyncV3Api } from '@/api/encryptedSyncV3'
import { metadataSetup, metadataRow, applyMetadata } from './metadataPrefix.testFixture'
import { received } from './legacyNoteApply.testFixture'
import { contentRow } from './noteTransport.testFixture'
import { sealEmptyLocalProject } from './localAuthority'
import { scope, amk } from './bootstrap.testFixture'
import { composeReplayOrderedContent, composeReplayMetadata, type MetadataPort } from './replayMetadata'
import { replayCoverage, type ReplaySnapshot } from './replayInventory'
import { BrowserContentNoteApplyRuntime } from './contentNoteApply'
import { stageRow } from './stageApply.testFixture'
import { orderRow } from './stageOrder.testFixture'

afterEach(() => vi.restoreAllMocks())

async function setup(contentOptions: Parameters<typeof contentRow>[2] = {}, withStructure = false) {
  const base = await metadataSetup(), m = await metadataRow(base, 1, { change: e => { e.metadata!.status = 'активен' } })
  await applyMetadata(base, m)
  const f = { ...base, m }
  if (withStructure) {
    const structural = { ...f, metadataEvent: m.event }
    const stage = await stageRow(structural as never, 2, { change: e => { e.header.entity_id = 's0' } })
    await orderRow({ ...structural, stageEvents: [stage.event] } as never, 3)
  }
  const noteSequence = withStructure ? 4 : 2, contentSequence = noteSequence + 1
  const root = await received(f, noteSequence, 1, null, 'upsert', p => { p.note.metadata = {} }, 'content-note')
  const wire = JSON.parse(root.wire_item); wire.event.device_id = m.event.header.device_id; root.wire_item = JSON.stringify(wire)
  const h = m.event.header, metadata = m.event.metadata!
  f.db.localProjects![0] = await sealEmptyLocalProject(scope, { id: 'p', name: metadata.name, goal: metadata.goal,
    infinite: metadata.infinite, unit: metadata.unit, status: metadata.status,
    created_at: h.updated_at, updated_at: h.updated_at, payload: {} }, amk)
  await contentRow(f, contentSequence, { mutation: 'update', parent: root.event_id, ...contentOptions })
  let manifest = { record_version: 5 as const, contract_version: 5 as const, metadata_cursor: 1, applied_cursor: 1,
    source_seeds: [{ project_id: 'p', bootstrap_id: f.b.bootstrap_id, origin_device_id: h.device_id,
      genesis_event_id: h.event_id, initial_event_count: 1, initial_max_server_sequence: noteSequence }],
    account_id: scope.accountId, device_id: scope.deviceId, canonical_user_id: scope.canonicalUserId,
    generation: crypto.randomUUID(), anchor: { registry: { current_cursor: contentSequence, projects: [{ project_id: 'p',
      bootstrap_id: f.b.bootstrap_id, origin_device_id: h.device_id, state: 'active' as const,
      initial_event_count: 1, initial_max_server_sequence: noteSequence }] },
    transport: { supported_transport_version: 2 as const, writer_transport_version: 3 as const, cutover_epoch: 1 } },
    receive_cursor: contentSequence, ciphertext_bytes: 0, phase: 'received' as const, revision: 1 }
  const snapshot = (): ReplaySnapshot => structuredClone({ manifest, rows: f.db.inbox, bindings: f.db.projectBindings,
    owners: f.db.ownerHeads, sources: f.db.localProjects, notes: f.db.localNotes, noteHistory: f.db.legacyNoteHistory }) as ReplaySnapshot
  vi.spyOn(cloudProjectsApi, 'listBootstraps').mockImplementation(async () => structuredClone(manifest.anchor.registry))
  vi.spyOn(encryptedSyncV2Api, 'capabilities').mockImplementation(async () => structuredClone(manifest.anchor.transport))
  vi.spyOn(encryptedSyncV3Api, 'pullRaw').mockImplementation(async (_token, _device, since) => JSON.stringify({
    protocol_version: 3, encrypted_sync_version: 3, items: (f.db.inbox.slice(since) as Array<{ wire_item: string }>).map(row => JSON.parse(row.wire_item)),
    next_cursor: contentSequence, has_more: false }))
  const port: MetadataPort = { read: async () => snapshot(), transaction: expected => async (s, stores, mode, schedule) => {
    expect(snapshot()).toEqual(expected)
    const result = await f.transaction(s, stores, mode, schedule)
    if (mode === 'readwrite' && result === 'applied') {
      const sequence = manifest.applied_cursor + 1
      manifest = replayCoverage(manifest, f.db.inbox[sequence - 1] as never) as typeof manifest
    }
    return result
  } }
  const run = () => composeReplayOrderedContent(port, scope, new AbortController().signal, () => true,
    f.auth, f.bindings as never, f.keys as never)
  return { f, snapshot, run, port }
}

it('commits the Legacy prefix before one real Content owner update and reopens without writes', async () => {
  const { f, snapshot, run, port } = await setup()
  await expect(composeReplayMetadata(port, scope, new AbortController().signal, () => true,
    f.auth, f.bindings as never, f.keys as never, true, true)).rejects.toThrow()
  expect(snapshot().manifest!.applied_cursor).toBe(1)
  expect(await run()).toMatchObject({ kind: 'bounded_ordered_content_update_applied', contentProofs: 1,
    noteProofs: 1, projectOpened: false, ready: false })
  const applied = snapshot()
  expect(applied.rows.map(row => row.state)).toEqual(['applied', 'note_proven', 'content_note_proven'])
  expect(applied.manifest!.applied_cursor).toBe(3)
  expect(await run()).toMatchObject({ contentProofs: 1 })
  expect(snapshot()).toEqual(applied)
})

it('commits Metadata, Stage, StageOrder, Legacy and Content in account sequence', async () => {
  const { snapshot, run } = await setup({}, true)
  expect(await run()).toMatchObject({ metadataProofs: 1, stageProofs: 1, stageOrderProofs: 1,
    noteProofs: 1, contentProofs: 1, ownerProofs: 5 })
  expect(snapshot().rows.map(row => row.state)).toEqual([
    'applied', 'stage_proven', 'stage_order_proven', 'note_proven', 'content_note_proven',
  ])
})

it('rejects corrupt terminal wire before committing the valid prefix', async () => {
  const { snapshot, run, f } = await setup()
  const row = f.db.inbox[2]! as { wire_item: string }, wire = JSON.parse(row.wire_item)
  wire.object.ciphertext = 'AA'; row.wire_item = JSON.stringify(wire)
  const before = snapshot()
  await expect(run()).rejects.toThrow()
  expect(snapshot()).toEqual(before)
})

it('retains only the proven prefix when Content dependencies fail', async () => {
  const { snapshot, run } = await setup({ change: event => { event.dependencies.metadata_event_id = crypto.randomUUID() } })
  await expect(run()).rejects.toThrow()
  const after = snapshot()
  expect(after.rows.map(row => row.state)).toEqual(['applied', 'note_proven', 'received'])
  expect(after.manifest!.applied_cursor).toBe(2)
  await expect(run()).rejects.toThrow()
  expect(snapshot()).toEqual(after)
})

it('recovers a lost Content commit response from genuine durable proofs', async () => {
  const { snapshot, run } = await setup()
  const original = BrowserContentNoteApplyRuntime.prototype.commit
  vi.spyOn(BrowserContentNoteApplyRuntime.prototype, 'commit').mockImplementationOnce(async function(this: BrowserContentNoteApplyRuntime, token) {
    await original.call(this, token)
    throw Error('isolated_lost_response')
  })
  await expect(run()).rejects.toThrow('isolated_lost_response')
  const applied = snapshot()
  expect(applied.manifest!.applied_cursor).toBe(3)
  expect(applied.rows[2]!.state).toBe('content_note_proven')
  expect(await run()).toMatchObject({ contentProofs: 1, projectOpened: false })
  expect(snapshot()).toEqual(applied)
})
