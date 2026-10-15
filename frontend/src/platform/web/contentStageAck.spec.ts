// @vitest-environment node
import {it,expect,vi,afterEach} from 'vitest'
import {scope} from './bootstrap.testFixture'
import {contentStageSetup,stageContent} from './contentStage.testFixture'
import {received} from './legacyNoteApply.testFixture'
import {BrowserDeviceRegistration} from './deviceRegistration'
import {BrowserReaderCapability} from './readerCapability'
import {syncApi} from '@/api/sync'
import {encryptedSyncV2Api} from '@/api/encryptedSyncV2'
import {encryptedSyncV3Api} from '@/api/encryptedSyncV3'
import {cloudProjectsApi} from '@/api/cloudProjects'
afterEach(()=>vi.restoreAllMocks())
async function setup(kind='safe'){
 const f=await contentStageSetup();await stageContent(f,3,{compressed:true,refs:kind==='bad'?[crypto.randomUUID()]:undefined,change:e=>{if(kind==='plain')(e.event as any).note.content_format='plain';if(kind==='resolution'){const parents=[crypto.randomUUID(),crypto.randomUUID()].sort(),h=e.event.header;e.event={version:2,header:{event_id:h.event_id,parent_event_id:parents[0]!,additional_parent_event_ids:[parents[1]!],project_id:'p',entity_id:h.entity_id,entity_type:'note',operation:'resolution',revision:3,updated_at:h.updated_at},mutation:'resolution',resolution:{conflict_group_id:crypto.randomUUID(),conflict_generation:1,resolved_event_ids:parents,strategy:'choose_version',selected_event_id:parents[0]!},result:{operation:'upsert',note:(e.event as any).note}}}}})
 if(kind==='safe')await f.content.apply(scope,3);else await expect(f.content.apply(scope,3)).rejects.toThrow();await received(f,4);await f.notes.apply(scope,4);await f.proven.advance(scope)
 vi.spyOn(syncApi,'registerDevice').mockResolvedValue({protocol_version:1,device_id:scope.deviceId,last_ack_cursor:0});vi.spyOn(encryptedSyncV2Api,'capabilities').mockResolvedValue({supported_transport_version:2,writer_transport_version:3,cutover_epoch:2});vi.spyOn(encryptedSyncV3Api,'compressionReaderCapabilities').mockResolvedValue(undefined)
 const d=await new BrowserDeviceRegistration(f.transaction,()=>true).bind(f.auth,f.bindings as never).registerVerified(scope),reader=await new BrowserReaderCapability(f.transaction,()=>true).bind(f.auth,f.bindings as never).declare(scope,d),b=f.db.projectBindings[0] as any
 vi.spyOn(cloudProjectsApi,'listBootstraps').mockResolvedValue({projects:[{project_id:'p',bootstrap_id:b.bootstrap_id,origin_device_id:'44444444-4444-4444-8444-444444444444',state:'active',initial_event_count:0,initial_max_server_sequence:0}],current_cursor:4})
 const registry=(await f.registry.reconcile(scope)).token,ack=vi.spyOn(encryptedSyncV3Api,'ack').mockResolvedValue(undefined);return{...f,reader,registry,ack,prepare:()=>f.proven.prepareAck(scope,reader,registry)}
}
it('safe Stage Content ACK4 uses one request; repeated/no-progress uses none',async()=>{const f=await setup(),p=await f.prepare();expect(await f.proven.ackOnce(p)).toEqual({status:'advanced',cursor:4,ready:false});expect(f.ack.mock.calls).toEqual([['fixture-token',scope.deviceId,4]]);expect(await f.proven.ackOnce(p)).toEqual({status:'no_progress',cursor:4,ready:false});expect(f.ack).toHaveBeenCalledTimes(1)})
it.each(['bad','plain','resolution'])('%s Stage Content caps prefix/ACK2 before later safe Legacy',async kind=>{const f=await setup(kind);expect((await f.proven.ackOnce(await f.prepare())).cursor).toBe(2);expect(f.ack).toHaveBeenCalledWith('fixture-token',scope.deviceId,2);expect(f.db.inbox[2]).toMatchObject({state:'received'})})
it('changed Stage owner invalidates prepared ACK before sending',async()=>{const f=await setup(),p=await f.prepare();(f.db.ownerHeads!.find((h:any)=>h.owner_kind==='stage') as any).tip_event_ids=[crypto.randomUUID()];await expect(f.proven.ackOnce(p)).rejects.toThrow();expect(f.ack).not.toHaveBeenCalled();expect(f.db.cursors[0]).toMatchObject({ack_cursor:0})})
