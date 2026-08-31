import { createPinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import type { GameItem } from '@/types/game'

import PurchaseConfirmDialog from './PurchaseConfirmDialog.vue'

const item: GameItem = {
  id: 'revival-potion',
  key: 'Зелье воскрешения',
  category: 'Зелья',
  name: 'Зелье воскрешения',
  description: null,
  price: 100,
  count: 0,
  sellable: false,
  usable: false,
  buy: true,
}

describe('PurchaseConfirmDialog', () => {
  it('renders the purchase confirmation without a scrollable content area', () => {
    const wrapper = mount(PurchaseConfirmDialog, {
      props: { item, count: 1, busy: false },
      global: {
        plugins: [createPinia()],
        stubs: {
          IonModal: {
            props: ['isOpen'],
            template: '<div v-if="isOpen"><slot /></div>',
          },
          IonContent: {
            props: ['scrollY'],
            template: '<div class="ion-content-stub" :data-scroll-y="String(scrollY)"><slot /></div>',
          },
        },
      },
    })

    expect(wrapper.get('.ion-content-stub').attributes('data-scroll-y')).toBe('false')
  })
})
