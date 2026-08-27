import { createPinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import type { GameInventory, ShopCatalog } from '@/types/game'

import InventoryShopPanel from './InventoryShopPanel.vue'

const inventory: GameInventory = {
  categories: [
    {
      key: 'Предметы',
      name: 'Предметы',
      items: [
        {
          id: 'Предметы:Лотерейный билет',
          key: 'Лотерейный билет',
          category: 'Предметы',
          name: '🎟️ Лотерейный билет',
          description: 'Лотерея',
          effect: 'Испытать удачу',
          count: 1,
          sellable: false,
          usable: true,
        },
        {
          id: 'Предметы:Заморозка',
          key: 'Заморозка',
          category: 'Предметы',
          name: '❄️ Заморозка',
          description: 'Сохранить серию',
          count: 1,
          sellable: true,
          usable: true,
        },
        {
          id: 'Предметы:Печатная машинка Хемингуэя',
          key: 'Печатная машинка Хемингуэя',
          category: 'Предметы',
          name: '📠 Печатная машинка Хемингуэя',
          description: 'Постоянный бонус',
          effect: 'Опыт +0,5',
          count: 1,
          sellable: true,
          usable: false,
        },
      ],
    },
    { key: 'Зелья', name: 'Зелья', items: [] },
    { key: 'Награды', name: 'Награды', items: [] },
  ],
}

const shop: ShopCatalog = {
  categories: [{ key: 'Зелья', name: 'Зелья', items: [] }],
  custom_awards: { items: [] },
}

describe('InventoryShopPanel', () => {
  it('restores and emits the persisted inventory category without changing shop state', async () => {
    const wrapper = mount(InventoryShopPanel, {
      props: {
        inventory,
        shop,
        busy: false,
        initialInventoryCategory: 'Награды',
      },
      global: { plugins: [createPinia()] },
    })

    const category = wrapper.get('.item-toolbar select')
    expect((category.element as HTMLSelectElement).value).toBe('Награды')

    await category.setValue('Зелья')

    expect(wrapper.emitted('inventoryCategory')?.[0]).toEqual(['Зелья'])
  })

  it('uses the explicit usable flag and routes freeze to the streak selector', async () => {
    const wrapper = mount(InventoryShopPanel, {
      props: { inventory, shop, busy: false },
      global: { plugins: [createPinia()] },
    })

    expect(wrapper.findAll('.item-card')).toHaveLength(3)
    expect(wrapper.get('.item-card').text()).toContain('Использовать')
    const freezeCard = wrapper.findAll('.item-card')[1]
    expect(freezeCard?.text()).toContain('Выбрать серию')
    const permanentCard = wrapper.findAll('.item-card')[2]
    expect(permanentCard?.text()).not.toContain('Использовать')
    await freezeCard?.get('button').trigger('click')
    expect(wrapper.emitted('freeze')).toHaveLength(1)
  })
})
