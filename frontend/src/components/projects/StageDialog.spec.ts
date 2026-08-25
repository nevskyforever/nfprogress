import { createPinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

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
  afterEach(() => vi.useRealTimers())

  it('keeps deadline and daily goal calculations live for a stage', async () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-08-26T12:00:00'))
    const wrapper = mount(StageDialog, {
      props: { open: true, projectUnit: 'symbols' },
      global: { plugins: [createPinia()], stubs: ionicStubs },
    })

    await wrapper.get('#stage-goal').setValue('1000')
    await wrapper.get('#stage-total').setValue('100')
    await wrapper.get('#stage-deadline').setValue('2026-08-28')
    expect((wrapper.get('#stage-personal-goal').element as HTMLInputElement).value).toBe('300')
  })
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
