import { describe, expect, it } from 'vitest'
import {
  MAX_NOTE_SYNC_PLAINTEXT_BYTES,
  canonicalNoteSyncJson,
  decodeNoteSyncPlaintext,
  encodeNoteSyncPlaintext,
  noteSyncEligibility,
  type NoteSyncPlaintext,
  type NoteSyncRecord,
} from './noteSyncCodec'

const timestamp = '2026-09-21T00:00:00.000000Z'
const eventId = '123e4567-e89b-42d3-a456-426614174000'

function note(overrides: Partial<NoteSyncRecord> = {}): NoteSyncRecord {
  return {
    id: 'note-1', project_id: 'project-1', stage_id: null, source_type: 'project', source_map_id: null,
    source_node_id: null, content_format: 'html', title: 'Title', content: '<p>Text</p>', checklist: [],
    color: 'default', pinned: false, archived: false, sort_order: 0, tags: [], created_at: timestamp,
    updated_at: timestamp, metadata: {}, ...overrides,
  }
}

function create(record = note()): Extract<NoteSyncPlaintext, { mutation: 'create' | 'update' }> {
  return {
    version: 1,
    header: { event_id: eventId, parent_event_id: null, project_id: 'project-1', entity_id: 'note-1', entity_type: 'note', operation: 'upsert', revision: 1, updated_at: timestamp, deleted_at: null },
    mutation: 'create', note: record,
  }
}

describe('C15 Note plaintext codec', () => {
  it('deterministically roundtrips create, update, and delete shapes', () => {
    const created = create(note({ metadata: { z: 1, a: { y: true, x: null } } }))
    const updated: NoteSyncPlaintext = { ...created, header: { ...created.header, revision: 2, parent_event_id: '123e4567-e89b-42d3-a456-426614174001' }, mutation: 'update' }
    const deleted: NoteSyncPlaintext = {
      version: 1,
      header: { ...updated.header, event_id: '123e4567-e89b-42d3-a456-426614174002', operation: 'delete', revision: 3, deleted_at: timestamp },
      mutation: 'delete', note: { id: 'note-1', project_id: 'project-1', stage_id: null, source_type: 'project', source_map_id: null, source_node_id: null, content_format: 'html', deleted_at: timestamp },
    }
    for (const payload of [created, updated, deleted]) {
      const encoded = encodeNoteSyncPlaintext(payload)
      expect(decodeNoteSyncPlaintext(encoded)).toEqual(payload)
      expect(new TextDecoder().decode(encoded)).toBe(canonicalNoteSyncJson(payload))
    }
  })

  it('keeps stage and mind-map shapes parseable but deferred', () => {
    const stage = create(note({ stage_id: 'stage-1' }))
    const mindMap = create(note({ source_type: 'mindmap', source_map_id: 'map-1', source_node_id: 'node-1' }))
    expect(decodeNoteSyncPlaintext(encodeNoteSyncPlaintext(stage))).toEqual(stage)
    expect(decodeNoteSyncPlaintext(encodeNoteSyncPlaintext(mindMap))).toEqual(mindMap)
    expect(noteSyncEligibility(stage)).toEqual({ eligible: false, error: 'dependency_not_synced' })
    expect(noteSyncEligibility(mindMap)).toEqual({ eligible: false, error: 'dependency_not_synced' })
    expect(noteSyncEligibility(create())).toEqual({ eligible: true })
    expect(noteSyncEligibility(create(note({ content_format: 'plain' })))).toEqual({ eligible: false, error: 'unsupported_content_format' })
  })

  it('enforces the exact canonical UTF-8 plaintext boundary without truncation', () => {
    const base = create(note({ content: '' }))
    const overhead = encodeNoteSyncPlaintext(base).byteLength
    const exact = create(note({ content: 'x'.repeat(MAX_NOTE_SYNC_PLAINTEXT_BYTES - overhead) }))
    expect(encodeNoteSyncPlaintext(exact)).toHaveLength(MAX_NOTE_SYNC_PLAINTEXT_BYTES)
    const oversized = create(note({ content: `${exact.note.content}x` }))
    expect(() => encodeNoteSyncPlaintext(oversized)).toThrowError(expect.objectContaining({ name: 'payload_too_large' }))
  })

  it('rejects malformed and noncanonical payload bytes', () => {
    expect(() => decodeNoteSyncPlaintext(new TextEncoder().encode('{"version":1}'))).toThrow()
    const canonical = canonicalNoteSyncJson(create())
    expect(() => decodeNoteSyncPlaintext(new TextEncoder().encode(` ${canonical}`))).toThrow()
  })
})
