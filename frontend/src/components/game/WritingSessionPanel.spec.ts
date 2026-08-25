import { createPinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { gameStateFixture } from '@/test/gameFixtures'

import WritingSessionPanel from './WritingSessionPanel.vue'

describe('WritingSessionPanel', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-08-15T12:00:00'))
  })

  afterEach(() => vi.useRealTimers())

  it('uses authoritative timestamps for the live countdown', async () => {
    const session = gameStateFixture().writing_session
    session.active = {
      started_at: '2026-08-15T12:00:00',
      ends_at: '2026-08-15T12:15:00',
      duration_minutes: 15,
      target_symbols: 1_000,
      progress: 300,
      intention: 'Написать новую сцену',
      mode: 'sprint',
      remaining_seconds: 900,
    }
    const wrapper = mount(WritingSessionPanel, {
      props: { session, busy: false },
      global: { plugins: [createPinia()] },
    })

    expect(wrapper.get('.session-clock').text()).toBe('15:00')
    await vi.advanceTimersByTimeAsync(1_000)
    expect(wrapper.get('.session-clock').text()).toBe('14:59')
    expect(wrapper.get('progress').attributes('value')).toBe('300')
  })

  it('finishes an active session once when its authoritative clock reaches zero', async () => {
    const session = gameStateFixture().writing_session
    session.active = {
      started_at: '2026-08-15T11:59:59',
      ends_at: '2026-08-15T12:00:01',
      duration_minutes: 15,
      target_symbols: 1_000,
      progress: 300,
      intention: 'Написать новую сцену',
      mode: 'sprint',
      remaining_seconds: 1,
    }
    const wrapper = mount(WritingSessionPanel, {
      props: { session, busy: false },
      global: { plugins: [createPinia()] },
    })

    await vi.advanceTimersByTimeAsync(1_000)
    await vi.advanceTimersByTimeAsync(2_000)

    expect(wrapper.emitted('finish')).toHaveLength(1)
  })

  it('emits only a validated editing-session command', async () => {
    const wrapper = mount(WritingSessionPanel, {
      props: { session: gameStateFixture().writing_session, busy: false },
      global: { plugins: [createPinia()] },
    })
    const selects = wrapper.findAll('select')
    await selects[0]?.setValue('editing')
    await wrapper.get('input[type="number"]').setValue('750')
    await wrapper.get('form').trigger('submit')

    expect(wrapper.emitted('start')?.[0]).toEqual([
      {
        duration_minutes: 25,
        target_symbols: 750,
        intention: 'Отредактировать текст',
        mode: 'editing',
      },
    ])
  })
})
