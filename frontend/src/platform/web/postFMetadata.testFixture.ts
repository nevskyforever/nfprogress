import {ordinaryV10Fixture} from './v10OrdinaryApply.testFixture'
import {metadataRow} from './metadataPrefix.testFixture'
import {BrowserV10Recovery} from './v10Recovery'
import {bindPrivateMetadataPrefix} from './privateMetadataPrefix'
import {scope} from './bootstrap.testFixture'
import type {BrowserSyncTransaction} from './syncDurability'

export type MetadataFixture=Awaited<ReturnType<typeof ordinaryV10Fixture>>
export const createMetadataRecovery=(f:MetadataFixture,tx:BrowserSyncTransaction=f.transaction,current=()=>true)=>new BrowserV10Recovery(tx,f.f.localOwner,current).bindPostFMetadata(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device)
export const createMetadataPrefix=(f:MetadataFixture,tx:BrowserSyncTransaction=f.transaction,current=()=>true)=>bindPrivateMetadataPrefix(tx,current,f.f.auth,f.f.bindings as never,f.f.keys as never,f.device)
/** Sender encryption only; no applied outcome/proof or local projection is fabricated. */
export async function pendingMetadata(f:MetadataFixture,operation:'update'|'delete'='update'){
 const head=f.f.db.ownerHeads!.find((h:any)=>h.owner_kind==='project_metadata') as any,prior=head.history.find((p:any)=>p.event_id===head.tip_event_ids[0])
 return metadataRow(f.f,(f.f.db.cursors[0] as any).pull_cursor+1,{revision:prior.revision+1,parent:prior.event_id,compressed:operation==='update',change:e=>{if(operation==='delete'){e.header.operation='delete';e.metadata=null;e.deleted_at=e.header.updated_at}}})
}
export const applyFamilyMetadata=(f:MetadataFixture,m:Awaited<ReturnType<typeof pendingMetadata>>)=>f.f.metadata.apply(scope,m.reference,f.f.auth,f.f.bindings as never,f.f.keys as never)
