import { createPinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import ProgressShareMenu from './ProgressShareMenu.vue'

describe('ProgressShareMenu', () => {
  it('offers separate icon actions for clipboard and file export', async () => {
    const wrapper = mount(ProgressShareMenu, {
      props: { label: 'Поделиться прогрессом «Роман»' },
      global: { plugins: [createPinia()], stubs: { IonIcon: true } },
    })

    await wrapper.get('button[aria-label="Поделиться прогрессом «Роман»"]').trigger('click')
    expect(wrapper.find('[role="menu"]').exists()).toBe(true)

    await wrapper.get('button[aria-label="Скопировать картинку прогресса"]').trigger('click')
    expect(wrapper.emitted('copy')).toHaveLength(1)

    await wrapper.get('button[aria-label="Поделиться прогрессом «Роман»"]').trigger('click')
    await wrapper.get('button[aria-label="Сохранить картинку прогресса"]').trigger('click')
    expect(wrapper.emitted('save')).toHaveLength(1)
  })
})
