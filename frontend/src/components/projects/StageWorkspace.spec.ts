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
})
