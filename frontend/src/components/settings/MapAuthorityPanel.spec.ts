import {mount,flushPromises} from '@vue/test-utils'
import {createPinia,setActivePinia} from 'pinia'
import {describe,it,expect,vi} from 'vitest'
import {useCloudSessionStore} from '@/stores/cloudSession'
import MapAuthorityPanel from './MapAuthorityPanel.vue'
function setup(){const pinia=createPinia();setActivePinia(pinia);const cloud=useCloudSessionStore();const begin=vi.spyOn(cloud,'beginMaps').mockResolvedValue();const choose=vi.spyOn(cloud,'chooseMapVersion').mockResolvedValue();const wrapper=mount(MapAuthorityPanel,{props:{projectId:'p'},global:{plugins:[pinia],stubs:{MindMapEditor:true}}});return {cloud,begin,choose,wrapper}}
describe('explicit map authority UX',()=>{
 it('opening never captures; explicit action publishes selected project',async()=>{const h=setup();expect(h.begin).not.toHaveBeenCalled();await h.wrapper.findAll('button').find(b=>b.text()==='Опубликовать карты')!.trigger('click');await flushPromises();expect(h.begin).toHaveBeenCalledWith('p');h.wrapper.unmount()})
 it('preserves whole-version decisions and exact rendered CAS evidence',async()=>{const h=setup();const owner={entity_id:'project-map',stage_id:null,state:'conflict',blocker:null,tips:['a','b'],local:{owner:{mindmap:'local'}},versions:[{event_id:'a',revision:2,mutation:'delete',map:null},{event_id:'b',revision:2,mutation:'delete',map:null}]};h.cloud.mapAuthority.p={owners:[owner]};await flushPromises();expect(h.wrapper.findAll('article > details')).toHaveLength(3);await h.wrapper.findAll('button').find(b=>b.text()==='Использовать эту версию')!.trigger('click');await flushPromises();expect(h.choose).toHaveBeenCalledWith({project_id:'p',stage_id:null,expected_tips:['a','b'],expected_local:owner.local,selected_event_id:'a'},undefined);h.wrapper.unmount()})
})
