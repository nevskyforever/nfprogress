import { createPinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import CabinetPanel from './CabinetPanel.vue'

describe('CabinetPanel', () => {
  it('renders the complete legacy relic set and migrated locked state', () => {
    const wrapper = mount(CabinetPanel, {
      props: {
        manuscripts: {
          journeys: [],
          milestones: [],
          cabinet: {
            relics: [
              { key: 'ink_candle', unlocked: true, name: 'Чернильная свеча', description: 'Первая работа.', condition: '10%', progress: 1, required: 1, effect_type: 'writing', bonus: 0.01, effect_description: '+1%' },
              { key: 'plot_map', unlocked: false, name: null, description: null, condition: 'Достигните рубежа 50% в одном тексте.', progress: 0, required: 1, effect_type: null, bonus: null, effect_description: null },
            ],
            sets: [],
          },
        },
      },
      global: { plugins: [createPinia()] },
    })

    expect(wrapper.text()).toContain('Чернильная свеча')
    expect(wrapper.text()).toContain('Первая работа.')
    expect(wrapper.text()).toContain('Достигните рубежа 50% в одном тексте.')
    expect(wrapper.text()).toContain('Неизвестная реликвия')
  })
})
