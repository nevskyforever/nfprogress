import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { createPinia } from 'pinia'
import {
  flameOutline,
  heartDislikeOutline,
  hourglassOutline,
  moonOutline,
  powerOutline,
  rocketOutline,
  snowOutline,
  trophyOutline,
} from 'ionicons/icons'

import StreakBadge from './StreakBadge.vue'

const iconStub = {
  props: ['icon'],
  template: '<i data-testid="streak-icon" />',
}

describe('StreakBadge', () => {
  it.each([
    ['Start', flameOutline],
    ['Go', rocketOutline],
    ['Active', hourglassOutline],
    ['Freeze', snowOutline],
    ['Complete', trophyOutline],
    ['Lose 4', heartDislikeOutline],
    ['No', moonOutline],
    ['Off', powerOutline],
  ])('uses a distinct vector icon for %s', (status, icon) => {
    const wrapper = mount(StreakBadge, {
      props: { length: 4, status },
      global: { plugins: [createPinia()], stubs: { IonIcon: iconStub } },
    })

    expect(wrapper.getComponent(iconStub).props('icon')).toBe(icon)
  })
})
