// @vitest-environment node
import{describe,expect,it,vi,afterEach}from'vitest'
import{cloudProjectsApi}from'@/api/cloudProjects'
import{syncApi}from'@/api/sync'
import{scope}from'./bootstrap.testFixture'
import{imported,received}from'./legacyNoteApply.testFixture'
afterEach(()=>vi.restoreAllMocks())
describe('C21.1.18 explicit prefix diagnostics / transport STOP',()=>{
 it('no-progress with empty prefix, no network or registration',async()=>{const f=await imported(),ack=vi.spyOn(syncApi,'ack'),reg=vi.spyOn(syncApi,'registerDevice'),list=vi.spyOn(cloudProjectsApi,'listBootstraps');expect(await f.proven.ackStatus(scope)).toMatchObject({code:'no_ack_progress',candidate_ack_cursor:0,ack_eligible:false,ready:false});expect(ack).not.toHaveBeenCalled();expect(reg).not.toHaveBeenCalled();expect(list).not.toHaveBeenCalled()})
 it('fresh explicit registry token reports transport unavailable, never turns runtime token into durable ACK authority',async()=>{const f=await imported();await received(f,1);await f.notes.apply(scope,1);expect(await f.proven.ackStatus(scope)).toMatchObject({code:'safe_note_prefix_available',candidate_ack_cursor:0,candidate_proven_prefix:1});await f.proven.advance(scope);const b=f.db.projectBindings[0] as any;vi.spyOn(cloudProjectsApi,'listBootstraps').mockResolvedValue({current_cursor:1,projects:[{project_id:'p',bootstrap_id:b.bootstrap_id,origin_device_id:crypto.randomUUID(),state:'active',initial_event_count:1,initial_max_server_sequence:1}]});const {token}=await f.registry.reconcile(scope),ack=vi.spyOn(syncApi,'ack'),reg=vi.spyOn(syncApi,'registerDevice'),list=cloudProjectsApi.listBootstraps as any;list.mockClear();expect(await f.proven.ackStatus(scope,token)).toMatchObject({code:'ack_transport_unavailable',candidate_ack_cursor:1,current_ack_cursor:0,ready:false,ack_eligible:false});expect(ack).not.toHaveBeenCalled();expect(reg).not.toHaveBeenCalled();expect(list).not.toHaveBeenCalled();expect(await f.sync.readCheckpoint(scope)).toMatchObject({proven_prefix:1,ack_cursor:0});const old=structuredClone(f.db);expect(await f.proven.ackStatus(scope,{} as never)).toMatchObject({code:'registry_reconciliation_required'});expect(f.db).toEqual(old)})
})
