import { BrowserPersistenceError } from './persistence'
import { validateBrowserInboxRecord, validateBrowserSyncCursor, validateBrowserStoredUploadPair, immutableWireIdentity, type BrowserSyncScope } from './syncDurability'
import { validateBrowserProjectBinding } from './projectBindings'
import { validateLocalProjectRecord, validateLocalNoteRecord } from './localAuthorityRecords'
import { validateNoteHistorySet } from './noteHistoryRecords'
import { validateNoteIntentRecord } from './noteIntentRecords'
import { inspectContentAuthorityInventory } from './contentAuthorityInventory'
import { validateBrowserOwnerHead } from './stageRecords'
import { inspectBrowserAckInventory } from './ackPrerequisites'
import { deriveInitialLegacyCohort } from './initialNoteCapture'

const bad = (): never => { throw new BrowserPersistenceError('corrupt_record') }
const same = (a: unknown, b: unknown) => immutableWireIdentity(a) === immutableWireIdentity(b)
const account = (v: unknown) => (v as { account_id?: string } | null)?.account_id
const unique = (rows: unknown[], key: (v: any) => unknown) => {
  const keys = rows.map(v => immutableWireIdentity(key(v)))
  if (new Set(keys).size !== keys.length) bad()
}
/** Keyless v9 structural gate. No repair, crypto, HTTP or record writes. */
export function validateBrowserV9State(scopes: readonly BrowserSyncScope[], stores: unknown[][]): void {
  if (stores.length !== 10 || stores.some(s => !Array.isArray(s))) bad()
  unique([...scopes], s => s.accountId)
  for (const rows of stores) for (const v of rows) if (!scopes.some(s => s.accountId === account(v))) bad()
  for (const scope of scopes) {
    const [out, incoming, checkpoints, receipts, bindings, owners, projects, notes, retained, pending] = stores.map(rows => rows.filter(v => account(v) === scope.accountId)) as [unknown[], unknown[], unknown[], unknown[], unknown[], unknown[], unknown[], unknown[], unknown[], unknown[]]
    // The current version-aware validators accept I2/C3/R2/inbox9, and reject future Resolution variants.
    unique(out, r => r.event_id); unique(incoming, r => r.event_id); unique(incoming, r => r.server_sequence)
    unique(receipts, r => r.event_id); unique(receipts, r => r.server_sequence)
    unique(bindings, r => r.project_id); unique(bindings, r => r.bootstrap_id)
    unique(owners, r => [r.owner_kind, r.owner_id]); unique(projects, r => r.project_id); unique(notes, r => r.note_id)
    unique(pending, r => r.event_id); unique(pending, r => [r.project_id, r.note_id])
    const rows = incoming.map(v => validateBrowserInboxRecord(v, scope))
    const bs = bindings.map(v => validateBrowserProjectBinding(v, scope))
    const hs = validateNoteHistorySet(scope, retained)
    const intents = pending.map(v => validateNoteIntentRecord(v, scope))
    const os = out.map(v => validateBrowserStoredUploadPair(v, receipts.find(r => (r as any).event_id === (v as any).event_id), scope))
    for (const r of receipts) {
      const event = (r as any).event_id, seq = (r as any).server_sequence
      validateBrowserStoredUploadPair(os.find(o => o.event_id === event), r, scope)
      if (rows.some(i => i.event_id === event && i.server_sequence !== seq || i.server_sequence === seq && i.event_id !== event)) bad()
    }
    if (checkpoints.length > 1) bad()
    const cursor = validateBrowserSyncCursor(checkpoints[0], scope)
    if (!checkpoints.length && (os.length || rows.length || intents.length)) bad()
    inspectContentAuthorityInventory(scope, {history: retained, intents: pending, out, receipts, rows: incoming, bindings, localNotes: notes, cursor})
    const allocation = [...os, ...intents].sort((a, b) => a.local_ordinal - b.local_ordinal)
    unique(allocation, r => r.event_id)
    if (allocation.some((r, i) => r.local_ordinal !== i + 1) || cursor.next_local_ordinal !== allocation.length + 1 || cursor.pull_cursor !== rows.reduce((max,r) => Math.max(max,r.server_sequence),0)) bad()
    const ps = projects.map(p => validateLocalProjectRecord(p, scope))
    const ns = notes.map(v => validateLocalNoteRecord(v, scope, (v as any).project_id))
    for (const n of ns) if (!ps.some(p => p.project_id === n.project_id && n.source_revision <= p.source_revision)) bad()
    for (const i of intents) if (!bs.some(b => b.project_id === i.project_id && b.bootstrap_id === i.bootstrap_id) || !ns.some(n => same(n, i.snapshot)) || os.some(o => o.event_id === i.event_id)) bad()
    for (const h of hs) {
      if (!bs.some(b => b.project_id === h.project_id && b.bootstrap_id === h.bootstrap_id)) bad()
      if (h.record_kind !== 'candidate') continue
      if (h.record_version === 3) continue // Authorship/receipt joins were checked by the v9 inventory dispatcher.
      const wire = JSON.parse(h.wire_item)
      if (h.origin === 'peer') {
        const r = rows.find(r => r.event_id === h.event_id)
        if (!r || r.protocol_version !== h.protocol_version || !(h.record_version === 2 ? ['content_note_proven', 'content_note_conflict_preserved'] : ['note_proven', 'note_conflict_preserved']).includes(r.state)) bad()
        const original = JSON.parse(r!.wire_item), { device_id, server_sequence: _seq, ...event } = original.event
        if (device_id !== h.source_device_id || !same(wire, h.record_version === 2 ? original : { event, object: original.object })) bad()
      } else {
        const o = os.find(o => o.event_id === h.event_id)
        if (!o || o.protocol_version !== h.protocol_version || !same(JSON.parse(o.raw_body).items[0], wire)) bad()
      }
    }
    const ownerHeads = owners.map(raw => validateBrowserOwnerHead(raw, scope))
    for (const h of ownerHeads) {
      const project = h.owner_kind === 'project_metadata' ? h.owner_id : h.project_id
      if (!bs.some(b => b.project_id === project && b.bootstrap_id === h.bootstrap_id)) bad()
    }
    for (const i of intents) if (i.parent_event_id !== null && !hs.some(h => h.record_kind === 'candidate' && h.project_id === i.project_id && h.note_id === i.note_id && h.bootstrap_id === i.bootstrap_id && h.event_id === i.parent_event_id && h.header.revision === i.revision-1)) bad()
    // Historical dependency witnesses may precede today's owner tip. Never rebase them.
    const contentIntents = [...intents.filter(i => i.record_version === 2), ...hs.flatMap(h => h.record_kind === 'candidate' && h.record_version === 3 ? [h.intent] : [])]
    for (const i of contentIntents) {
      if (i.record_version !== 2) bad()
      const metadata = ownerHeads.find(h => h.owner_kind === 'project_metadata' && h.owner_id === i.project_id && h.bootstrap_id === i.bootstrap_id)
      if (!metadata?.history.some(p => p.event_id === i.dependencies.metadata_event_id)) bad()
      for (const id of i.dependencies.stage_event_ids) if (!ownerHeads.some(h => h.owner_kind === 'stage' && h.project_id === i.project_id && h.bootstrap_id === i.bootstrap_id && h.history.some(p => p.event_id === id))) bad()
    }
    inspectBrowserAckInventory(scope, cursor, rows, owners, bs, hs)
    const proven = rows.filter(r => r.server_sequence <= cursor.proven_prefix).sort((a,b) => a.server_sequence-b.server_sequence)
    if (proven.length !== cursor.proven_prefix || proven.some((r,i) => r.server_sequence !== i+1 || r.state === 'received' || r.state === 'content_note_self_echo_proven')) bad()
    for (const r of rows) if (r.state === 'note_proven' && r.note_proof.outcome === 'self_echo_applied') {
      const o = os.find(o => o.event_id === r.event_id), receipt = receipts.find(p => (p as any).event_id === r.event_id) as any
      const c = hs.find(h => h.record_kind === 'candidate' && h.event_id === r.event_id)
      const w = JSON.parse(r!.wire_item), { device_id, server_sequence, ...event } = w.event
      if (!o || o.state !== 'accepted' || !receipt || receipt.server_sequence !== server_sequence || device_id !== scope.deviceId || !c || !same(JSON.parse(o.raw_body).items[0], { event, object: w.object })) bad()
    }
    for (const b of bs) if (b.mode === 'upload_existing' && ['captured', 'completing'].includes(b.phase)) deriveInitialLegacyCohort(scope, b, out, receipts)
  }
}
