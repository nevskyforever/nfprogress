import { createPinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import { projectFixture } from '@/test/fixtures'

import StageDialog from './StageDialog.vue'

const ionicStubs = {
  IonModal: { template: '<div><slot /></div>' },
  IonHeader: { template: '<header><slot /></header>' },
  IonContent: { template: '<main><slot /></main>' },
  IonIcon: true,
  IonSpinner: true,
}

describe('StageDialog', () => {
  it('carries an edited current value without implicitly recalculating the plan', async () => {
    const wrapper = mount(StageDialog, {
      props: {
        open: true,
        projectUnit: 'symbols',
        stage: projectFixture({ id: 'stage-1', total: 200 }),
      },
      global: { plugins: [createPinia()], stubs: ionicStubs },
    })

    await wrapper.get('#stage-total').setValue('350')
    await wrapper.get('form').trigger('submit')

    expect(wrapper.emitted('submit')?.[0]?.[0]).toMatchObject({ total: 350 })
    expect(wrapper.emitted('submit')?.[0]?.[0]).not.toHaveProperty('recalculate_plan')
  })

  it('creates a shared-project source as an infinite zero-baseline stage', async () => {
    const wrapper = mount(StageDialog, {
      props: { open: true, projectUnit: 'symbols', sharedSource: true },
      global: { plugins: [createPinia()], stubs: ionicStubs },
    })

    await wrapper.get('#stage-name').setValue('Рукопись')
    await wrapper.get('form').trigger('submit')

    expect(wrapper.emitted('submit')?.[0]?.[0]).toMatchObject({
      name: 'Рукопись', infinite: true, total: 0,
    })
  })
})
