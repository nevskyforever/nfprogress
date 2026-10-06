import {mount} from '@vue/test-utils'
import {createPinia} from 'pinia'
import {expect,it} from 'vitest'
import Panel from './LocalWordBindingPanel.vue'
function panel(attached=false){return mount(Panel,{props:{attached,state:attached?'external_proposal':'unlinked',externalContent:{type:'doc',content:[{type:'paragraph',content:[{type:'text',text:'Local external manuscript'}]}]}},global:{plugins:[createPinia()]}})}
it('shows an unattached local binding without performing a choice',()=>{const w=panel();expect(w.emitted()).toEqual({});expect(w.find('[data-action=cloud]').exists()).toBe(false);expect(w.find('[data-action=import]').exists()).toBe(false);expect(w.text()).toContain('не подключён');w.unmount()})
it('separates existing-file reattachment from copy/export and destructive decisions',async()=>{const w=panel(true);await w.get('[data-action=reattach]').trigger('click');expect(w.emitted('reattach')).toHaveLength(1);expect(w.emitted('decision')).toBeUndefined();await w.get('[data-action=copy]').trigger('click');expect(w.emitted('copy')).toHaveLength(1);w.unmount()})
it('previews local content and requires an explicit import/overwrite/unlink choice',async()=>{const w=panel(true);expect(w.text()).toContain('Local external manuscript');for(const c of ['compare','cloud','import','unlink'])await w.get(`[data-action=${c}]`).trigger('click');expect(w.emitted('decision')).toEqual([['compare'],['cloud'],['import'],['unlink']]);w.unmount()})
