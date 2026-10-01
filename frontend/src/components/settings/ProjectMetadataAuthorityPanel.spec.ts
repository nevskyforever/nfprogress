import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { describe, expect, it, vi } from 'vitest'
import { useCloudSessionStore } from '@/stores/cloudSession'
import type { MetadataAuthorityView } from '@/infrastructure/sqlite/projectMetadataMigrationRepository'
import ProjectMetadataAuthorityPanel from './ProjectMetadataAuthorityPanel.vue'

const local = { name: 'Private local', goal: null, infinite: true, unit: 'symbols', deadline: null,
  status: 'active', personal_goal: 100, auto_freeze: true, streak_enabled: true,
  work_method: 'manual', stages_enabled: false, combine_stage_mindmaps: false }
function setup(state: MetadataAuthorityView['state'], branches = [{ event_id: 'first', revision: 1, operation: 'create', metadata: { ...local, name: 'Cloud' } }]) {
  const pinia = createPinia(); setActivePinia(pinia)
  const cloud = useCloudSessionStore()
  cloud.metadataTransportMode = 3
  cloud.metadataAuthority.project = { state, local, authenticated: branches.length === 1 ? branches[0]!.metadata : null,
    head_event_id: branches.length === 1 ? branches[0]!.event_id : null, branches, pending_event_id: null, blockers: [] }
  const inspect = vi.spyOn(cloud, 'inspectProjectMetadata').mockResolvedValue()
  const begin = vi.spyOn(cloud, 'beginMetadataMigration').mockResolvedValue()
  const adopt = vi.spyOn(cloud, 'adoptMetadata').mockResolvedValue()
  const decide = vi.spyOn(cloud, 'decideMetadata').mockResolvedValue()
  const wrapper = mount(ProjectMetadataAuthorityPanel, { props: { projectId: 'project' }, global: { plugins: [pinia] } })
  return { cloud, wrapper, inspect, begin, adopt, decide }
}
async function click(wrapper: ReturnType<typeof setup>['wrapper'], text: string) {
  const button = wrapper.findAll('button').find(button => button.text() === text)
  expect(button).toBeDefined(); await button!.trigger('click'); await flushPromises()
}
describe('project metadata explicit authority panel', () => {
  it.each(['local_legacy_only', 'local_candidate_ready', 'local_matches_authenticated', 'local_differs_from_authenticated',
    'genesis_conflict', 'metadata_conflict', 'resolution_pending', 'active', 'blocked'] as const)('exposes %s without making a decision on open', state => {
    const h = setup(state)
    expect(h.wrapper.attributes('data-metadata-state')).toBe(state)
    expect(h.inspect).not.toHaveBeenCalled(); expect(h.begin).not.toHaveBeenCalled()
    expect(h.adopt).not.toHaveBeenCalled(); expect(h.decide).not.toHaveBeenCalled()
    h.wrapper.unmount()
  })
  it('publishes only after an explicit click and shows the local values', async () => {
    const h = setup('local_legacy_only', [])
    expect(h.wrapper.text()).toContain('Private local')
    await click(h.wrapper, 'Опубликовать локальные метаданные')
    expect(h.begin).toHaveBeenCalledWith('project')
    h.wrapper.unmount()
  })
  it('adopts an existing head without publishing an update', async () => {
    const h = setup('local_differs_from_authenticated')
    await click(h.wrapper, 'Использовать облачную версию')
    expect(h.adopt).toHaveBeenCalledWith('project', 'first', local)
    expect(h.decide).not.toHaveBeenCalled(); h.wrapper.unmount()
  })
  it('preserves all branch identities in the explicit resolution request', async () => {
    const h = setup('genesis_conflict', [
      { event_id: 'second', revision: 1, operation: 'create', metadata: { ...local, name: 'Gamma' } },
      { event_id: 'first', revision: 1, operation: 'create', metadata: { ...local, name: 'Beta' } },
    ])
    expect(h.wrapper.text()).toContain('Beta'); expect(h.wrapper.text()).toContain('Gamma')
    await click(h.wrapper, 'Использовать эту версию для согласования')
    expect(h.decide).toHaveBeenCalledWith('project', 'choose_branch', 'second', null, local, ['first', 'second'])
    h.wrapper.unmount()
  })
  it('offers a bounded editor for all twelve portable fields', async () => {
    const h = setup('local_differs_from_authenticated')
    await click(h.wrapper, 'Редактировать результат')
    expect(h.wrapper.findAll('form input, form select')).toHaveLength(12)
    await h.wrapper.find('form input').setValue('Merged')
    await h.wrapper.find('form').trigger('submit'); await flushPromises()
    expect(h.decide).toHaveBeenCalledWith('project', 'manual', null, { ...local, name: 'Merged' }, local, ['first'])
    h.wrapper.unmount()
  })
})
