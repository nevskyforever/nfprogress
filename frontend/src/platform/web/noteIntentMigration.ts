import { validateBrowserV6State } from './noteHistoryMigration'
import { validateNoteHistorySet } from './noteHistoryRecords'
import { inspectBrowserAckInventory } from './ackPrerequisites'
import { validateBrowserProjectBinding } from './projectBindings'
import { immutableWireIdentity,validateBrowserInboxRecord,type BrowserSyncScope } from './syncDurability'
import { BrowserPersistenceError } from './persistence'
/** Structural v7 validation only; never synthesize unsealed intents or decrypt content. */
export function validateBrowserV7State(scopes:BrowserSyncScope[],stores:unknown[][]){
 const bad=():never=>{throw new BrowserPersistenceError('corrupt_record')};if(stores.length!==9)bad()
 const scopeFor=(v:unknown)=>scopes.find(s=>s.accountId===(v as {account_id?:string})?.account_id)??bad(),rows=stores[1]!.map(v=>validateBrowserInboxRecord(v,scopeFor(v)))
 const oldRows=rows.map(r=>{if(r.state!=='note_conflict_preserved')return r;const {note_conflict_proof:_proof,...rest}=r;return{...rest,state:'received',record_version:1}})
 validateBrowserV6State(scopes,[stores[0]!,oldRows,...stores.slice(2,8)])
 for(const row of stores[8]!)scopeFor(row)
 for(const scope of scopes){const own=(rows:unknown[])=>rows.filter(r=>(r as {account_id:string}).account_id===scope.accountId),history=validateNoteHistorySet(scope,own(stores[8]!)),bindings=own(stores[4]!).map(r=>validateBrowserProjectBinding(r,scope)),cursor=own(stores[2]!)[0] as {pull_cursor:number}|undefined
  for(const r of history){if(r.record_kind==='local_version')bad();const b=bindings.find(b=>b.project_id===r.project_id);if(!b||r.bootstrap_id!==b.bootstrap_id)bad();if(r.record_kind==='candidate'){if(r.origin==='local_sealed')bad();if(r.origin==='peer'){const inbound=rows.find(v=>v.account_id===scope.accountId&&v.event_id===r.event_id);if(!inbound||!['note_proven','note_conflict_preserved'].includes(inbound.state)||inbound.protocol_version!==r.protocol_version)bad();const wire=JSON.parse(inbound!.wire_item),{device_id:device,server_sequence:_seq,...event}=wire.event;if(device!==r.source_device_id||immutableWireIdentity({event,object:wire.object})!==immutableWireIdentity(JSON.parse(r.wire_item)))bad()}else{const out=own(stores[0]!).find(v=>(v as {event_id:string}).event_id===r.event_id) as {protocol_version:number;raw_body:string}|undefined;if(!out||out.protocol_version!==r.protocol_version||immutableWireIdentity(JSON.parse(out.raw_body).items[0])!==immutableWireIdentity(JSON.parse(r.wire_item)))bad()}}}
  inspectBrowserAckInventory(scope,{pull_cursor:cursor?.pull_cursor??0,ack_cursor:0,proven_prefix:0,next_local_ordinal:1},own(rows),own(stores[5]!),bindings,history)
 }
}
