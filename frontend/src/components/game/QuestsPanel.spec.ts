import { createPinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import type { GameQuests } from '@/types/game'

import QuestsPanel from './QuestsPanel.vue'

const quests: GameQuests = {
  items: [
    {
      id: 'high',
      name: 'Высокий квест',
      description: 'Описание',
      status: 'available',
      required_level: 8,
      started_at: null,
      finished_at: null,
      reward: { coins: 10, experience: 20, items: [], buffs: [] },
    },
    {
      id: 'done',
      name: 'Завершённый квест',
      description: 'Описание',
      status: 'completed',
      required_level: 1,
      started_at: null,
      finished_at: null,
      reward: { coins: 10, experience: 20, items: [], buffs: [] },
    },
    {
      id: 'low',
      name: 'Низкий квест',
      description: 'Описание',
      status: 'available',
      required_level: 2,
      started_at: null,
      finished_at: null,
      reward: { coins: 10, experience: 20, items: [], buffs: [] },
    },
  ],
  by_status: {},
}

describe('QuestsPanel', () => {
  it('hides completed quests by default and sorts visible quests by ascending level', async () => {
    const wrapper = mount(QuestsPanel, {
      props: { quests, level: 10, busy: false },
      global: { plugins: [createPinia()] },
    })

    expect((wrapper.get('input[type="checkbox"]').element as HTMLInputElement).checked).toBe(true)
    expect(wrapper.findAll('h3').map((item) => item.text())).toEqual(['Низкий квест', 'Высокий квест'])

    await wrapper.get('input[type="checkbox"]').setValue(false)
    expect(wrapper.findAll('h3')).toHaveLength(3)

    await wrapper.get('select').setValue('desc')
    expect(wrapper.findAll('h3').map((item) => item.text())).toEqual([
      'Высокий квест',
      'Низкий квест',
      'Завершённый квест',
    ])
  })
})
