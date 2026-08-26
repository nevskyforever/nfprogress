import { createPinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import ProjectCreateDialog from './ProjectCreateDialog.vue'

const ionicStubs = {
  IonModal: { template: '<div><slot /></div>' },
  IonHeader: { template: '<header><slot /></header>' },
  IonContent: { template: '<main><slot /></main>' },
  IonIcon: true,
  IonSpinner: true,
}

describe('ProjectCreateDialog', () => {
  afterEach(() => vi.useRealTimers())

  it('calculates the daily goal and deadline as the planning fields change', async () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-08-26T12:00:00'))
    const wrapper = mount(ProjectCreateDialog, {
      props: { open: true }, global: { plugins: [createPinia()], stubs: ionicStubs },
    })

    await wrapper.get('#project-goal').setValue('1000')
    await wrapper.get('#project-total').setValue('100')
    await wrapper.get('input[name="no_deadline"]').setValue(false)
    await wrapper.get('#project-deadline').setValue('2026-08-28')
    expect((wrapper.get('#project-personal-goal').element as HTMLInputElement).value).toBe('300')

    await wrapper.get('#project-personal-goal').setValue('225')
    expect((wrapper.get('#project-deadline').element as HTMLInputElement).value).toBe('2026-08-29')
  })

  it('uses the legacy no-deadline checkbox to disable the daily plan', async () => {
    const wrapper = mount(ProjectCreateDialog, {
      props: { open: true }, global: { plugins: [createPinia()], stubs: ionicStubs },
    })

    expect((wrapper.get('#project-deadline').element as HTMLInputElement).disabled).toBe(true)
    await wrapper.get('input[name="no_deadline"]').setValue(false)
    expect((wrapper.get('#project-deadline').element as HTMLInputElement).disabled).toBe(false)
  })
  it('emits a typed finite-project payload from the form', async () => {
    const wrapper = mount(ProjectCreateDialog, {
      props: { open: true },
      global: { plugins: [createPinia()], stubs: ionicStubs },
    })

    await wrapper.get('#project-name').setValue('Новая книга')
    await wrapper.get('#project-goal').setValue('75000')
    await wrapper.get('#project-total').setValue('1200')
    await wrapper.get('form').trigger('submit')

    const submitEvents = wrapper.emitted('submit')
    expect(submitEvents).toHaveLength(1)
    expect(submitEvents?.[0]?.[0]).toMatchObject({
      name: 'Новая книга',
      goal: 75_000,
      total: 1_200,
      unit: 'symbols',
      infinite: false,
    })
  })

  it('keeps the dialog open and announces local validation errors', async () => {
    const wrapper = mount(ProjectCreateDialog, {
      props: { open: true },
      global: { plugins: [createPinia()], stubs: ionicStubs },
    })

    await wrapper.get('#project-name').setValue('   ')
    await wrapper.get('form').trigger('submit')

    expect(wrapper.emitted('submit')).toBeUndefined()
    expect(wrapper.get('[role="alert"]').text()).toContain('Введите название проекта')
  })

  it('can request a data-preserving initial stage conversion', async () => {
    const wrapper = mount(ProjectCreateDialog, {
      props: { open: true },
      global: { plugins: [createPinia()], stubs: ionicStubs },
    })

    await wrapper.get('#project-name').setValue('Роман')
    await wrapper.get('input[name="stages_enabled"]').setValue(true)
    await wrapper.get('form').trigger('submit')

    expect(wrapper.emitted('submit')?.[0]?.[0]).toMatchObject({
      name: 'Роман',
      stages_enabled: true,
    })
  })
})
