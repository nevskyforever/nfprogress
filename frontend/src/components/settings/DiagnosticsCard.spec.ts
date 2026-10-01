import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { diagnostics } from '@/diagnostics/service'
import DiagnosticsCard from './DiagnosticsCard.vue'
import FriendlyStatus from './FriendlyStatus.vue'
vi.mock('@/diagnostics/service',()=>({diagnostics:{stats:vi.fn(),copy:vi.fn(),export:vi.fn(),clear:vi.fn()}}))
beforeEach(()=>{
  vi.mocked(diagnostics.stats).mockResolvedValue({write_failed:false,count:5,bytes:2048,last_event_at:'2026-10-02T10:00:00.000Z'})
  vi.mocked(diagnostics.copy).mockReset();vi.mocked(diagnostics.export).mockReset();vi.mocked(diagnostics.clear).mockReset()
})
function setup(){return mount(DiagnosticsCard,{global:{plugins:[createPinia()]}})}
async function click(w:ReturnType<typeof setup>,label:string){await w.findAll('button').find(b=>b.text()===label)!.trigger('click');await flushPromises()}
describe('local diagnostics support workflow',()=>{
  it('shows safe size/time/privacy and only copies, exports, clears on explicit action',async()=>{
    const w=setup();await flushPromises();expect(w.text()).toContain('Событий: 5');expect(w.text()).toContain('2 КБ');expect(w.text()).toContain('2026-10-02');expect(w.text()).toContain('Автоматической отправки нет')
    expect(diagnostics.copy).not.toHaveBeenCalled();expect(diagnostics.export).not.toHaveBeenCalled();expect(diagnostics.clear).not.toHaveBeenCalled()
    await click(w,'Скопировать журнал');expect(diagnostics.copy).toHaveBeenCalledOnce();expect(w.text()).toContain('Журнал скопирован')
    vi.mocked(diagnostics.export).mockResolvedValue(true);await click(w,'Экспортировать журнал');expect(w.text()).toContain('Журнал экспортирован')
    vi.mocked(diagnostics.stats).mockResolvedValue({write_failed:false,count:0,bytes:0,last_event_at:null});await click(w,'Очистить журнал');expect(diagnostics.clear).toHaveBeenCalledOnce();expect(w.text()).toContain('Событий: 0');w.unmount()
  })
  it('treats export cancellation silently and hides arbitrary storage errors',async()=>{
    const w=setup();await flushPromises();vi.mocked(diagnostics.export).mockResolvedValue(false);await click(w,'Экспортировать журнал');expect(w.find('[role="status"]').exists()).toBe(false)
    vi.mocked(diagnostics.copy).mockRejectedValue(new Error('SECRET_TOKEN_PATH'));await click(w,'Скопировать журнал');expect(w.text()).toContain('Не удалось завершить действие');expect(w.text()).not.toContain('SECRET_TOKEN_PATH');w.unmount()
  })
  it('reports a failed append even when retained history can still be read and copied', async () => {
    vi.mocked(diagnostics.stats).mockResolvedValue({write_failed:true,count:5,bytes:2048,last_event_at:null})
    const w=setup();await flushPromises();expect(w.text()).toContain('diagnostic_storage_unavailable')
    await click(w,'Скопировать журнал');expect(diagnostics.copy).toHaveBeenCalledOnce();expect(w.text()).toContain('diagnostic_storage_unavailable')
    vi.mocked(diagnostics.stats).mockResolvedValue({write_failed:false,count:0,bytes:0,last_event_at:null})
    await click(w,'Очистить журнал');expect(w.text()).not.toContain('diagnostic_storage_unavailable');w.unmount()
  })
  it('keeps codes in initially collapsed technical details, never a primary title',()=>{
    const w=mount(FriendlyStatus,{props:{domain:'error',code:'stale_structural_resolution:secret-entity'},global:{plugins:[createPinia()]}})
    expect(w.find('details').attributes('open')).toBeUndefined();expect(w.find('strong').text()).toBe('Во время выбора появились новые изменения');expect(w.find('details').text()).toContain('stale_structural_resolution');expect(w.text()).not.toContain('secret-entity');expect(w.find('pre').exists()).toBe(false);w.unmount()
  })
})
