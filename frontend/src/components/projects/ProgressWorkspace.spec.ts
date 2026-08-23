import { createPinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import { projectFixture } from '@/test/fixtures'

import ProgressWorkspace from './ProgressWorkspace.vue'

const ionicStubs = {
  IonIcon: true,
  IonSpinner: true,
}

describe('ProgressWorkspace', () => {
  it('sends a new authoritative total for the selected stage', async () => {
    const stage = projectFixture({ id: 'stage-1', name: 'Глава 1', total: 1_000 })
    const wrapper = mount(ProgressWorkspace, {
      props: {
        project: projectFixture({ stages_enabled: true, stages: [stage] }),
        modelValue: stage.id,
        busy: false,
      },
      global: { plugins: [createPinia()], stubs: ionicStubs },
    })

    await wrapper.get('#progress-new-total').setValue('1750')
    await wrapper.get('form').trigger('submit')

    expect(wrapper.emitted('record')?.[0]?.[0]).toEqual({
      new_total: 1_750,
      stage_id: 'stage-1',
    })
    expect(wrapper.get('.progress-entry-form h3').text()).toContain('Новая запись')
    expect(wrapper.get('.progress-entry-form #progress-entity').element.tagName).toBe('SELECT')
  })

  it('announces unchanged totals instead of calling the API boundary', async () => {
    const project = projectFixture({ total: 1_000 })
    const wrapper = mount(ProgressWorkspace, {
      props: { project, busy: false },
      global: { plugins: [createPinia()], stubs: ionicStubs },
    })

    await wrapper.get('form').trigger('submit')

    expect(wrapper.emitted('record')).toBeUndefined()
    expect(wrapper.get('[role="alert"]').text()).toContain('отличающееся от текущего')
  })

  it('blocks manual input for a synchronized stage but keeps stage selection available', () => {
    const stage = projectFixture({ id: 'stage-1', name: 'Глава 1', total: 1_000 })
    const wrapper = mount(ProgressWorkspace, {
      props: {
        project: projectFixture({ stages_enabled: true, stages: [stage] }),
        modelValue: stage.id,
        busy: false,
        syncs: [{
          project_id: 'f184de493a344752898ea43f2988dddb',
          stage_id: stage.id,
          configured: true,
          type: 'word',
          path: null,
          item_id: null,
          last_synced_at: null,
          desktop_only: true,
        }],
      },
      global: { plugins: [createPinia()], stubs: ionicStubs },
    })

    expect(wrapper.get('#progress-new-total').attributes('disabled')).toBeDefined()
    expect(wrapper.get('button[type="submit"]').attributes('disabled')).toBeDefined()
    expect(wrapper.get('#progress-entity').attributes('disabled')).toBeUndefined()
    expect(wrapper.get('.read-only-note').text()).toContain('Включена синхронизация')
  })
})
