// @vitest-environment node
import {it,expect,vi,afterEach} from 'vitest'
import {scope} from './bootstrap.testFixture'
import {contentConflictSetup} from './contentConflict.testFixture'
import {received} from './legacyNoteApply.testFixture'
import {BrowserDeviceRegistration} from './deviceRegistration'
import {BrowserReaderCapability} from './readerCapability'
import {syncApi} from '@/api/sync'
import {encryptedSyncV2Api} from '@/api/encryptedSyncV2'
import {encryptedSyncV3Api} from '@/api/encryptedSyncV3'
import {cloudProjectsApi} from '@/api/cloudProjects'
afterEach(()=>vi.restoreAllMocks())
async function setup(stage=false,format:'html'|'plain'='html',bad=false){
 const f=await contentConflictSetup(stage,format,true),seq=f.start+2
 if(bad){f.db.inbox.pop();await f.incoming(seq,{mutation:'update',parent:f.parent.row.event_id,change:e=>{e.dependencies.metadata_event_id=crypto.randomUUID()}});await expect(f.content.apply(scope,seq)).rejects.toThrow()}else await f.content.apply(scope,seq)
 await received(f,seq+1);await f.notes.apply(scope,seq+1);await f.proven.advance(scope)
 vi.spyOn(syncApi,'registerDevice').mockResolvedValue({protocol_version:1,device_id:scope.deviceId,last_ack_cursor:0});vi.spyOn(encryptedSyncV2Api,'capabilities').mockResolvedValue({supported_transport_version:2,writer_transport_version:3,cutover_epoch:2});vi.spyOn(encryptedSyncV3Api,'compressionReaderCapabilities').mockResolvedValue(undefined)
 const d=await new BrowserDeviceRegistration(f.transaction,()=>true).bind(f.auth,f.bindings as never).registerVerified(scope),reader=await new BrowserReaderCapability(f.transaction,()=>true).bind(f.auth,f.bindings as never).declare(scope,d),b=f.db.projectBindings[0] as any
 vi.spyOn(cloudProjectsApi,'listBootstraps').mockResolvedValue({projects:[{project_id:'p',bootstrap_id:b.bootstrap_id,origin_device_id:'44444444-4444-4444-8444-444444444444',state:'active',initial_event_count:0,initial_max_server_sequence:0}],current_cursor:seq+1})
 const registry=(await f.registry.reconcile(scope)).token,ack=vi.spyOn(encryptedSyncV3Api,'ack').mockResolvedValue(undefined);return {...f,ack,prepare:()=>f.proven.prepareAck(scope,reader,registry),target:bad?seq-1:seq+1}
}
for(const stage of [false,true])for(const format of ['html','plain'] as const)it(`ACK crosses ${stage?'Stage':'project'} ${format} peer conflict; exactly one request`,async()=>{const f=await setup(stage,format),p=await f.prepare();expect(await f.proven.ackOnce(p)).toEqual({status:'advanced',cursor:f.target,ready:false});expect(f.ack.mock.calls).toEqual([['fixture-token',scope.deviceId,f.target]]);expect((await f.proven.ackOnce(p)).status).toBe('no_progress');expect(f.ack).toHaveBeenCalledTimes(1)})
it.each([false,true])('invalid dependency stage=%s caps ACK before conflict',async stage=>{const f=await setup(stage,'plain',true);expect((await f.proven.ackOnce(await f.prepare())).cursor).toBe(f.target);expect(f.ack).toHaveBeenCalledTimes(1)})
it.each(['http','commit'] as const)('%s failure leaves ACK cursor unchanged, explicit retry succeeds',async kind=>{const f=await setup(true,'plain'),p=await f.prepare();if(kind==='http')f.ack.mockRejectedValueOnce(Error('lost'));else f.ack.mockImplementationOnce(async()=>f.abort());await expect(f.proven.ackOnce(p)).rejects.toThrow();expect(f.db.cursors[0]).toMatchObject({ack_cursor:0});f.abort(false);expect((await f.proven.ackOnce(p)).cursor).toBe(f.target);expect(f.ack).toHaveBeenCalledTimes(2)})
it('tampered group after ACK preparation cannot send HTTP',async()=>{const f=await setup(),p=await f.prepare();(f.db.legacyNoteHistory!.find((r:any)=>r.record_kind==='group') as any).members[0].server_sequence++;await expect(f.proven.ackOnce(p)).rejects.toThrow();expect(f.ack).not.toHaveBeenCalled();expect(f.db.cursors[0]).toMatchObject({ack_cursor:0})})
