import type { BrowserNoteIntentRuntime, NoteMutationPlan } from './noteIntents'
import { verifiedLegacyNoteForLocal, verifiedNoteRouteForLocal, type VerifiedLegacyNotePlan } from './legacyNoteApply'
import type { AuthoritativeAccountBinding } from '@/auth/accountBinding'
import type { AuthoritativeKeyContextLease, RuntimeKeyContext } from '@/auth/keyContext'
import type { NormalUserAuthRuntime } from '@/auth/userAuth'
import { decryptObjectBytes, encryptObjectBytes, type AccountMasterKey } from '@/crypto'
import { decodeBase64Url, encodeBase64Url } from '@/api/base64url'
import { canonical, timestamp } from '@/cloud/projectMetadataCodec'
import { BrowserPersistenceError } from './persistence'
import { immutableWireIdentity, snapshotBrowserSyncScope, type BrowserSyncScope, type BrowserSyncTransaction } from './syncDurability'
import { localCanonicalBytes, localExact, localFailure as fail, localId, localSafe, MAX_LOCAL_NOTES, validateContentLocalNote, validatePersistedLocalNote, validateLocalNote, validateLocalNoteRecord, validateLocalProject, validateLocalProjectRecord, type LocalEnvelope, type LocalNotePayload, type LocalNoteRecord, type LocalNoteSource, type LocalProjectPayload, type LocalProjectRecord, type NativeLegacyNote, type NativeLocalProject } from './localAuthorityRecords'
import type { ProjectNotePatch } from '@/types/notes'

export interface LocalSourceToken { readonly verifiedLocalSource: unique symbol }
export interface LocalSourceSnapshot {
  record_version: 1; account_id: string; project_id: string; source_revision: number
  project: LocalProjectRecord; notes: readonly LocalNoteRecord[]; token: LocalSourceToken
}
interface SourceProof { owner: BrowserLocalAuthority; scope: BrowserSyncScope; project: LocalProjectRecord; notes: LocalNoteRecord[]; current: () => boolean }
interface Guard { lease: AuthoritativeKeyContextLease; current: () => boolean }
interface Opened { project: LocalProjectPayload; notes: LocalNoteSource[] }
const proofs = new WeakMap<object, SourceProof>()
const same = (a: unknown, b: unknown) => immutableWireIdentity(a) === immutableWireIdentity(b)
const noteRange = (s: BrowserSyncScope, p: string) => IDBKeyRange.bound([s.accountId, p], [s.accountId, p, []])
const order = (a: string, b: string) => a < b ? -1 : a > b ? 1 : 0
function freeze<T>(value: T): T {
  if (value && typeof value === 'object') { Object.values(value).forEach(freeze); Object.freeze(value) }
  return value
}
function proof(scope: BrowserSyncScope, token: LocalSourceToken): SourceProof {
  const p = token && proofs.get(token)
  if (!p || !same(p.scope, scope)) fail('stale_source')
  if (!p.current()) fail('closed')
  return p
}

/** Future capture infrastructure: synchronous requests in its SAME source+outbox transaction. No raw put API. */
export function assertLocalSourceInTransaction(tx: IDBTransaction, scope: BrowserSyncScope, token: LocalSourceToken, ready: () => void, abort: (error: unknown) => void): void {
  try {
    const p = proof(scope, token)
    const project = tx.objectStore('localProjects').get([scope.accountId, p.project.project_id])
    const notes = tx.objectStore('localNotes').getAll(noteRange(scope, p.project.project_id))
    let count = 0
    const finish = () => {
      if (++count !== 2) return
      try {
        if (!p.current()) fail('closed')
        const current = validateLocalProjectRecord(project.result, scope)
        const rows = notes.result.map(value => validateLocalNoteRecord(value, scope, p.project.project_id)).sort((a, b) => order(a.note_id, b.note_id))
        if (current.deleted) fail('deleted_local_source')
        if (current.source_revision !== p.project.source_revision || !same(current, p.project) || !same(rows, p.notes)) fail('stale_source')
        ready()
      } catch (error) { abort(error) }
    }
    project.onsuccess = finish; notes.onsuccess = finish
  } catch (error) { abort(error) }
}

export interface ProtectedNoteSourcePlan { readonly protectedNoteSource: unique symbol }
interface ProtectedChange {scope:BrowserSyncScope;source:LocalSourceToken;project:LocalProjectRecord;note:LocalNoteRecord;current:()=>boolean}
const protectedChanges=new WeakMap<object,ProtectedChange>()
/** Internal verified Note capability only; encrypted writes share the inbox-proof transaction. */
export function scheduleProtectedNoteApply(tx:IDBTransaction,scope:BrowserSyncScope,token:ProtectedNoteSourcePlan,ready:()=>void,abort:(e:unknown)=>void):void {
  const p=protectedChanges.get(token)
  if(!p||!same(p.scope,scope)||!p.current()){abort(new BrowserPersistenceError('stale_source'));return}
  assertLocalSourceInTransaction(tx,scope,p.source,()=>{
    const identity=tx.objectStore('localNotes').index('identity').get([scope.accountId,p.note.note_id])
    identity.onsuccess=()=>{try{if(!p.current())fail('closed');if(identity.result&&validateLocalNoteRecord(identity.result,scope,identity.result.project_id).project_id!==p.project.project_id)fail('conflicting_record')
      const writes=[tx.objectStore('localProjects').put(p.project),tx.objectStore('localNotes').put(p.note)]
      writes.forEach(r=>r.onsuccess=()=>{if(!p.current())abort(new BrowserPersistenceError('closed'))});ready()
    }catch(e){abort(e)}}
  },abort)
}

/** Dormant entry point. No UI/HTTP fallback; mutation runtime requires existing normal-user key context. */
export class BrowserLocalAuthority {
  constructor(private readonly transaction: BrowserSyncTransaction) {}
  bind(auth: NormalUserAuthRuntime, bindings: AuthoritativeAccountBinding, keys: RuntimeKeyContext): BrowserLocalAuthorityRuntime {
    return new BrowserLocalAuthorityRuntime(this, this.transaction, auth, bindings, keys)
  }
}
export class BrowserLocalAuthorityRuntime {
  constructor(private readonly owner: BrowserLocalAuthority, private readonly transaction: BrowserSyncTransaction, private readonly auth: NormalUserAuthRuntime, private readonly bindings: AuthoritativeAccountBinding, private readonly keys: RuntimeKeyContext, private readonly writer?: BrowserNoteIntentRuntime) {}
  /** Internal dormant writer binding; ordinary local-only runtime remains unchanged. */
  withNoteWriter(writer: BrowserNoteIntentRuntime): BrowserLocalAuthorityRuntime { return new BrowserLocalAuthorityRuntime(this.owner,this.transaction,this.auth,this.bindings,this.keys,writer) }
  private async guard(scope: BrowserSyncScope): Promise<Guard> {
    const { context } = await this.bindings.ensureForCurrentUser(scope.accountId)
    const lease = this.keys.leaseForAccount(scope.accountId)
    const current = () => this.auth.isCurrent(context) && !!lease?.isCurrent()
    if (!lease || context.userId !== scope.canonicalUserId || lease.localAccountId !== scope.accountId || lease.canonicalUserId !== context.userId || lease.authEpoch !== context.authEpoch || !current()) throw new BrowserPersistenceError('account_mismatch')
    return { lease, current }
  }
  private token(scope: BrowserSyncScope, token: LocalSourceToken): SourceProof {
    const p = proof(scope, token)
    if (p.owner !== this.owner) fail('stale_source')
    return p
  }
  private load(scope: BrowserSyncScope, id: string): Promise<{ project: LocalProjectRecord; notes: LocalNoteRecord[] }> {
    return this.transaction(scope, ['localProjects','localNotes'], 'readonly', (tx, result, abort) => {
      const project = tx.objectStore('localProjects').get([scope.accountId, id]), notes = tx.objectStore('localNotes').getAll(noteRange(scope, id))
      let count = 0
      const finish = () => { if (++count !== 2) return; try {
        if (!project.result) fail(notes.result.length ? 'corrupt_record' : 'missing_local_source')
        const p = validateLocalProjectRecord(project.result, scope)
        if (p.deleted) fail('deleted_local_source')
        if (notes.result.length > MAX_LOCAL_NOTES) fail('source_limit')
        result({ project: p, notes: notes.result.map(value => validateLocalNoteRecord(value, scope, id)).sort((a, b) => order(a.note_id, b.note_id)) })
      } catch (error) { abort(error) } }
      project.onsuccess = finish; notes.onsuccess = finish
    })
  }
  private async seal(scope: BrowserSyncScope, id: string, kind: 'project' | 'note', payload: LocalProjectPayload | LocalNotePayload, amk: AccountMasterKey): Promise<LocalEnvelope> {
    const bytes = localCanonicalBytes(payload)
    let nonce: Uint8Array | undefined, ciphertext: Uint8Array | undefined
    try {
      const e = await encryptObjectBytes(amk, { userId: scope.canonicalUserId, projectId: payload.project_id, entityId: id, entityType: kind === 'project' ? 'project_metadata' : 'note' }, bytes)
      nonce = e.nonce; ciphertext = e.ciphertext
      return { crypto_version: 1, aad_version: 1, nonce: encodeBase64Url(nonce), ciphertext: encodeBase64Url(ciphertext) }
    } finally { bytes.fill(0); nonce?.fill(0); ciphertext?.fill(0) }
  }
  private async decode(scope: BrowserSyncScope, row: LocalProjectRecord | LocalNoteRecord, kind: 'project' | 'note', amk: AccountMasterKey): Promise<unknown> {
    let nonce: Uint8Array | undefined, ciphertext: Uint8Array | undefined, bytes: Uint8Array | undefined
    try {
      nonce = decodeBase64Url(row.envelope.nonce); ciphertext = decodeBase64Url(row.envelope.ciphertext)
      bytes = await decryptObjectBytes(amk, { userId: scope.canonicalUserId, projectId: row.project_id, entityId: 'note_id' in row ? row.note_id : row.project_id, entityType: kind === 'project' ? 'project_metadata' : 'note' }, { crypto_version: 1, aad_version: 1, nonce, ciphertext })
      const raw = new TextDecoder('utf-8', { fatal: true }).decode(bytes), value: unknown = JSON.parse(raw)
      if (canonical(value) !== raw) fail('corrupt_record')
      return value
    } catch { fail('corrupt_record') }
    finally { bytes?.fill(0); nonce?.fill(0); ciphertext?.fill(0) }
  }
  private async open(scope: BrowserSyncScope, p: LocalProjectRecord, rows: readonly LocalNoteRecord[], amk: AccountMasterKey): Promise<Opened> {
    const value = await this.decode(scope, p, 'project', amk)
    if (!localExact(value, ['local_format','kind','account_id','device_id','project_id','source_revision','deleted_at','project','member_ids'])) fail('corrupt_record')
    const project = value as unknown as LocalProjectPayload
    if (project.local_format !== 1 || project.kind !== 'project' || project.account_id !== scope.accountId || project.device_id !== scope.deviceId || project.project_id !== p.project_id || project.source_revision !== p.source_revision || project.deleted_at !== null || !Array.isArray(project.member_ids)
      || !same(project.member_ids, rows.map(r => r.note_id))) fail('corrupt_record')
    project.project = validateLocalProject(project.project)
    if (project.project.id !== p.project_id) fail('corrupt_record')
    const notes: LocalNoteSource[] = []
    for (const row of rows) {
      const raw = await this.decode(scope, row, 'note', amk)
      if (!localExact(raw, ['local_format','kind','account_id','device_id','project_id','note_id','source_revision','source'])) fail('corrupt_record')
      const note = raw as unknown as LocalNotePayload
      if (note.local_format !== 1 || note.kind !== 'note' || note.account_id !== scope.accountId || note.device_id !== scope.deviceId || note.project_id !== p.project_id || note.note_id !== row.note_id || note.source_revision !== row.source_revision || row.source_revision > p.source_revision) fail('corrupt_record')
      const source = validatePersistedLocalNote(note.source, p.project_id)
      if (source.note.id !== row.note_id || (source.state === 'tombstone') !== row.deleted || (source.state === 'live' ? source.note.revision : source.revision) !== row.note_revision) fail('corrupt_record')
      notes.push(source)
    }
    return { project, notes }
  }
  async readSnapshot(scope: BrowserSyncScope, projectId: string): Promise<LocalSourceSnapshot> {
    scope = snapshotBrowserSyncScope(scope); localId(projectId)
    const guard = await this.guard(scope), stored = await this.load(scope, projectId)
    await guard.lease.use(async amk => { await this.open(scope, stored.project, stored.notes, amk) })
    if (!guard.current()) fail('closed')
    const token = Object.freeze({}) as LocalSourceToken
    proofs.set(token, { owner: this.owner, scope, project: structuredClone(stored.project), notes: structuredClone(stored.notes), current: guard.current })
    return freeze({ record_version: 1, account_id: scope.accountId, project_id: projectId, source_revision: stored.project.source_revision, ...stored, token })
  }
  async withDecryptedSnapshot<T>(scope: BrowserSyncScope, token: LocalSourceToken, consume: (source: { project: NativeLocalProject; notes: readonly LocalNoteSource[]; source_revision: number }) => Promise<T>): Promise<T> {
    scope = snapshotBrowserSyncScope(scope)
    const p = this.token(scope, token), guard = await this.guard(scope)
    return guard.lease.use(async amk => {
      const source = await this.open(scope, p.project, p.notes, amk)
      if (!guard.current() || !p.current()) fail('closed')
      const result = await consume(freeze({ project: source.project.project, notes: source.notes, source_revision: p.project.source_revision }))
      if (!guard.current() || !p.current()) fail('closed')
      return result
    })
  }
  async assertSnapshot(scope: BrowserSyncScope, token: LocalSourceToken): Promise<void> {
    scope = snapshotBrowserSyncScope(scope); this.token(scope, token)
    await this.transaction<void>(scope, ['localProjects','localNotes'], 'readonly', (tx, result, abort) => assertLocalSourceInTransaction(tx, scope, token, () => result(undefined), abort))
  }
  initializeProject(scope: BrowserSyncScope, input: { project: NativeLocalProject; notes: readonly LocalNoteSource[] }): Promise<number> {
    return this.initialize(scope, input, true)
  }
  private async initialize(scope: BrowserSyncScope, input: { project: NativeLocalProject; notes: readonly LocalNoteSource[] }, retry: boolean): Promise<number> {
    scope = snapshotBrowserSyncScope(scope)
    if (!localExact(input, ['project','notes']) || !Array.isArray(input.notes) || input.notes.length > MAX_LOCAL_NOTES) fail()
    const project = validateLocalProject(input.project), sources = input.notes.map(n => validateLocalNote(n, project.id)).sort((a, b) => order(a.note.id, b.note.id))
    if (sources.some((n, i) => i > 0 && sources[i - 1]!.note.id === n.note.id)) fail('conflicting_record')
    if (retry) {
      let prior: LocalSourceSnapshot | undefined
      try { prior = await this.readSnapshot(scope, project.id) } catch (e) { if (!(e instanceof BrowserPersistenceError) || e.code !== 'missing_local_source') throw e }
      if (prior) {
        const matches = await this.withDecryptedSnapshot(scope, prior.token, async source => source.source_revision === 1 && same(source.project, project) && same(source.notes, sources))
        if (!matches) fail('conflicting_record')
        await this.assertSnapshot(scope, prior.token)
        return 1
      }
    }
    const guard = await this.guard(scope)
    return guard.lease.use(async amk => {
      const payload: LocalProjectPayload = { local_format: 1, kind: 'project', account_id: scope.accountId, device_id: scope.deviceId, project_id: project.id, source_revision: 1, deleted_at: null, project, member_ids: sources.map(n => n.note.id) }
      const p: LocalProjectRecord = { record_version: 1, account_id: scope.accountId, device_id: scope.deviceId, project_id: project.id, source_revision: 1, deleted: false, envelope: await this.seal(scope, project.id, 'project', payload, amk) }
      const notes: LocalNoteRecord[] = []
      for (const source of sources) notes.push(await this.noteRow(scope, source, 1, amk))
      return this.write(scope, guard, null, p, notes)
    })
  }
  createProject(scope: BrowserSyncScope, project: NativeLocalProject): Promise<number> { return this.initialize(scope, { project, notes: [] }, false) }
  private async noteRow(scope: BrowserSyncScope, source: LocalNoteSource, revision: number, amk: AccountMasterKey): Promise<LocalNoteRecord> {
    return { record_version: 1, account_id: scope.accountId, device_id: scope.deviceId, project_id: source.note.project_id, note_id: source.note.id, source_revision: revision, note_revision: source.state === 'live' ? source.note.revision : source.revision, deleted: source.state === 'tombstone', envelope: await this.seal(scope, source.note.id, 'note', { local_format: 1, kind: 'note', account_id: scope.accountId, device_id: scope.deviceId, project_id: source.note.project_id, note_id: source.note.id, source_revision: revision, source }, amk) }
  }
  private write(scope: BrowserSyncScope, guard: Guard, expected: LocalSourceToken | null, project: LocalProjectRecord, notes: LocalNoteRecord[], deletion = false, mutation?: NoteMutationPlan): Promise<number> {
    if (!guard.current()) fail('closed')
    let unsubscribe: (() => void) | undefined
    return this.transaction<number>(scope, ['localProjects','localNotes', ...(deletion ? ['projectBindings'] : []), ...(mutation ? this.writer!.mutationStores : [])], 'readwrite', (tx, result, abort) => {
      unsubscribe = this.auth.onInvalidated(() => abort(new BrowserPersistenceError('closed')))
      const commit = () => {
        const reads = notes.map(note => tx.objectStore('localNotes').index('identity').get([scope.accountId, note.note_id]))
        const binding = deletion ? tx.objectStore('projectBindings').get([scope.accountId, project.project_id]) : null
        const requests = [...reads, ...(binding ? [binding] : [])]
        let ready = 0
        const finish = () => { if (++ready < requests.length) return; try {
          if (!guard.current()) fail('closed')
          if (binding?.result) fail('unsupported_local_source') // No cloud deletion/bootstrap semantics here.
          reads.forEach(read => { if (read.result) { const existing = validateLocalNoteRecord(read.result, scope, read.result.project_id); if (existing.project_id !== project.project_id) fail('conflicting_record') } })
          const persist = () => {
          const writes = [tx.objectStore('localProjects').put(project), ...notes.map(n => tx.objectStore('localNotes')[expected ? 'put' : 'add'](n))]
          writes.forEach(write => { write.onsuccess = () => { if (!guard.current()) abort(new BrowserPersistenceError('closed')) } })
          result(project.source_revision)
          }
          if(mutation)this.writer!.scheduleMutation(tx,mutation,persist,abort);else persist()
        } catch (error) { abort(error) } }
        if (!requests.length) finish(); else requests.forEach(read => { read.onsuccess = finish })
      }
      if (expected) assertLocalSourceInTransaction(tx, scope, expected, commit, abort)
      else {
        const p = tx.objectStore('localProjects').get([scope.accountId, project.project_id]), members = tx.objectStore('localNotes').count(noteRange(scope, project.project_id))
        let count = 0
        const finish = () => { if (++count !== 2) return; try { if (p.result || members.result) fail('conflicting_record'); commit() } catch (e) { abort(e) } }
        p.onsuccess = finish; members.onsuccess = finish
      }
    }).finally(() => unsubscribe?.())
  }
  private async mutate(scope: BrowserSyncScope, token: LocalSourceToken, action: (opened: Opened) => LocalNoteSource[] | void, deletedAt: string | null = null): Promise<number> {
    scope = snapshotBrowserSyncScope(scope)
    const p = this.token(scope, token), guard = await this.guard(scope)
    if (p.project.source_revision === Number.MAX_SAFE_INTEGER) fail('source_limit')
    return guard.lease.use(async amk => {
      const opened = await this.open(scope, p.project, p.notes, amk)
      if(this.writer&&opened.project.project.status==='завершен')fail('unsupported_local_source') // Native direct Note writer keeps completed projects readonly.
      const changed = action(opened) ?? []
      const revision = p.project.source_revision + 1
      opened.project.source_revision = revision; opened.project.deleted_at = deletedAt
      opened.project.member_ids = opened.notes.map(n => n.note.id).sort(order)
      if (opened.project.member_ids.length > MAX_LOCAL_NOTES) fail('source_limit')
      const row: LocalProjectRecord = { ...p.project, source_revision: revision, deleted: deletedAt !== null, envelope: await this.seal(scope, p.project.project_id, 'project', opened.project, amk) }
      const notes: LocalNoteRecord[] = []
      for (const source of changed) notes.push(await this.noteRow(scope, source, revision, amk))
      const mutation=this.writer ? await this.writer.prepareMutation(scope,notes,amk) : undefined
      return this.write(scope, guard, token, row, notes, deletedAt !== null, mutation)
    })
  }
  async prepareProtectedNoteApply(scope:BrowserSyncScope,token:LocalSourceToken,verified:VerifiedLegacyNotePlan):Promise<{token:ProtectedNoteSourcePlan;source_revision:number;note:LocalNoteRecord}> {
    scope=snapshotBrowserSyncScope(scope);const incoming=verifiedLegacyNoteForLocal(verified,this,scope),p=this.token(scope,token),guard=await this.guard(scope)
    if(p.project.source_revision===Number.MAX_SAFE_INTEGER)fail('source_limit')
    return guard.lease.use(async amk=>{
      const opened=await this.open(scope,p.project,p.notes,amk),revision=p.project.source_revision+1
      // Native peer payload has local mutation revision0; sync revision stays in Note proof.
      const admit=verifiedNoteRouteForLocal(verified,this,scope)==='content_note_v1'?validateContentLocalNote:validateLocalNote
      const source=admit(incoming.mutation==='delete'?{state:'tombstone',note:incoming.note,revision:0}:{state:'live',note:{...incoming.note,revision:0}},p.project.project_id)
      const old=opened.notes.findIndex(n=>n.note.id===source.note.id)
      if(old<0)opened.notes.push(source);else opened.notes[old]=source
      if(opened.notes.length>MAX_LOCAL_NOTES)fail('source_limit')
      opened.project.source_revision=revision;opened.project.member_ids=opened.notes.map(n=>n.note.id).sort(order)
      const project:LocalProjectRecord={...p.project,source_revision:revision,envelope:await this.seal(scope,p.project.project_id,'project',opened.project,amk)},note=await this.noteRow(scope,source,revision,amk)
      if(!guard.current())fail('closed');const plan=Object.freeze({}) as ProtectedNoteSourcePlan
      protectedChanges.set(plan,{scope,source:token,project,note,current:guard.current});return{token:plan,source_revision:revision,note}
    })
  }
  createNote(scope: BrowserSyncScope, token: LocalSourceToken, input: NativeLegacyNote): Promise<number> {
    const source = validateLocalNote({ state: 'live', note: input }, input.project_id)
    if (source.state !== 'live' || source.note.revision !== 0) fail()
    return this.mutate(scope, token, opened => { if (source.note.project_id !== opened.project.project_id || opened.notes.some(n => n.note.id === source.note.id)) fail('conflicting_record'); opened.notes.push(source); return [source] })
  }
  updateNote(scope: BrowserSyncScope, token: LocalSourceToken, id: string, patch: ProjectNotePatch, updatedAt: string): Promise<number> {
    localId(id)
    if (!timestamp(updatedAt) || !patch || typeof patch !== 'object' || Array.isArray(patch) || Object.keys(patch).some(k => !['title','content','tags','checklist','color','pinned','archived'].includes(k))) fail()
    const fields = structuredClone(patch)
    return this.mutate(scope, token, opened => {
      const source = opened.notes.find(n => n.note.id === id)
      if (!source || source.state !== 'live') fail('missing_local_source')
      if (!localSafe(source.note.revision + 1)) fail('source_limit')
      const note = structuredClone(source.note)
      for (const [key, value] of Object.entries(fields)) {
        if (['title','content','color'].includes(key) && value !== null && (typeof value !== 'string' || value.includes('\0'))) fail()
        let normalized = value ?? (['tags','checklist'].includes(key) ? [] : ['pinned','archived'].includes(key) ? false : '')
        if (key === 'color' && !['default','coral','orange','yellow','green','teal','blue','purple','pink','brown','gray'].includes(normalized as string)) normalized = 'default'
        ;(note as unknown as Record<string, unknown>)[key] = normalized
      }
      note.revision++; note.updated_at = updatedAt
      const changed = validateLocalNote({ state: 'live', note }, opened.project.project_id)
      opened.notes[opened.notes.indexOf(source)] = changed
      return [changed]
    })
  }
  tombstoneNote(scope: BrowserSyncScope, token: LocalSourceToken, id: string, deletedAt: string): Promise<number> {
    localId(id); if (!timestamp(deletedAt)) fail()
    return this.mutate(scope, token, opened => {
      const source = opened.notes.find(n => n.note.id === id)
      if (!source || source.state !== 'live') fail('missing_local_source')
      if (!localSafe(source.note.revision + 1)) fail('source_limit')
      const n = source.note
      const changed = validateLocalNote({ state: 'tombstone', revision: n.revision + 1, note: { id: n.id, project_id: n.project_id, stage_id: n.stage_id, source_type: n.source_type, source_map_id: n.source_map_id, source_node_id: n.source_node_id, content_format: n.content_format, deleted_at: deletedAt } }, opened.project.project_id)
      opened.notes[opened.notes.indexOf(source)] = changed
      return [changed]
    })
  }
  replaceProject(scope: BrowserSyncScope, token: LocalSourceToken, input: NativeLocalProject): Promise<number> {
    const project = validateLocalProject(input)
    return this.mutate(scope, token, opened => { if (project.id !== opened.project.project_id || project.created_at !== opened.project.project.created_at) fail(); opened.project.project = project })
  }
  deleteProject(scope: BrowserSyncScope, token: LocalSourceToken, deletedAt: string): Promise<number> {
    if (!timestamp(deletedAt)) fail()
    return this.mutate(scope, token, () => {}, deletedAt)
  }
}
