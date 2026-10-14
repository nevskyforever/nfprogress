// @vitest-environment node
import {it,expect,vi,afterEach} from 'vitest'
import {metadataBetweenNotes,scope} from './metadataPrefix.testFixture'
import {BrowserDeviceRegistration} from './deviceRegistration'
import {BrowserReaderCapability} from './readerCapability'
import {syncApi} from '@/api/sync'
import {encryptedSyncV2Api} from '@/api/encryptedSyncV2'
import {encryptedSyncV3Api} from '@/api/encryptedSyncV3'
import {cloudProjectsApi} from '@/api/cloudProjects'
afterEach(()=>vi.restoreAllMocks())
async function gates(f:Awaited<ReturnType<typeof metadataBetweenNotes>>){
 vi.spyOn(syncApi,'registerDevice').mockResolvedValue({protocol_version:1,device_id:scope.deviceId,last_ack_cursor:9});vi.spyOn(encryptedSyncV2Api,'capabilities').mockResolvedValue({supported_transport_version:2,writer_transport_version:3,cutover_epoch:2});vi.spyOn(encryptedSyncV3Api,'compressionReaderCapabilities').mockResolvedValue(undefined)
 const d=await new BrowserDeviceRegistration(f.transaction,()=>true).bind(f.auth,f.bindings as never).registerVerified(scope),r=await new BrowserReaderCapability(f.transaction,()=>true).bind(f.auth,f.bindings as never).declare(scope,d),b=f.db.projectBindings[0] as any
 vi.spyOn(cloudProjectsApi,'listBootstraps').mockResolvedValue({projects:[{project_id:'p',bootstrap_id:b.bootstrap_id,origin_device_id:'44444444-4444-4444-8444-444444444444',state:'active',initial_event_count:0,initial_max_server_sequence:0}],current_cursor:3})
 return{reader:r,registry:(await f.registry.reconcile(scope)).token,ack:vi.spyOn(encryptedSyncV3Api,'ack').mockResolvedValue(undefined)}
}
it('new Metadata-qualified durable prefix produces bounded ACK3; replay unchanged',async()=>{const f=await metadataBetweenNotes(true);await f.proven.advance(scope);const g=await gates(f),p=await f.proven.prepareAck(scope,g.reader,g.registry),old=structuredClone(f.db);expect(await f.proven.ackOnce(p)).toMatchObject({status:'advanced',cursor:3,ready:false});expect(g.ack.mock.calls).toEqual([['fixture-token',scope.deviceId,3]]);expect(f.db.cursors[0]).toMatchObject({ack_cursor:3,proven_prefix:3,pull_cursor:3});for(const name of Object.keys(f.db).filter(n=>n!=='cursors'))expect(f.db[name]).toEqual(old[name]);expect((await f.proven.ackOnce(p)).status).toBe('no_progress');expect(g.ack).toHaveBeenCalledTimes(1)})
it.each(['lost','commit'])('Metadata ACK %s failure remains exact-retry-safe',async kind=>{const f=await metadataBetweenNotes();await f.proven.advance(scope);const g=await gates(f),p=await f.proven.prepareAck(scope,g.reader,g.registry);if(kind==='lost')g.ack.mockRejectedValueOnce(Error('lost_response'));else g.ack.mockImplementationOnce(async()=>{f.abort()});await expect(f.proven.ackOnce(p)).rejects.toThrow();expect(f.db.cursors[0]).toMatchObject({ack_cursor:0,proven_prefix:3});f.abort(false);expect((await f.proven.ackOnce(p)).cursor).toBe(3);expect(g.ack).toHaveBeenCalledTimes(2)})
it('received Metadata keeps prefix1/ACK1 despite applied Note3',async()=>{const f=await metadataBetweenNotes(false,false);await f.proven.advance(scope);const g=await gates(f),p=await f.proven.prepareAck(scope,g.reader,g.registry);expect((await f.proven.ackOnce(p)).cursor).toBe(1);expect(g.ack).toHaveBeenCalledWith('fixture-token',scope.deviceId,1)})
