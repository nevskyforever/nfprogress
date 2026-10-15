import {vi,expect} from 'vitest'
import {scope} from './bootstrap.testFixture'
import {contentLocalConflict} from './contentLocalConflict.testFixture'
import {received} from './legacyNoteApply.testFixture'
import {contentRow} from './noteTransport.testFixture'
import {BrowserDeviceRegistration} from './deviceRegistration'
import {BrowserReaderCapability} from './readerCapability'
import {syncApi} from '@/api/sync'
import {encryptedSyncV2Api} from '@/api/encryptedSyncV2'
import {encryptedSyncV3Api} from '@/api/encryptedSyncV3'
import {cloudProjectsApi} from '@/api/cloudProjects'
export async function contentLocalAck(bad=false){const f=await contentLocalConflict('update','delete',true);if(bad){f.db.inbox.pop();await contentRow(f,3,{mutation:'update',parent:f.root.event_id,change:e=>{(e.event as any).note.content_format='plain'}});await expect(f.content.apply(scope,3)).rejects.toThrow()}else await f.content.apply(scope,3);await received(f,4);await f.notes.apply(scope,4);await f.proven.advance(scope)
 vi.spyOn(syncApi,'registerDevice').mockResolvedValue({protocol_version:1,device_id:scope.deviceId,last_ack_cursor:0});vi.spyOn(encryptedSyncV2Api,'capabilities').mockResolvedValue({supported_transport_version:2,writer_transport_version:3,cutover_epoch:2});vi.spyOn(encryptedSyncV3Api,'compressionReaderCapabilities').mockResolvedValue(undefined)
 const d=await new BrowserDeviceRegistration(f.transaction,()=>true).bind(f.auth,f.bindings as never).registerVerified(scope),reader=await new BrowserReaderCapability(f.transaction,()=>true).bind(f.auth,f.bindings as never).declare(scope,d),b=f.db.projectBindings[0] as any
 vi.spyOn(cloudProjectsApi,'listBootstraps').mockResolvedValue({projects:[{project_id:'p',bootstrap_id:b.bootstrap_id,origin_device_id:'44444444-4444-4444-8444-444444444444',state:'active',initial_event_count:0,initial_max_server_sequence:0}],current_cursor:4});const registry=(await f.registry.reconcile(scope)).token,ack=vi.spyOn(encryptedSyncV3Api,'ack').mockResolvedValue(undefined);return{...f,ack,prepare:()=>f.proven.prepareAck(scope,reader,registry)}}
