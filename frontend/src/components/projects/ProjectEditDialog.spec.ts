import { createPinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { projectFixture } from '@/test/fixtures'

import ProjectEditDialog from './ProjectEditDialog.vue'

const ionicStubs = {
  IonModal: { template: '<div><slot /></div>' },
  IonHeader: { template: '<header><slot /></header>' },
  IonContent: { template: '<main><slot /></main>' },
  IonIcon: true,
  IonSpinner: true,
}

describe('ProjectEditDialog', () => {
  afterEach(() => vi.restoreAllMocks())

  it('updates the current value without forcing a daily-plan reset', async () => {
    const wrapper = mount(ProjectEditDialog, {
      props: { open: true, project: projectFixture({ total: 1_200 }) },
      global: { plugins: [createPinia()], stubs: ionicStubs },
    })

    await wrapper.get('#edit-project-total').setValue('1500')
    await wrapper.get('form').trigger('submit')

    expect(wrapper.emitted('submit')?.[0]?.[0]).toMatchObject({ total: 1_500 })
    expect(wrapper.emitted('submit')?.[0]?.[0]).not.toHaveProperty('recalculate_plan')
  })

  it('confirms and requests the preserving stages-to-single conversion', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const stage = projectFixture({ id: 'stage-1', name: 'Черновик' })
    const wrapper = mount(ProjectEditDialog, {
      props: {
        open: true,
        project: projectFixture({ stages_enabled: true, stages: [stage] }),
      },
      global: { plugins: [createPinia()], stubs: ionicStubs },
    })

    const stagesToggle = wrapper.findAll('label').find((item) => item.text().includes('Проект с этапами'))
    await stagesToggle?.get('input').setValue(false)
    await wrapper.get('form').trigger('submit')

    expect(window.confirm).toHaveBeenCalledOnce()
    expect(wrapper.emitted('submit')?.[0]?.[0]).toMatchObject({ stages_enabled: false })
  })
})
