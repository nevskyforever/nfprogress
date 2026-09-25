import { describe, expect, it } from 'vitest'
import fixture from './__fixtures__/noteSyncPlaintextV2Resolution.json'
import { decodeNoteSyncPlaintext, type NoteSyncRecord } from './noteSyncCodec'
import { canonicalNoteSyncResolutionV2Json, decodeNoteSyncResolutionV2, encodeNoteSyncResolutionV2, validateNoteSyncResolutionV2, type NoteSyncResolutionV2 } from './noteSyncResolutionV2Codec'

const encoder = new TextEncoder()

function example(index = 0): NoteSyncResolutionV2 {
  return structuredClone(fixture.examples[index]!.plaintext) as NoteSyncResolutionV2
}

describe('C17 Note resolution plaintext v2 codec', () => {
  it.each(fixture.examples.map((item, index) => [item.name, index, item.canonical_json]))('%s matches the shared canonical UTF-8 bytes', (_name, index, canonical) => {
    const value = example(index as number)
    validateNoteSyncResolutionV2(value)
    expect(canonicalNoteSyncResolutionV2Json(value)).toBe(canonical)
    expect([...encodeNoteSyncResolutionV2(value)]).toEqual([...encoder.encode(canonical)])
    expect(decodeNoteSyncResolutionV2(encoder.encode(canonical))).toEqual(value)
  })

  it('accepts structurally complete keep_both and delete variants', () => {
    const keep = example()
    const source = keep.result.note as NoteSyncRecord
    keep.resolution = {
      conflict_group_id: keep.resolution.conflict_group_id,
      conflict_generation: keep.resolution.conflict_generation,
      resolved_event_ids: keep.resolution.resolved_event_ids,
      strategy: 'keep_both',
      selected_event_id: keep.resolution.resolved_event_ids[0]!,
      retained_event_id: keep.resolution.resolved_event_ids[1]!,
      retained_note: { ...source, id: 'retained-note', created_at: '2026-09-25T10:00:00.000000Z', updated_at: '2026-09-25T10:00:00.000000Z' },
    }
    expect(decodeNoteSyncResolutionV2(encodeNoteSyncResolutionV2(keep))).toEqual(keep)

    const deleted = example()
    deleted.resolution = { conflict_group_id: deleted.resolution.conflict_group_id, conflict_generation: 1, resolved_event_ids: deleted.resolution.resolved_event_ids, strategy: 'delete' }
    deleted.result = { operation: 'delete', note: { id: deleted.header.entity_id, project_id: deleted.header.project_id, stage_id: null, source_type: 'project', source_map_id: null, source_node_id: null, content_format: 'html', deleted_at: '2026-09-25T10:00:00.000000Z' } }
    expect(decodeNoteSyncResolutionV2(encodeNoteSyncResolutionV2(deleted))).toEqual(deleted)
  })

  it('rejects malformed structure without claiming causal-history proof', () => {
    const cases: Array<(value: NoteSyncResolutionV2) => void> = [
      value => { (value as unknown as Record<string, unknown>).extra = true },
      value => { delete (value.result.note as unknown as Record<string, unknown>).title },
      value => { (value.result.note as unknown as Record<string, unknown>).extra = true },
      value => { value.header.additional_parent_event_ids = [value.header.parent_event_id] },
      value => { value.resolution.resolved_event_ids.reverse() },
      value => { value.header.parent_event_id = value.resolution.resolved_event_ids[1]! },
      value => { value.header.event_id = value.header.parent_event_id },
      value => { value.header.event_id = value.header.event_id.toUpperCase() },
      value => { value.header.updated_at = '2026-09-25T10:00:00Z' },
      value => { value.resolution = { conflict_group_id: value.resolution.conflict_group_id, conflict_generation: 1, resolved_event_ids: value.resolution.resolved_event_ids, strategy: 'manual_merge' }; value.result = { operation: 'delete', note: { id: value.header.entity_id, project_id: value.header.project_id, stage_id: null, source_type: 'project', source_map_id: null, source_node_id: null, content_format: 'html', deleted_at: '2026-09-25T10:00:00.000000Z' } } },
      value => { const source = value.result.note as NoteSyncRecord; value.resolution = { conflict_group_id: value.resolution.conflict_group_id, conflict_generation: 1, resolved_event_ids: value.resolution.resolved_event_ids, strategy: 'keep_both', selected_event_id: value.resolution.resolved_event_ids[0]!, retained_event_id: value.resolution.resolved_event_ids[1]!, retained_note: { ...source, id: value.header.entity_id } } },
      value => { const source = value.result.note as NoteSyncRecord; value.resolution = { conflict_group_id: value.resolution.conflict_group_id, conflict_generation: 1, resolved_event_ids: value.resolution.resolved_event_ids, strategy: 'keep_both', selected_event_id: value.resolution.resolved_event_ids[0]!, retained_event_id: value.resolution.resolved_event_ids[1]!, retained_note: { ...source, id: 'retained-note' } }; value.result = { operation: 'delete', note: { id: value.header.entity_id, project_id: value.header.project_id, stage_id: null, source_type: 'project', source_map_id: null, source_node_id: null, content_format: 'html', deleted_at: '2026-09-25T10:00:00.000000Z' } } },
    ]
    for (const mutate of cases) {
      const value = example(); mutate(value)
      expect(() => validateNoteSyncResolutionV2(value)).toThrow('Invalid Note resolution v2 payload.')
    }
  })

  it('keeps the v1 decoder fail-closed for v2 bytes', () => {
    expect(() => decodeNoteSyncPlaintext(encoder.encode(fixture.examples[0]!.canonical_json))).toThrow()
  })
})
