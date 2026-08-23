import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import { useUpdaterStore } from '@/stores/updater'

import UpdatePrompt from './UpdatePrompt.vue'

describe('UpdatePrompt', () => {
  it('announces an available version and can be postponed', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const updater = useUpdaterStore(pinia)
    updater.status = 'available'
    updater.availableVersion = '4.15.0'
    updater.releaseNotes = 'Исправления и улучшения'

    const wrapper = mount(UpdatePrompt, {
      global: {
        plugins: [pinia],
        stubs: {
          IonIcon: true,
          IonSpinner: true,
        },
      },
    })

    expect(wrapper.get('[role="dialog"]').attributes('aria-labelledby'))
      .toBe('update-prompt-title')
    expect(wrapper.text()).toContain('4.15.0')
    expect(wrapper.text()).toContain('Исправления и улучшения')

    await wrapper.get('.update-prompt__close').trigger('click')

    expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
  })
})
