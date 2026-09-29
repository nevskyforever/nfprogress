// @vitest-environment node
import { beforeAll, describe, expect, it } from 'vitest'
import { generateAccountMasterKey, type AccountMasterKey } from '@/crypto'
import {
  decodeProjectMetadataEvent, encodeProjectMetadataEvent, frameProjectMetadata,
  openProjectMetadataEvent, sealProjectMetadataEvent, unframeProjectMetadata,
  type ProjectMetadataEvent,
} from './projectMetadataCodec'

const user = '123e4567-e89b-42d3-a456-426614174099'
const project = 'project-1'
const eventId = '123e4567-e89b-42d3-a456-426614174001'
const time = '2026-09-21T00:00:00.000000Z'
function event(): ProjectMetadataEvent {
  return {
    version: 1,
    header: { account_id: user, bootstrap_id: '123e4567-e89b-42d3-a456-426614174002',
      device_id: '123e4567-e89b-42d3-a456-426614174003', entity_id: project,
      event_id: eventId, generation: 1, operation: 'create', parent_event_ids: [],
      project_id: project, revision: 1, updated_at: time },
    metadata: { name: 'Private project name', goal: 1000, infinite: false, unit: 'symbols',
      deadline: null, status: 'активен', personal_goal: 100, auto_freeze: true,
      streak_enabled: true, work_method: 'manual', stages_enabled: false,
      combine_stage_mindmaps: false },
    deleted_at: null,
  }
}

describe('C18 metadata codec and isolated E2EE', () => {
  let amk: AccountMasterKey
  beforeAll(async () => { amk = await generateAccountMasterKey() })
  it('encodes deterministic canonical bytes and uncompressed framed round trip', () => {
    const a = event()
    const b = { ...a, metadata: { ...a.metadata! } }
    expect(encodeProjectMetadataEvent(a)).toEqual(encodeProjectMetadataEvent(b))
    expect(decodeProjectMetadataEvent(encodeProjectMetadataEvent(a))).toEqual(a)
    expect(unframeProjectMetadata(frameProjectMetadata(a))).toEqual(a)
    const unsupported = frameProjectMetadata(a)
    unsupported[11] = 1
    expect(() => unframeProjectMetadata(unsupported)).toThrow('invalid_project_metadata')
  })
  it('rejects unknown fields, malformed types, invalid causal identity and tombstone', () => {
    expect(() => encodeProjectMetadataEvent({ ...event(), metadata: { ...event().metadata, secret: 'x' } } as ProjectMetadataEvent)).toThrow()
    expect(() => encodeProjectMetadataEvent({ ...event(), metadata: { ...event().metadata, goal: '100' } } as unknown as ProjectMetadataEvent)).toThrow()
    expect(() => encodeProjectMetadataEvent({ ...event(), header: { ...event().header, entity_id: 'other' } })).toThrow()
    const deletion: ProjectMetadataEvent = { ...event(), header: { ...event().header, operation: 'delete', revision: 2, generation: 2, parent_event_ids: [eventId], event_id: '123e4567-e89b-42d3-a456-426614174004' }, metadata: null, deleted_at: time }
    expect(decodeProjectMetadataEvent(encodeProjectMetadataEvent(deletion))).toEqual(deletion)
  })
  it('seals metadata without plaintext and authenticates every scope', async () => {
    const sealed = await sealProjectMetadataEvent(amk, event())
    expect(Buffer.from(sealed.ciphertext).includes(Buffer.from('Private project name'))).toBe(false)
    const scope = { account_id: user, project_id: project, entity_id: project, event_id: eventId }
    await expect(openProjectMetadataEvent(amk, scope, sealed)).resolves.toEqual(event())
    await expect(openProjectMetadataEvent(amk, { ...scope, account_id: 'other' }, sealed)).rejects.toThrow()
    await expect(openProjectMetadataEvent(amk, { ...scope, project_id: 'other' }, sealed)).rejects.toThrow()
    await expect(openProjectMetadataEvent(amk, { ...scope, entity_id: 'other' }, sealed)).rejects.toThrow()
    await expect(openProjectMetadataEvent(amk, { ...scope, event_id: 'other' }, sealed)).rejects.toThrow()
    const tampered = { ...sealed, ciphertext: new Uint8Array(sealed.ciphertext) }
    tampered.ciphertext[0]! ^= 1
    await expect(openProjectMetadataEvent(amk, scope, tampered)).rejects.toThrow()
  })
})
