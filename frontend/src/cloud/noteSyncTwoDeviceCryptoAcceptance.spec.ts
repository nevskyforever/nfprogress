// @vitest-environment node
import { beforeAll, describe, expect, it } from 'vitest'
import { generateAccountMasterKey, type AccountMasterKey } from '@/crypto'
import type { SyncEventEnvelope } from './syncProtocol'
import { openNoteSyncEvent, sealNoteSyncEvent } from './encryptedSyncProtocol'
import type { NoteSyncRecord, NoteSyncTombstone } from './noteSyncCodec'

const USER = '123e4567-e89b-42d3-a456-426614174099'
const PROJECT = 'project-1'
const NOTE = 'note-1'
const CREATED = '2026-09-21T00:00:00.000000Z'
const UPDATED = '2026-09-21T01:00:00.000000Z'
const DELETED = '2026-09-21T02:00:00.000000Z'
const CREATE_EVENT = '123e4567-e89b-42d3-a456-426614174001'
const UPDATE_EVENT = '123e4567-e89b-42d3-a456-426614174002'
const DELETE_EVENT = '123e4567-e89b-42d3-a456-426614174003'

function event(
  eventId: string,
  revision: number,
  updatedAt: string,
  operation: 'upsert' | 'delete' = 'upsert',
): SyncEventEnvelope {
  return {
    event_id: eventId,
    project_id: PROJECT,
    entity_id: NOTE,
    entity_type: 'note',
    operation,
    revision,
    updated_at: updatedAt,
    deleted_at: operation === 'delete' ? updatedAt : null,
  }
}

function note(title: string, content: string, updatedAt: string): NoteSyncRecord {
  return {
    id: NOTE,
    project_id: PROJECT,
    stage_id: null,
    source_type: 'project',
    source_map_id: null,
    source_node_id: null,
    content_format: 'html',
    title,
    content,
    checklist: [],
    color: 'default',
    pinned: false,
    archived: false,
    sort_order: 0,
    tags: [],
    created_at: CREATED,
    updated_at: updatedAt,
    metadata: {},
  }
}

function tombstone(): NoteSyncTombstone {
  return {
    id: NOTE,
    project_id: PROJECT,
    stage_id: null,
    source_type: 'project',
    source_map_id: null,
    source_node_id: null,
    content_format: 'html',
    deleted_at: DELETED,
  }
}

describe('C15 two-device production crypto boundary', () => {
  let amk: AccountMasterKey

  beforeAll(async () => { amk = await generateAccountMasterKey() })

  it('opens create, update, and tombstone envelopes on the peer using one account AMK', async () => {
    const create = await sealNoteSyncEvent(
      amk, USER, event(CREATE_EVENT, 1, CREATED), null,
      note('private create', '<p>private body A</p>', CREATED),
    )
    const update = await sealNoteSyncEvent(
      amk, USER, event(UPDATE_EVENT, 2, UPDATED), CREATE_EVENT,
      note('private update', '<p>private body B</p>', UPDATED),
    )
    const deletion = await sealNoteSyncEvent(
      amk, USER, event(DELETE_EVENT, 3, DELETED, 'delete'), UPDATE_EVENT, tombstone(),
    )

    await expect(openNoteSyncEvent(amk, USER, create.event, create.object)).resolves.toMatchObject({
      mutation: 'create', note: { title: 'private create' },
    })
    await expect(openNoteSyncEvent(amk, USER, update.event, update.object)).resolves.toMatchObject({
      mutation: 'update', header: { parent_event_id: CREATE_EVENT }, note: { title: 'private update' },
    })
    await expect(openNoteSyncEvent(amk, USER, deletion.event, deletion.object)).resolves.toMatchObject({
      mutation: 'delete', header: { parent_event_id: UPDATE_EVENT }, note: { deleted_at: DELETED },
    })

    expect(new Set([create.object.nonce, update.object.nonce, deletion.object.nonce]
      .map(value => Buffer.from(value).toString('hex'))).size).toBe(3)
    const wireBytes = Buffer.concat([create.object.ciphertext, update.object.ciphertext, deletion.object.ciphertext])
    expect(wireBytes.includes(Buffer.from('private body'))).toBe(false)
  })

  it('keeps an immutable retry decryptable and rejects a different account context', async () => {
    const sealed = await sealNoteSyncEvent(
      amk, USER, event(CREATE_EVENT, 1, CREATED), null,
      note('retry title', '<p>retry body</p>', CREATED),
    )
    const retry = {
      event: { ...sealed.event },
      object: {
        ...sealed.object,
        nonce: Uint8Array.from(sealed.object.nonce),
        ciphertext: Uint8Array.from(sealed.object.ciphertext),
      },
    }

    expect(retry).toEqual(sealed)
    await expect(openNoteSyncEvent(amk, USER, retry.event, retry.object)).resolves.toMatchObject({
      mutation: 'create', note: { title: 'retry title' },
    })
    await expect(openNoteSyncEvent(amk, 'different-user', retry.event, retry.object)).rejects.toMatchObject({
      code: 'decrypt_failed',
    })
  })
})
