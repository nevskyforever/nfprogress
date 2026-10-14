import {metadataSetup,metadataRow,applyMetadata,scope} from './metadataPrefix.testFixture'
import {amk,at} from './bootstrap.testFixture'
import {BrowserStageApply} from './stageApply'
import {frameStructuralEvent,type StructuralEvent} from '@/cloud/stageCodec'
import golden from '@/cloud/__fixtures__/stageCodecV1.json'
import {compressCanonicalFrame} from '@/cloud/frameCompression'
import {encryptObjectBytes} from '@/crypto'
import {encodeBase64Url} from '@/api/base64url'
export {scope}
export async function stageSetup(){const f=await metadataSetup(),metadata=await metadataRow(f,1);await applyMetadata(f,metadata);return{...f,metadataEvent:metadata.event,stages:new BrowserStageApply(f.transaction,()=>true).bind(f.auth,f.bindings as never,f.keys as never)}}
export async function stageRow(f:Awaited<ReturnType<typeof stageSetup>>,seq:number,options:{compressed?:boolean;version?:1|2;parent?:string;revision?:number;frameTransform?:(f:Uint8Array)=>Uint8Array;frameChange?:(f:Uint8Array)=>void;change?:(e:StructuralEvent)=>void}={}){
 const revision=options.revision??1,event=structuredClone(golden.event) as StructuralEvent
 Object.assign(event.header,{account_id:scope.canonicalUserId,bootstrap_id:(f.db.projectBindings[0] as any).bootstrap_id,project_id:'p',entity_id:'s',event_id:crypto.randomUUID(),device_id:'44444444-4444-4444-8444-444444444444',operation:revision===1?'create':'update',revision,generation:revision,parent_event_ids:options.parent?[options.parent]:[],metadata_event_id:f.metadataEvent.header.event_id,updated_at:at});event.version=options.version??1;event.stage!.name='PRIVATE_STAGE'.repeat(30);options.change?.(event)
 const original=frameStructuralEvent(event),selected=options.compressed?compressCanonicalFrame(original):original,frame=options.frameTransform?.(selected)??selected
 if(options.compressed&&frame[11]!==1)throw Error('expected_ID1')
 options.frameChange?.(frame)
 const o=await encryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:event.header.project_id,entityId:event.header.entity_id,entityType:event.header.entity_type},frame),reference={event_id:event.header.event_id,device_id:event.header.device_id,server_sequence:seq,project_id:event.header.project_id,entity_id:event.header.entity_id,entity_type:event.header.entity_type,operation:event.header.operation==='delete'?'delete':'upsert',revision:event.header.revision,updated_at:event.header.updated_at,deleted_at:event.deleted_at},row={record_version:1,account_id:scope.accountId,device_id:scope.deviceId,event_id:reference.event_id,server_sequence:seq,protocol_version:3,state:'received',wire_item:JSON.stringify({event:reference,object:{crypto_version:1,aad_version:1,nonce:encodeBase64Url(o.nonce),ciphertext:encodeBase64Url(o.ciphertext)}})}
 original.fill(0);if(selected!==original)selected.fill(0);if(frame!==original)frame.fill(0);o.nonce.fill(0);o.ciphertext.fill(0);f.db.inbox.push(row);f.db.cursors=[{...(f.db.cursors[0] as any),pull_cursor:seq}];return{event,row}
}
