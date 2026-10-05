import {mount,flushPromises} from '@vue/test-utils'
import {createPinia,setActivePinia} from 'pinia'
import {describe,it,expect,vi} from 'vitest'
import {useCloudSessionStore} from '@/stores/cloudSession'
import ProjectCoverAuthorityPanel from './ProjectCoverAuthorityPanel.vue'
function setup(){
 const pinia=createPinia();setActivePinia(pinia);const cloud=useCloudSessionStore()
 const inspect=vi.spyOn(cloud,'inspectCover').mockResolvedValue(),begin=vi.spyOn(cloud,'beginCover').mockResolvedValue(),retry=vi.spyOn(cloud,'retry').mockResolvedValue()
 cloud.coverAuthority.p={metadata_state:'active',active:false,has_local_cover:true,blockers:[]}
 const wrapper=mount(ProjectCoverAuthorityPanel,{props:{projectId:'p'},global:{plugins:[pinia]}})
 return{cloud,inspect,begin,retry,wrapper}
}
describe('explicit cover authority UX',()=>{
 it('opening only inspects, explicit publish is required and pending changes only retry',async()=>{
  const h=setup();await flushPromises();expect(h.inspect).toHaveBeenCalledWith('p');expect(h.begin).not.toHaveBeenCalled()
  await h.wrapper.get('button').trigger('click');await flushPromises();expect(h.begin).toHaveBeenCalledWith('p')
  h.cloud.coverAuthority.p!.pending={state:'sealed',blocker:'cover_readers_not_ready'}
  await flushPromises();expect(h.wrapper.text()).toContain('требуется обновление всех устройств')
  expect(h.wrapper.findAll('button').map(b=>b.text())).toEqual(['Повторить'])
  await h.wrapper.get('button').trigger('click');await flushPromises();expect(h.retry).toHaveBeenCalledOnce();h.wrapper.unmount()
 })
 it.each([['cover_blob_missing','Зашифрованная обложка пока недоступна'],['cover_blob_invalid','Обложка не прошла проверку']])('shows safe %s state without technical identifiers',async(code,label)=>{
  const h=setup();h.cloud.coverAuthority.p={metadata_state:'active',active:true,has_local_cover:true,blockers:[code]}
  await flushPromises();expect(h.wrapper.get('[role=status]').text()).toBe(label)
  expect(h.wrapper.text()).toContain('временно задерживает');expect(h.wrapper.text()).toContain('сохраняет зашифрованные изображения')
  expect(h.wrapper.text()).not.toContain('blob_id');expect(h.begin).not.toHaveBeenCalled();h.wrapper.unmount()
 })
})
