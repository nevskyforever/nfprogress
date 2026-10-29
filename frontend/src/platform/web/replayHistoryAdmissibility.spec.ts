// @vitest-environment node
import { expect, it } from 'vitest'
import { assertReplayHistoryAdmissible } from './replayMetadata'
import { routeSetup, contentRow } from './noteTransport.testFixture'
import { received } from './legacyNoteApply.testFixture'
import { scope, amk } from './bootstrap.testFixture'
import type { ReplaySnapshot } from './replayInventory'

async function history(options: Parameters<typeof contentRow>[2] = {}) {
  const f = await routeSetup()
  const root = await received(f, 2, 1, null, 'upsert', p => { p.note.metadata = {} }, 'content-note')
  const wire = JSON.parse(root.wire_item)
  wire.event.device_id = f.m.event.header.device_id
  root.wire_item = JSON.stringify(wire)
  await contentRow(f, 3, { mutation: 'update', parent: root.event_id, ...options })
  const h = f.m.event.header
  const snapshot = {
    manifest: { phase: 'received', anchor: { registry: { current_cursor: 3, projects: [{ project_id: 'p',
      origin_device_id: h.device_id }] } }, source_seeds: [{ project_id: 'p', initial_max_server_sequence: 2 }] },
    rows: f.db.inbox,
  } as unknown as ReplaySnapshot
  return { snapshot, root }
}

it('admits one terminal genuine Content update without committing any proof', async () => {
  const { snapshot } = await history()
  const before = structuredClone(snapshot)
  await assertReplayHistoryAdmissible(snapshot, scope, true, true, amk)
  expect(snapshot).toEqual(before)
  await expect(assertReplayHistoryAdmissible(snapshot, scope, true, true)).rejects.toThrow()
})

it.each(['parent', 'revision', 'self', 'without_legacy', 'after_content', 'unsupported_prefix'] as const)(
  'rejects %s while retaining the original inventory', async kind => {
    const { snapshot } = await history(kind === 'parent' ? { parent: crypto.randomUUID() }
      : kind === 'revision' ? { revision: 4 } : {})
    if (kind === 'self') {
      const wire = JSON.parse(snapshot.rows[2]!.wire_item); wire.event.device_id = scope.deviceId
      snapshot.rows[2]!.wire_item = JSON.stringify(wire)
    }
    if (kind === 'without_legacy') snapshot.rows[1]!.wire_item = snapshot.rows[0]!.wire_item
    if (kind === 'after_content') {
      snapshot.rows.push(structuredClone(snapshot.rows[0]!))
      snapshot.manifest!.anchor.registry.current_cursor = 4
    }
    if (kind === 'unsupported_prefix') {
      const wire = JSON.parse(snapshot.rows[0]!.wire_item); wire.event.entity_type = 'map'
      snapshot.rows[0]!.wire_item = JSON.stringify(wire)
    }
    const before = structuredClone(snapshot)
    await expect(assertReplayHistoryAdmissible(snapshot, scope, true, true, amk)).rejects.toThrow()
    expect(snapshot).toEqual(before)
  },
)
