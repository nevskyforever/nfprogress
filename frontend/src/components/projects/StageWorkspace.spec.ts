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
    const shareButton = wrapper.find('.progress-share-menu button')
    expect(completeButton?.attributes('disabled')).toBeDefined()
    expect(shareButton?.attributes('disabled')).toBeDefined()
  })

  it('emits a copy request for a finite stage without duplicating image logic', async () => {
    const stage = projectFixture({ id: 'stage-a', name: 'Черновик', goal: 10_000 })
    const wrapper = mount(StageWorkspace, {
      props: { project: projectFixture({ stages_enabled: true, stages: [stage] }), busy: false },
      global: { plugins: [createPinia()], stubs: { IonIcon: true } },
    })

    const shareButton = wrapper.find('.progress-share-menu button')
    await shareButton?.trigger('click')
    await wrapper.get('button[aria-label="Скопировать картинку прогресса"]').trigger('click')

    expect(wrapper.emitted('copy')?.[0]?.[0]).toEqual(stage)
  })

  it('opens a stage from its progress tile', async () => {
    const stage = projectFixture({ id: 'stage-a', name: 'Черновик', goal: 10_000 })
    const wrapper = mount(StageWorkspace, {
      props: { project: projectFixture({ stages_enabled: true, stages: [stage] }), busy: false },
      global: { plugins: [createPinia()], stubs: { IonIcon: true } },
    })

    await wrapper.get('button[aria-label="Этапы: Черновик"]').trigger('click')

    expect(wrapper.emitted('open')?.[0]?.[0]).toEqual(stage)
    expect(wrapper.find('.progress-ring').exists()).toBe(true)
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

  it('allows adding another synchronization source to the shared project', async () => {
    const wrapper = mount(StageWorkspace, {
      props: {
        project: projectFixture({
          name: 'Общий проект',
          infinite: true,
          goal: null,
          stages_enabled: true,
        }),
        busy: false,
      },
      global: { plugins: [createPinia()], stubs: { IonIcon: true } },
    })

    const addButton = wrapper.get('button.nf-button--secondary')
    expect(addButton.text()).toContain('Добавить источник')

    await addButton.trigger('click')

    expect(wrapper.emitted('add')).toHaveLength(1)
  })

  it('shows stage streaks only when stages own the legacy streak plan', () => {
    const stage = projectFixture({
      id: 'stage-a',
      deadline: '2027-05-10',
      streak_length: 3,
      streak_status: 'Active',
    })
    const wrapper = mount(StageWorkspace, {
      props: {
        project: projectFixture({
          deadline: null,
          stages_enabled: true,
          stages: [stage],
        }),
        busy: false,
        streaksEnabled: true,
      },
      global: { plugins: [createPinia()], stubs: { IonIcon: true } },
    })

    expect(wrapper.get('.stage-streak').attributes('aria-label')).toContain('Стрик этапа')
    expect(wrapper.get('.stage-streak').attributes('aria-label')).toContain('3 дн.')
  })
})
