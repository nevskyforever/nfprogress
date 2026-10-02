import { mount,flushPromises } from '@vue/test-utils'
import { createPinia,setActivePinia } from 'pinia'
import { describe,it,expect,vi } from 'vitest'
import { useCloudSessionStore } from '@/stores/cloudSession'
import ContentNoteAuthorityPanel from './ContentNoteAuthorityPanel.vue'
function setup(){
 const pinia=createPinia();setActivePinia(pinia);const cloud=useCloudSessionStore()
 cloud.noteAuthority.p={state:'content_local',activated:false,candidates:[]}
 const begin=vi.spyOn(cloud,'beginNotes').mockResolvedValue()
 const choose=vi.spyOn(cloud,'chooseNoteVersion').mockResolvedValue()
 const wrapper=mount(ContentNoteAuthorityPanel,{props:{projectId:'p'},global:{plugins:[pinia]}})
 return {cloud,begin,choose,wrapper}
}
describe('explicit Note publication and preserved conflict UI',()=>{
 it('opening never publishes; a click starts the selected project migration',async()=>{
  const h=setup();expect(h.begin).not.toHaveBeenCalled()
  await h.wrapper.findAll('button').find(b=>b.text()==='Опубликовать заметки')!.trigger('click');await flushPromises()
  expect(h.begin).toHaveBeenCalledWith('p');h.wrapper.unmount()
 })
 it('shows both versions as text and submits the exact rendered full-tip decision',async()=>{
  const h=setup();const decision={group_id:'g',note_id:'n',generation:3,local:{revision:2},versions:[{event_id:'a',operation:'upsert',revision:2,note:{title:'Writer title',content:'<script>unsafe()</script>'}},{event_id:'b',operation:'delete',revision:2,note:{deleted_at:'now'}}]}
  h.cloud.noteConflicts.p=[decision];await flushPromises()
  expect(h.wrapper.text()).toContain('Writer title');expect(h.wrapper.text()).toContain('Заметка удалена');expect(h.wrapper.find('script').exists()).toBe(false)
  await h.wrapper.findAll('button').find(b=>b.text()==='Использовать эту версию')!.trigger('click');await flushPromises()
  expect(h.choose).toHaveBeenCalledWith('p',decision,'a');h.wrapper.unmount()
 })
})
