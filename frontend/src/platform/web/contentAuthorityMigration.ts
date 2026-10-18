import { BrowserPersistenceError } from './persistence'
import { validateBrowserInboxRecord, validateBrowserSyncCursor, validateBrowserUploadPair, immutableWireIdentity, type BrowserSyncScope } from './syncDurability'
import { validateBrowserProjectBinding } from './projectBindings'
import { validateLocalProjectRecord, validateLocalNoteRecord } from './localAuthorityRecords'
import { validateNoteHistorySet } from './noteHistoryRecords'
import { validateNoteIntent } from './noteIntentRecords'
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
/** Keyless v8 structural gate. No repair, crypto, HTTP or record writes. */
export function validateBrowserV8State(scopes: readonly BrowserSyncScope[], stores: unknown[][]): void {
  if (stores.length !== 10 || stores.some(s => !Array.isArray(s))) bad()
  unique([...scopes], s => s.accountId)
  for (const rows of stores) for (const v of rows) if (!scopes.some(s => s.accountId === account(v))) bad()
  for (const scope of scopes) {
    const [out, incoming, checkpoints, receipts, bindings, owners, projects, notes, retained, pending] = stores.map(rows => rows.filter(v => account(v) === scope.accountId)) as [unknown[], unknown[], unknown[], unknown[], unknown[], unknown[], unknown[], unknown[], unknown[], unknown[]]
    if (out.some(v => (v as any)?.record_version !== 1) || receipts.some(v => (v as any)?.record_version !== 1) || incoming.some(v => !Number.isInteger((v as any)?.record_version) || (v as any).record_version > 8) || retained.some(v => ![1, 2].includes((v as any)?.record_version)) || pending.some(v => (v as any)?.record_version !== 1)) bad()
    unique(out, r => r.event_id); unique(incoming, r => r.event_id); unique(incoming, r => r.server_sequence)
    unique(receipts, r => r.event_id); unique(receipts, r => r.server_sequence)
    unique(bindings, r => r.project_id); unique(bindings, r => r.bootstrap_id)
    unique(owners, r => [r.owner_kind, r.owner_id]); unique(projects, r => r.project_id); unique(notes, r => r.note_id)
    unique(pending, r => r.event_id); unique(pending, r => [r.project_id, r.note_id])
    const rows = incoming.map(v => validateBrowserInboxRecord(v, scope))
    const bs = bindings.map(v => validateBrowserProjectBinding(v, scope))
    const hs = validateNoteHistorySet(scope, retained)
    const intents = pending.map(v => validateNoteIntent(v, scope))
    const os = out.map(v => validateBrowserUploadPair(v, receipts.find(r => (r as any).event_id === (v as any).event_id), scope))
    for (const r of receipts) {
      const event = (r as any).event_id, seq = (r as any).server_sequence
      validateBrowserUploadPair(os.find(o => o.event_id === event), r, scope)
      if (rows.some(i => i.event_id === event && i.server_sequence !== seq || i.server_sequence === seq && i.event_id !== event)) bad()
    }
    if (checkpoints.length > 1) bad()
    const cursor = validateBrowserSyncCursor(checkpoints[0], scope)
    const allocation = [...os, ...intents].sort((a, b) => a.local_ordinal - b.local_ordinal)
    unique(allocation, r => r.event_id)
    if (allocation.some((r, i) => r.local_ordinal !== i + 1) || cursor.next_local_ordinal !== allocation.length + 1 || cursor.pull_cursor !== Math.max(0, ...rows.map(r => r.server_sequence))) bad()
    const ps = projects.map(p => validateLocalProjectRecord(p, scope))
    const ns = notes.map(v => validateLocalNoteRecord(v, scope, (v as any).project_id))
    for (const n of ns) if (!ps.some(p => p.project_id === n.project_id && n.source_revision <= p.source_revision)) bad()
    for (const i of intents) if (!bs.some(b => b.project_id === i.project_id && b.bootstrap_id === i.bootstrap_id) || !ns.some(n => same(n, i.snapshot)) || os.some(o => o.event_id === i.event_id)) bad()
    for (const h of hs) {
      if (!bs.some(b => b.project_id === h.project_id && b.bootstrap_id === h.bootstrap_id)) bad()
      if (h.record_kind !== 'candidate') continue
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
    for (const raw of owners) {
      const h = validateBrowserOwnerHead(raw, scope), project = h.owner_kind === 'project_metadata' ? h.owner_id : h.project_id
      if (!bs.some(b => b.project_id === project && b.bootstrap_id === h.bootstrap_id)) bad()
    }
    inspectBrowserAckInventory(scope, cursor, rows, owners, bs, hs)
    for (let seq = 1; seq <= cursor.proven_prefix; seq++) if (!rows.some(r => r.server_sequence === seq && r.state !== 'received')) bad()
    for (const r of rows) if (r.state === 'note_proven' && r.note_proof.outcome === 'self_echo_applied') {
      const o = os.find(o => o.event_id === r.event_id), receipt = receipts.find(p => (p as any).event_id === r.event_id) as any
      const c = hs.find(h => h.record_kind === 'candidate' && h.event_id === r.event_id)
      const w = JSON.parse(r!.wire_item), { device_id, server_sequence, ...event } = w.event
      if (!o || o.state !== 'accepted' || !receipt || receipt.server_sequence !== server_sequence || device_id !== scope.deviceId || !c || !same(JSON.parse(o.raw_body).items[0], { event, object: w.object })) bad()
    }
    for (const b of bs) if (b.mode === 'upload_existing' && ['captured', 'completing'].includes(b.phase)) deriveInitialLegacyCohort(scope, b, out, receipts)
  }
}
