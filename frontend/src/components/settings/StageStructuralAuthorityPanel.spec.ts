import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { describe, expect, it, vi } from 'vitest'
import { useCloudSessionStore } from '@/stores/cloudSession'
import StageStructuralAuthorityPanel from './StageStructuralAuthorityPanel.vue'
import fixture from '@/cloud/__fixtures__/stageCodecV1.json'
import type { StructuralEvent } from '@/cloud/stageCodec'
import type { StructuralView } from '@/infrastructure/sqlite/stageStructuralRepository'
function setup(state: StructuralView['state']) {
  const pinia = createPinia(); setActivePinia(pinia); const cloud = useCloudSessionStore()
  cloud.metadataTransportMode = 3
  const branch = structuredClone(fixture.event) as StructuralEvent
  const entity = { entity_type: 'stage' as const, entity_id: 'S1', local: branch.stage!, tips: ['z', 'a'], branches: [branch], conflict: state === 'conflict' }
  cloud.structuralAuthority.project = { state, blockers: [], entities: [entity], order: ['S1'], migration_id: null }
  const inspect = vi.spyOn(cloud, 'inspectStructure').mockResolvedValue(), begin = vi.spyOn(cloud, 'beginStructure').mockResolvedValue(), decide = vi.spyOn(cloud, 'decideStructure').mockResolvedValue()
  const wrapper = mount(StageStructuralAuthorityPanel, { props: { projectId: 'project' }, global: { plugins: [pinia] } })
  return { cloud, wrapper, inspect, begin, decide, branch, entity }
}
async function click(h: ReturnType<typeof setup>, label: string) {
  await h.wrapper.findAll('button').find(button => button.text() === label)!.trigger('click'); await flushPromises()
}
describe('explicit Stage authority panel', () => {
  it.each(['structural_local', 'candidate_captured', 'publication_pending', 'published_self_echo_pending', 'active', 'conflict', 'blocked'] as const)('shows %s without beginning on open', state => {
    const h = setup(state); expect(h.wrapper.attributes('data-structural-state')).toBe(state)
    expect(h.begin).not.toHaveBeenCalled(); expect(h.decide).not.toHaveBeenCalled(); expect(h.inspect).not.toHaveBeenCalled(); h.wrapper.unmount()
  })
  it('begins only through an explicit click', async () => {
    const h = setup('structural_local'); await click(h, 'Отправить этапы этого устройства'); expect(h.begin).toHaveBeenCalledWith('project'); h.wrapper.unmount()
  })
  it('submits the full sorted tip set and exact local snapshot', async () => {
    const h = setup('conflict'); await click(h, 'Выбрать этот вариант')
    expect(h.decide).toHaveBeenCalledWith('project', { entity_type: 'stage', entity_id: 'S1', expected_tips: ['a', 'z'], expected_local: h.entity.local, proposed: null, selected_event_id: h.branch.header.event_id }); h.wrapper.unmount()
  })
  it('distinguishes selected causal deletion from physical cleanup', () => {
    const h = setup('blocked')
    h.cloud.structuralAuthority.project!.entities[0]!.causal_tombstone_selected = true
    return flushPromises().then(() => {
      expect(h.wrapper.text()).toContain('Удаление этапа выбрано. Физическое удаление пока заблокировано; дочерние данные сохранены.')
      expect(h.wrapper.text()).not.toContain('Выбрать этот вариант')
      h.wrapper.unmount()
    })
  })
  it('retains a failed retry visibly and safely retries', async () => {
    const h = setup('blocked'), retry = vi.spyOn(h.cloud, 'retry').mockRejectedValueOnce(new Error('blocked')).mockResolvedValue()
    await click(h, 'Безопасно продолжить'); expect(h.wrapper.find('[role="alert"]').exists()).toBe(true)
    await click(h, 'Безопасно продолжить'); expect(retry).toHaveBeenCalledTimes(2); expect(h.inspect).toHaveBeenCalledWith('project'); expect(h.wrapper.find('[role="alert"]').exists()).toBe(false); h.wrapper.unmount()
  })
})
