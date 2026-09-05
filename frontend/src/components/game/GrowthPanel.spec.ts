import { createPinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import { gameStateFixture } from '@/test/gameFixtures'

import GrowthPanel from './GrowthPanel.vue'

describe('GrowthPanel', () => {
  it('renders the specialization section from migrated definitions', async () => {
    const state = gameStateFixture()
    const wrapper = mount(GrowthPanel, {
      props: {
        inspiration: state.inspiration,
        inspirationPoints: state.profile.inspiration,
        specializations: {
          selected: 'ritualist',
          unlocks_at_level: 3,
          change_cooldown_days: 14,
          change_days_remaining: 0,
          mastery_thresholds: [0, 3, 8, 15, 25],
          items: [
            {
              key: 'ritualist',
              name: 'Ритуалист',
              description: 'Даёт +25% к награде за успешную писательскую сессию.',
              selected: true,
              mastery_experience: 8,
              mastery_rank: 2,
              passive_bonus: 0.3,
              ability: {
                name: 'Сила ритуала',
                description: 'Даёт +30% к следующей успешной сессии.',
                cooldown_hours: 24,
                remaining_seconds: 0,
                pending: false,
              },
            },
          ],
        },
        skills: state.skills,
        quests: state.quests,
        level: 40,
        busy: false,
      },
      global: { plugins: [createPinia()] },
    })

    await wrapper.find('button[role="tab"]:nth-child(2)').trigger('click')
    expect(wrapper.text()).toContain('Ритуалист')
    expect(wrapper.text()).toContain('Даёт +25% к награде за успешную писательскую сессию.')
    expect(wrapper.text()).toContain('Сила ритуала')
  })
})
