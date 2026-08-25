import { createPinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import type { Statistics } from '@/types/api'
import { projectFixture } from '@/test/fixtures'

import StatisticsWorkspace from './StatisticsWorkspace.vue'

const statistics: Statistics = {
  entity_id: 'project-1',
  unit: 'symbols',
  metrics: {
    entries_count: 2,
    total: 3_500,
    average_symbols_per_active_day: 1_750,
    average_symbols_per_entry: 1_750,
    average_entries_per_active_day: 1,
    freezes_used: 0,
    best_day: { date: '2026-08-15', symbols: 2_000, value: 2_000 },
    best_weekday: { weekday: 5, symbols: 2_000 },
    current_streak: 2,
    max_streak: 2,
    days_since_start: 10,
    active_days: 2,
    active_days_percent: 20,
  },
  timeline: [
    { date: '2026-08-14', value: 1_500, symbols: 1_500 },
    { date: '2026-08-15', value: 2_000, symbols: 2_000 },
  ],
}

describe('StatisticsWorkspace', () => {
  it('renders metrics, compact daily bars and an accessible growth chart', () => {
    const wrapper = mount(StatisticsWorkspace, {
      props: { statistics },
      global: { plugins: [createPinia()], stubs: { IonSpinner: true } },
    })

    expect(wrapper.findAll('.metric-card dd')[1]?.text().replace(/\D/g, '')).toBe('3500')
    expect(wrapper.find('table').exists()).toBe(false)
    expect(wrapper.findAll('.timeline-row')).toHaveLength(2)
    expect(wrapper.get('svg[role="img"]').attributes('aria-label')).toContain('График роста')
  })

  it('offers aggregate project statistics separately from stage statistics', async () => {
    const stage = projectFixture({ id: 'stage-1', name: 'Черновик' })
    const wrapper = mount(StatisticsWorkspace, {
      props: {
        statistics,
        project: projectFixture({ stages_enabled: true, stages: [stage] }),
        entityId: stage.id,
      },
      global: { plugins: [createPinia()], stubs: { IonSpinner: true } },
    })

    const select = wrapper.get('#statistics-entity')
    expect(select.findAll('option').map((option) => option.text())).toEqual([
      'Весь проект', 'Черновик',
    ])
    await select.setValue('')
    expect(wrapper.emitted('update:entityId')?.[0]).toEqual([''])
  })
})
