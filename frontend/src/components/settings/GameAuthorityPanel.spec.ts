import {flushPromises,mount} from '@vue/test-utils'
import {createPinia,setActivePinia} from 'pinia'
import {describe,it,expect,vi} from 'vitest'
import {useCloudSessionStore} from '@/stores/cloudSession'
import Panel from './GameAuthorityPanel.vue'
import {announceDataChange} from '@/services/dataChanges'
function setup(state:string){
 const pinia=createPinia();setActivePinia(pinia);const cloud=useCloudSessionStore()
 cloud.gameAuthority={owners:[{owner_key:'account',state,blocker:null,blockers:[],tips:['b','a'],local:{coins:'10.000000'},versions:[{event_id:'a',snapshot:{coins:'10.000000',experience:'500.000000'}},{event_id:'b',snapshot:{coins:'8.000000',experience:'500.000000'}}]}],rewards:[{event_id:'reward',date:'2026-10-04',reward:{coins:'10.000000',experience:'500.000000'}}],blockers:[]}
 const begin=vi.spyOn(cloud,'beginGame').mockResolvedValue(),choose=vi.spyOn(cloud,'chooseGameHistory').mockResolvedValue(),compensate=vi.spyOn(cloud,'compensateGameReward').mockResolvedValue()
 const wrapper=mount(Panel,{global:{plugins:[pinia]}})
 return{cloud,wrapper,begin,choose,compensate}
}
const button=(h:ReturnType<typeof setup>,label:string)=>h.wrapper.findAll('button').find(b=>b.text()===label)!
describe('explicit Game authority UX',()=>{
 it('refreshes deferred mutation blockers without publishing and removes its listener on close',async()=>{
  const h=setup('active'),inspect=vi.spyOn(h.cloud,'inspectGame').mockImplementation(async()=>{
   h.cloud.gameAuthority!.owners[0]!.state='blocked'
   h.cloud.gameAuthority!.owners[0]!.blocker='game_unsupported_local_mutation'
  })
  announceDataChange('game');await flushPromises()
  expect(inspect).toHaveBeenCalledOnce();expect(h.wrapper.text()).not.toContain('Данные согласованы')
  expect(h.begin).not.toHaveBeenCalled();h.wrapper.unmount()
  announceDataChange('game');expect(inspect).toHaveBeenCalledOnce()
 })
 it.each(['local','publication_pending','self_echo_pending','active','blocked','conflict'])('opening %s never publishes or resolves',state=>{const h=setup(state);expect(h.begin).not.toHaveBeenCalled();expect(h.choose).not.toHaveBeenCalled();expect(h.compensate).not.toHaveBeenCalled();h.wrapper.unmount()})
 it('publishes only after explicit click',async()=>{const h=setup('local');await button(h,'Опубликовать игровой прогресс').trigger('click');await flushPromises();expect(h.begin).toHaveBeenCalledTimes(1);h.wrapper.unmount()})
 it('resolves with full tips and captured local projection',async()=>{const h=setup('conflict');await h.wrapper.find('select').setValue('b');await button(h,'Оставить выбранную историю').trigger('click');await flushPromises();expect(h.choose).toHaveBeenCalledWith({owner_key:'account',expected_tips:['b','a'],expected_local:{coins:'10.000000'},selected_event_id:'b'});expect(h.wrapper.text()).not.toContain('event_id');h.wrapper.unmount()})
 it('requires reward selection and separate reversal confirmation',async()=>{const h=setup('active');const b=button(h,'Отменить выбранную награду');expect(b.attributes('disabled')).toBeDefined();await h.wrapper.find('select').setValue('reward');expect(b.attributes('disabled')).toBeDefined();await h.wrapper.find('input[type=checkbox]').setValue(true);await b.trigger('click');await flushPromises();expect(h.compensate).toHaveBeenCalledWith({target_action_id:'reward',expected_tips:['b','a'],expected_local:{coins:'10.000000'}});expect(h.wrapper.find('input').element).toHaveProperty('checked',false);h.wrapper.unmount()})
 it('shows friendly failure without raw diagnostic text',async()=>{const h=setup('local');h.begin.mockRejectedValueOnce(new Error('secret internal payload'));await button(h,'Опубликовать игровой прогресс').trigger('click');await flushPromises();expect(h.wrapper.find('[role=alert]').exists()).toBe(true);expect(h.wrapper.text()).not.toContain('secret internal payload');h.wrapper.unmount()})
})
