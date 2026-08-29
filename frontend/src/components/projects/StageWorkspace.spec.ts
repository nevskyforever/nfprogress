import { createPinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { projectFixture } from '@/test/fixtures'

import StageWorkspace from './StageWorkspace.vue'

describe('StageWorkspace', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    document.body.innerHTML = ''
  })

  it('reorders stages by dragging stable stage ids', async () => {
    const first = projectFixture({ id: 'stage-a', name: 'Первая глава', goal: 10_000 })
    const second = projectFixture({ id: 'stage-b', name: 'Вторая глава', goal: 10_000 })
    const wrapper = mount(StageWorkspace, {
      props: { project: projectFixture({ stages_enabled: true, stages: [first, second] }), busy: false },
      global: { plugins: [createPinia()], stubs: { IonIcon: true } },
    })

    const cards = wrapper.findAll('.stage-card')
    const data = new Map<string, string>()
    const dataTransfer = {
      effectAllowed: '',
      setData: (type: string, value: string) => data.set(type, value),
      getData: (type: string) => data.get(type) ?? '',
    }
    await cards[0]?.trigger('dragstart', { dataTransfer })
    await cards[1]?.trigger('drop', { dataTransfer })

    expect(wrapper.emitted('reorder')?.[0]?.[0]).toEqual(['stage-b', 'stage-a'])
    expect(data.get('application/x-nfprogress-stage-id')).toBe('stage-a')
  })

  it('confirms destructive stage deletion before emitting it', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const stage = projectFixture({ id: 'stage-a', name: 'Черновик' })
    const wrapper = mount(StageWorkspace, {
      props: { project: projectFixture({ stages_enabled: true, stages: [stage] }), busy: false },
      global: { plugins: [createPinia()], stubs: { IonIcon: true } },
    })

    await wrapper.get('.stage-card').trigger('contextmenu')
    await wrapper.vm.$nextTick()
    const contextRemove = [...document.body.querySelectorAll<HTMLButtonElement>('.context-action-menu button')]
      .find((button) => button.textContent?.includes('Удалить'))
    contextRemove?.click()

    expect(window.confirm).toHaveBeenCalled()
    expect(wrapper.emitted('remove')?.[0]?.[0]).toEqual(stage)
  })

  it('does not offer completion for an infinite stage', async () => {
    const stage = projectFixture({ id: 'stage-a', infinite: true, goal: null })
    const wrapper = mount(StageWorkspace, {
      props: { project: projectFixture({ stages_enabled: true, stages: [stage] }), busy: false },
      global: { plugins: [createPinia()], stubs: { IonIcon: true } },
    })

    await wrapper.get('.stage-card').trigger('contextmenu')
    await wrapper.vm.$nextTick()
    const completeButton = [...document.body.querySelectorAll<HTMLButtonElement>('.context-action-menu button')]
      .find((button) => button.textContent?.includes('Завершить'))
    const shareButton = wrapper.find('.progress-share-menu button')
    expect(completeButton).toBeUndefined()
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

  it('protects shared-project sources from edit while allowing deletion', async () => {
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

    vi.spyOn(window, 'confirm').mockReturnValue(true)
    await wrapper.get('.stage-card').trigger('contextmenu')
    await wrapper.vm.$nextTick()
    const menuButtons = [...document.body.querySelectorAll<HTMLButtonElement>('.context-action-menu button')]
    expect(menuButtons.some((button) => button.textContent?.includes('Изменить'))).toBe(false)
    const removeButton = menuButtons.find((button) => button.textContent?.includes('Удалить'))
    removeButton?.click()
    expect(wrapper.emitted('remove')?.[0]?.[0]).toEqual(stage)
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
