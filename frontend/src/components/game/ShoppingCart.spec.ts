import { createPinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import type { GameItem } from '@/types/game'
import ShoppingCart from './ShoppingCart.vue'

const item: GameItem = {
  id: 'Предметы:test', key: 'test', category: 'Предметы', name: 'test', description: '', count: 0,
  sellable: false, usable: false, buy: true, maximum_quantity: 1, price: 10,
}

describe('ShoppingCart', () => {
  it('disables increment at the inventory-aware maximum', async () => {
    const wrapper = mount(ShoppingCart, {
      props: {
        lines: [{ item, count: 1, maximumCount: 1 }],
        coins: 100,
        canOpenCredit: false,
        creditAllowed: true,
        busy: false,
      },
      global: { plugins: [createPinia()] },
    })

    const increment = wrapper.findAll('li button').find((button) => button.text() === '+')
    expect(increment?.attributes('disabled')).toBeDefined()
    await increment?.trigger('click')
    expect(wrapper.emitted('change')).toBeUndefined()
  })
})
