import { createPinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import { useLocaleStore } from '@/stores/locale'
import type { CustomAwardsState } from '@/types/game'

import CustomAwardsPanel from './CustomAwardsPanel.vue'

const awards: CustomAwardsState = {
  items: [{
    id: 'award-1', name: 'Прогулка', description: 'Награда',
    base_price: 40, apply_inflation: true, price: 58, sell_price: 43.5,
    count: 0, available_in_shop: true, sellable: true, usable: true, can_buy: true,
  }],
}

function mountPanel() {
  const pinia = createPinia()
  useLocaleStore(pinia).language = 'ru'
  return mount(CustomAwardsPanel, {
    props: { awards, busy: false },
    global: { plugins: [pinia] },
  })
}

describe('CustomAwardsPanel', () => {
  it('emits the base price and inflation opt-in when creating a reward', async () => {
    const wrapper = mountPanel()
    const fields = wrapper.findAll<HTMLInputElement>('.award-form input')
    await fields[0]?.setValue('Кофе')
    await fields[1]?.setValue(40)
    await fields[2]?.setValue(true)
    await wrapper.get('.award-form').trigger('submit')

    expect(wrapper.emitted('create')?.[0]).toEqual(['Кофе', 40, true])
  })

  it('keeps the displayed effective price separate from the editable base price', async () => {
    const wrapper = mountPanel()

    expect(wrapper.text()).toContain('58 монет')
    await wrapper.get('.nf-button--quiet').trigger('click')

    const fields = wrapper.findAll<HTMLInputElement>('.award-card input')
    expect(fields[0]?.element.value).toBe('Прогулка')
    expect(fields[1]?.element.value).toBe('40')
    expect(fields[2]?.element.checked).toBe(true)
  })
})
