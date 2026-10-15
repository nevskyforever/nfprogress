// @vitest-environment node
import {it,expect,vi,afterEach} from 'vitest'
import {scope} from './bootstrap.testFixture'
import {contentLocalConflict,localVersion} from './contentLocalConflict.testFixture'
import {received} from './legacyNoteApply.testFixture'
import {contentRow} from './noteTransport.testFixture'
import {BrowserDeviceRegistration} from './deviceRegistration'
import {BrowserReaderCapability} from './readerCapability'
import {syncApi} from '@/api/sync'
import {encryptedSyncV2Api} from '@/api/encryptedSyncV2'
import {encryptedSyncV3Api} from '@/api/encryptedSyncV3'
import {cloudProjectsApi} from '@/api/cloudProjects'
afterEach(()=>vi.restoreAllMocks())
async function setup(bad=false){const f=await contentLocalConflict('update','delete',true);if(bad){f.db.inbox.pop();await contentRow(f,3,{mutation:'update',parent:f.root.event_id,change:e=>{(e.event as any).note.content_format='plain'}});await expect(f.content.apply(scope,3)).rejects.toThrow()}else await f.content.apply(scope,3);await received(f,4);await f.notes.apply(scope,4);await f.proven.advance(scope)
 vi.spyOn(syncApi,'registerDevice').mockResolvedValue({protocol_version:1,device_id:scope.deviceId,last_ack_cursor:0});vi.spyOn(encryptedSyncV2Api,'capabilities').mockResolvedValue({supported_transport_version:2,writer_transport_version:3,cutover_epoch:2});vi.spyOn(encryptedSyncV3Api,'compressionReaderCapabilities').mockResolvedValue(undefined)
 const d=await new BrowserDeviceRegistration(f.transaction,()=>true).bind(f.auth,f.bindings as never).registerVerified(scope),reader=await new BrowserReaderCapability(f.transaction,()=>true).bind(f.auth,f.bindings as never).declare(scope,d),b=f.db.projectBindings[0] as any
 vi.spyOn(cloudProjectsApi,'listBootstraps').mockResolvedValue({projects:[{project_id:'p',bootstrap_id:b.bootstrap_id,origin_device_id:'44444444-4444-4444-8444-444444444444',state:'active',initial_event_count:0,initial_max_server_sequence:0}],current_cursor:4});const registry=(await f.registry.reconcile(scope)).token,ack=vi.spyOn(encryptedSyncV3Api,'ack').mockResolvedValue(undefined);return{...f,ack,prepare:()=>f.proven.prepareAck(scope,reader,registry)}}
it('explicit ACK4 crosses proof2, one request, no-progress adds none',async()=>{const f=await setup(),p=await f.prepare();expect(await f.proven.ackOnce(p)).toEqual({status:'advanced',cursor:4,ready:false});expect(f.ack.mock.calls).toEqual([['fixture-token',scope.deviceId,4]]);expect((await f.proven.ackOnce(p)).status).toBe('no_progress');expect(f.ack).toHaveBeenCalledTimes(1)})
it('plain mismatch caps ACK2 before unrelated safe Note4',async()=>{const f=await setup(true);expect((await f.proven.ackOnce(await f.prepare())).cursor).toBe(2);expect(f.ack).toHaveBeenCalledWith('fixture-token',scope.deviceId,2)})
it.each(['frozen','intent','source'] as const)('changed %s cannot send prepared ACK',async kind=>{const f=await setup(),p=await f.prepare();if(kind==='frozen')localVersion(f).record_digest='0'.repeat(64);if(kind==='intent')(f.db.legacyNoteIntents![0] as any).mutation_generation++;if(kind==='source')(f.db.localNotes![0] as any).source_revision++;await expect(f.proven.ackOnce(p)).rejects.toThrow();expect(f.ack).not.toHaveBeenCalled();expect(f.db.cursors[0]).toMatchObject({ack_cursor:0})})
it.each(['http','commit'] as const)('%s failure keeps cursor and existing retry semantics',async kind=>{const f=await setup(),p=await f.prepare();if(kind==='http')f.ack.mockRejectedValueOnce(Error('lost'));else f.ack.mockImplementationOnce(async()=>f.abort());await expect(f.proven.ackOnce(p)).rejects.toThrow();expect(f.db.cursors[0]).toMatchObject({ack_cursor:0});f.abort(false);expect((await f.proven.ackOnce(p)).cursor).toBe(4);expect(f.ack).toHaveBeenCalledTimes(2)})
it('intent drift during server success cannot commit stale local ACK cursor',async()=>{const f=await setup(),p=await f.prepare();f.ack.mockImplementationOnce(async()=>{(f.db.legacyNoteIntents![0] as any).mutation_generation++});await expect(f.proven.ackOnce(p)).rejects.toThrow();expect(f.ack).toHaveBeenCalledTimes(1);expect(f.db.cursors[0]).toMatchObject({ack_cursor:0})})
