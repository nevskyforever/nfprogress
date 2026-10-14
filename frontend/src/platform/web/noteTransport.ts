import { decodeBase64Url } from '@/api/base64url'
import { decryptObjectBytes, type AccountMasterKey } from '@/crypto'
import { decodeNoteSyncPlaintext, noteSyncEligibility, type NoteSyncPlaintext } from '@/cloud/noteSyncCodec'
import type { ContentNoteEvent } from '@/cloud/contentNoteCodec'
import { canonicalizeSyncTimestamp } from '@/cloud/syncTimestamp'
import { openBrowserCanonicalObject } from './canonicalReaders'
import { BrowserPersistenceError } from './persistence'
import { snapshotBrowserSyncScope, type BrowserSyncScope } from './syncDurability'
export type NoteTransportKind = 'legacy' | 'content_note_v1'
function fail(): never { throw new BrowserPersistenceError('note_rejected') }
/** Internal authenticated route selection. Never replaces or relabels the original object. */
export async function openNoteTransport(scope: BrowserSyncScope, amk: AccountMasterKey, protocol: 2|3, wire: string, kind: NoteTransportKind): Promise<{ plaintext: NoteSyncPlaintext; content?: ContentNoteEvent }> {
 scope=snapshotBrowserSyncScope(scope)
 let nonce: Uint8Array|undefined, ciphertext: Uint8Array|undefined, bytes: Uint8Array|undefined
 try {
  const item=JSON.parse(wire), r=item.event
  if(r.entity_type!=='note')fail()
  nonce=decodeBase64Url(item.object.nonce);ciphertext=decodeBase64Url(item.object.ciphertext)
  let plaintext: NoteSyncPlaintext, content: ContentNoteEvent|undefined
  if(kind==='legacy') {
   if(!['upsert','delete'].includes(r.operation))fail()
   bytes=await decryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:r.project_id,entityId:r.entity_id,entityType:'note'},{...item.object,nonce,ciphertext})
   plaintext=decodeNoteSyncPlaintext(bytes)
  } else if(kind==='content_note_v1') {
   if(protocol!==3||r.operation!=='event'||r.deleted_at!==null)fail()
   content=await openBrowserCanonicalObject(amk,{accountId:scope.canonicalUserId,projectId:r.project_id,entityId:r.entity_id,entityType:'note',eventId:r.event_id},{...item.object,nonce,ciphertext}) as ContentNoteEvent
   if(content.event.version!==1)throw new BrowserPersistenceError('unsupported_local_source')
   if(content.device_id!==r.device_id)fail()
   plaintext=content.event
  } else return fail()
  const h=plaintext.header
  if(h.event_id!==r.event_id||h.project_id!==r.project_id||h.entity_id!==r.entity_id||h.revision!==r.revision||canonicalizeSyncTimestamp(h.updated_at)!==canonicalizeSyncTimestamp(r.updated_at))fail()
  if(kind==='legacy'&&(h.operation!==r.operation||(h.deleted_at===null)!==(r.deleted_at===null)||h.deleted_at!==null&&canonicalizeSyncTimestamp(h.deleted_at)!==canonicalizeSyncTimestamp(r.deleted_at)))fail()
  if(!noteSyncEligibility(plaintext).eligible||plaintext.note.stage_id!==null||plaintext.note.source_type!=='project'||plaintext.note.source_map_id!==null||plaintext.note.source_node_id!==null)throw new BrowserPersistenceError('unsupported_local_source')
  return {plaintext,...(content?{content}:{})}
 } catch(e) {if(e instanceof BrowserPersistenceError)throw e;return fail()}
 finally {nonce?.fill(0);ciphertext?.fill(0);bytes?.fill(0)}
}
