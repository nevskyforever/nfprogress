// @vitest-environment node
import {it,expect,vi,afterEach} from 'vitest'
import {scope} from './bootstrap.testFixture'
import {routeSetup,contentRow} from './noteTransport.testFixture'
import {received} from './legacyNoteApply.testFixture'
import {BrowserContentNoteApplyRuntime} from './contentNoteApply'
import {BrowserDeviceRegistration} from './deviceRegistration'
import {BrowserReaderCapability} from './readerCapability'
import {syncApi} from '@/api/sync'
import {encryptedSyncV2Api} from '@/api/encryptedSyncV2'
import {encryptedSyncV3Api} from '@/api/encryptedSyncV3'
import {cloudProjectsApi} from '@/api/cloudProjects'
afterEach(()=>vi.restoreAllMocks())
async function setup(blocked?:'plain'|'stage'|'dependency'|'resolution'){
 const f=await routeSetup(),content=new BrowserContentNoteApplyRuntime(f.notes);await contentRow(f,2,{compressed:true,change:e=>{if(blocked==='plain')(e.event as any).note.content_format='plain';else if(blocked==='stage'){(e.event as any).note.stage_id='S';e.dependencies.stage_event_ids=[crypto.randomUUID()]}else if(blocked==='dependency')e.dependencies.metadata_event_id=crypto.randomUUID();else if(blocked==='resolution'){const parents=[crypto.randomUUID(),crypto.randomUUID()].sort(),h=e.event.header;e.event={version:2,header:{event_id:h.event_id,parent_event_id:parents[0]!,additional_parent_event_ids:[parents[1]!],project_id:'p',entity_id:h.entity_id,entity_type:'note',operation:'resolution',revision:3,updated_at:h.updated_at},mutation:'resolution',resolution:{conflict_group_id:crypto.randomUUID(),conflict_generation:1,resolved_event_ids:parents,strategy:'choose_version',selected_event_id:parents[0]!},result:{operation:'upsert',note:(e.event as any).note}}}}})
 if(blocked)await expect(content.apply(scope,2)).rejects.toThrow();else await content.apply(scope,2)
 await received(f,3);await f.notes.apply(scope,3);await f.proven.advance(scope)
 vi.spyOn(syncApi,'registerDevice').mockResolvedValue({protocol_version:1,device_id:scope.deviceId,last_ack_cursor:0});vi.spyOn(encryptedSyncV2Api,'capabilities').mockResolvedValue({supported_transport_version:2,writer_transport_version:3,cutover_epoch:2});vi.spyOn(encryptedSyncV3Api,'compressionReaderCapabilities').mockResolvedValue(undefined)
 const d=await new BrowserDeviceRegistration(f.transaction,()=>true).bind(f.auth,f.bindings as never).registerVerified(scope),reader=await new BrowserReaderCapability(f.transaction,()=>true).bind(f.auth,f.bindings as never).declare(scope,d),b=f.db.projectBindings[0] as any
 vi.spyOn(cloudProjectsApi,'listBootstraps').mockResolvedValue({projects:[{project_id:'p',bootstrap_id:b.bootstrap_id,origin_device_id:'44444444-4444-4444-8444-444444444444',state:'active',initial_event_count:0,initial_max_server_sequence:0}],current_cursor:3})
 const registry=(await f.registry.reconcile(scope)).token,ack=vi.spyOn(encryptedSyncV3Api,'ack').mockResolvedValue(undefined)
 return{...f,content,reader,registry,ack,prepare:()=>f.proven.prepareAck(scope,reader,registry)}
}
it('Content final proof allows ACK3 with one explicit request; no-progress adds none',async()=>{const f=await setup(),p=await f.prepare();expect((await f.proven.ackOnce(p))).toEqual({status:'advanced',cursor:3,ready:false});expect(f.ack.mock.calls).toEqual([['fixture-token',scope.deviceId,3]]);expect(f.db.cursors[0]).toMatchObject({ack_cursor:3,proven_prefix:3});expect((await f.proven.ackOnce(p)).status).toBe('no_progress');expect(f.ack).toHaveBeenCalledTimes(1)})
it.each(['plain','stage','dependency','resolution'] as const)('unsupported %s caps ACK before Content and later Legacy',async kind=>{const f=await setup(kind);expect((await f.proven.ackOnce(await f.prepare())).cursor).toBe(1);expect(f.ack).toHaveBeenCalledWith('fixture-token',scope.deviceId,1);expect(f.db.inbox[1]).toMatchObject({state:'received'})})
it.each(['lost','commit','http'] as const)('Content ACK %s failure retains cursor and permits same explicit retry',async kind=>{const f=await setup(),p=await f.prepare();if(kind==='commit')f.ack.mockImplementationOnce(async()=>f.abort());else f.ack.mockRejectedValueOnce(Error(kind));await expect(f.proven.ackOnce(p)).rejects.toThrow();expect(f.db.cursors[0]).toMatchObject({ack_cursor:0,proven_prefix:3});f.abort(false);expect((await f.proven.ackOnce(p)).cursor).toBe(3);expect(f.ack).toHaveBeenCalledTimes(2)})
it.each(['candidate','proof','owner','wire'] as const)('stale %s cannot send ACK across Content',async kind=>{const f=await setup(),p=await f.prepare();if(kind==='candidate')(f.db.legacyNoteHistory!.find((r:any)=>r.record_kind==='candidate'&&r.record_version===2) as any).record_digest='0'.repeat(64);else if(kind==='proof')(f.db.inbox[1] as any).content_note_proof.outcome_digest='0'.repeat(64);else if(kind==='owner')(f.db.ownerHeads![0] as any).tip_event_ids=[crypto.randomUUID()];else{const r=f.db.inbox[1] as any,w=JSON.parse(r.wire_item);w.event.revision++;r.wire_item=JSON.stringify(w)}await expect(f.proven.ackOnce(p)).rejects.toThrow();expect(f.ack).not.toHaveBeenCalled();expect(f.db.cursors[0]).toMatchObject({ack_cursor:0})})
it('server success with changed Content proof cannot commit stale ACK',async()=>{const f=await setup(),p=await f.prepare();f.ack.mockImplementationOnce(async()=>{(f.db.inbox[1] as any).content_note_proof.outcome_digest='0'.repeat(64)});await expect(f.proven.ackOnce(p)).rejects.toThrow();expect(f.ack).toHaveBeenCalledTimes(1);expect(f.db.cursors[0]).toMatchObject({ack_cursor:0})})
