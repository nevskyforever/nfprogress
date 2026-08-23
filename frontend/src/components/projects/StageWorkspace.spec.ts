import { createPinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { projectFixture } from '@/test/fixtures'

import StageWorkspace from './StageWorkspace.vue'

describe('StageWorkspace', () => {
  afterEach(() => vi.restoreAllMocks())

  it('exposes keyboard-friendly reorder commands with stable stage ids', async () => {
    const first = projectFixture({ id: 'stage-a', name: 'Первая глава', goal: 10_000 })
    const second = projectFixture({ id: 'stage-b', name: 'Вторая глава', goal: 10_000 })
    const wrapper = mount(StageWorkspace, {
      props: { project: projectFixture({ stages_enabled: true, stages: [first, second] }), busy: false },
      global: { plugins: [createPinia()], stubs: { IonIcon: true } },
    })

    await wrapper.get('button[aria-label*="Опустить этап"]').trigger('click')

    expect(wrapper.emitted('reorder')?.[0]?.[0]).toEqual(['stage-b', 'stage-a'])
  })

  it('confirms destructive stage deletion before emitting it', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const stage = projectFixture({ id: 'stage-a', name: 'Черновик' })
    const wrapper = mount(StageWorkspace, {
      props: { project: projectFixture({ stages_enabled: true, stages: [stage] }), busy: false },
      global: { plugins: [createPinia()], stubs: { IonIcon: true } },
    })

    const removeButton = wrapper.findAll('button').find((button) => button.text().includes('Удалить'))
    await removeButton?.trigger('click')

    expect(window.confirm).toHaveBeenCalled()
    expect(wrapper.emitted('remove')?.[0]?.[0]).toEqual(stage)
  })

  it('does not offer completion for an infinite stage', () => {
    const stage = projectFixture({ id: 'stage-a', infinite: true, goal: null })
    const wrapper = mount(StageWorkspace, {
      props: { project: projectFixture({ stages_enabled: true, stages: [stage] }), busy: false },
      global: { plugins: [createPinia()], stubs: { IonIcon: true } },
    })

    const completeButton = wrapper.findAll('button').find((button) => button.text().includes('Завершить'))
    const shareButton = wrapper.findAll('button').find((button) => button.text().includes('Поделиться'))
    expect(completeButton?.attributes('disabled')).toBeDefined()
    expect(shareButton?.attributes('disabled')).toBeDefined()
  })

  it('emits a share request for a finite stage without duplicating image logic', async () => {
    const stage = projectFixture({ id: 'stage-a', name: 'Черновик', goal: 10_000 })
    const wrapper = mount(StageWorkspace, {
      props: { project: projectFixture({ stages_enabled: true, stages: [stage] }), busy: false },
      global: { plugins: [createPinia()], stubs: { IonIcon: true } },
    })

    const shareButton = wrapper.findAll('.stage-action-button').find((button) => button.text().includes('Поделиться'))
    await shareButton?.trigger('click')

    expect(wrapper.emitted('share')?.[0]?.[0]).toEqual(stage)
  })

  it('protects shared-project sources from edit and deletion', () => {
    const stage = projectFixture({ id: 'source-a', infinite: true, goal: null })
    const wrapper = mount(StageWorkspace, {
      props: {
        project: projectFixture({
          name: 'Общий проект',
          infinite: true,
          goal: null,
          stages_enabled: true,
          stages: [stage],
        }),
        busy: false,
      },
      global: { plugins: [createPinia()], stubs: { IonIcon: true } },
    })

    const protectedButtons = wrapper.findAll('.stage-action-button')
    expect(protectedButtons.every((button) => button.attributes('disabled') !== undefined)).toBe(true)
  })
})
