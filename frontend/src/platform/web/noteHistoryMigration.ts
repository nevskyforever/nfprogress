import { BrowserPersistenceError } from './persistence'
import { immutableWireIdentity,validateBrowserInboxRecord,validateBrowserV3SyncState,type BrowserSyncScope } from './syncDurability'
import { validateBrowserProjectBinding } from './projectBindings'
import { validateBrowserMetadataHead } from './metadataApplyRecords'
import { validateLocalProjectRecord,validateLocalNoteRecord } from './localAuthorityRecords'
/** v6 structure only, no keys/crypto/repair/inference in versionchange. */
export function validateBrowserV6State(scopes:BrowserSyncScope[],stores:unknown[][]):void{
 const bad=():never=>{throw new BrowserPersistenceError('corrupt_record')}
 if(stores.length!==8)bad();const [out,inbound,cursors,receipts,bindings,heads,projects,notes]=stores as [unknown[],unknown[],unknown[],unknown[],unknown[],unknown[],unknown[],unknown[]]
 const scopeFor=(v:unknown)=>scopes.find(s=>s.accountId===(v as {account_id?:string})?.account_id)??bad()
 const incoming=inbound.map(v=>validateBrowserInboxRecord(v,scopeFor(v)))
 if(incoming.some(r=>r.record_version>3))bad()
 const received=incoming.map(r=>{if(r.state==='received')return structuredClone(r);if(r.state==='applied'){const {applied_proof:_proof,...row}=r;return{...row,state:'received',record_version:1}}if(r.state==='note_proven'){const {note_proof:_proof,...row}=r;return{...row,state:'received',record_version:1}}return bad()})
 validateBrowserV3SyncState(scopes,out,received,cursors,receipts)
 const lineage=bindings.map(v=>validateBrowserProjectBinding(v,scopeFor(v))),bindingKeys=new Set<string>(),boots=new Set<string>()
 for(const b of lineage){const k=immutableWireIdentity([b.account_id,b.project_id]),boot=immutableWireIdentity([b.account_id,b.bootstrap_id]);if(bindingKeys.has(k)||boots.has(boot))bad();bindingKeys.add(k);boots.add(boot)}
 const linked=new Set<string>(),ownerKeys=new Set<string>()
 for(const value of heads){const scope=scopeFor(value),h=validateBrowserMetadataHead(value,scope),b=lineage.find(b=>b.account_id===h.account_id&&b.project_id===h.owner_id),key=immutableWireIdentity([h.account_id,h.owner_id]);if(!b||b.mode!=='import_remote'||b.phase!=='captured'||b.remote_state!=='active'||b.bootstrap_id!==h.bootstrap_id||ownerKeys.has(key))bad();ownerKeys.add(key)
  for(const proof of h.history){const r=incoming.find(r=>r.account_id===h.account_id&&r.event_id===proof.event_id);if(r?.state!=='applied'||immutableWireIdentity(r.applied_proof)!==immutableWireIdentity(proof))bad();linked.add(immutableWireIdentity([h.account_id,r!.event_id]))}
 }
 for(const r of incoming){if(r.state==='applied'&&!linked.has(immutableWireIdentity([r.account_id,r.event_id])))bad();if(r.state==='note_proven'){const b=lineage.find(b=>b.account_id===r.account_id&&b.project_id===r.note_proof.header.project_id);if(!b||b.bootstrap_id!==r.note_proof.bootstrap_id||b.remote_state!=='active'||!(b.mode==='import_remote'&&b.phase==='captured'||b.mode==='upload_existing'&&b.phase==='completing'))bad()}}
 const ps=projects.map(v=>validateLocalProjectRecord(v,scopeFor(v))),projectKeys=new Set<string>(),noteKeys=new Set<string>()
 for(const p of ps){const k=immutableWireIdentity([p.account_id,p.project_id]);if(projectKeys.has(k))bad();projectKeys.add(k)}
 for(const value of notes){const n=validateLocalNoteRecord(value,scopeFor(value),(value as {project_id:string}).project_id),p=ps.find(p=>p.account_id===n.account_id&&p.project_id===n.project_id),k=immutableWireIdentity([n.account_id,n.note_id]);if(!p||n.source_revision>p.source_revision||noteKeys.has(k))bad();noteKeys.add(k)}
}
