import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { nextTick } from 'vue'

import { useMotionStore } from '@/stores/motion'

import ProgressBar from './ProgressBar.vue'
import ProgressRing from './ProgressRing.vue'

describe('progress indicator motion', () => {
  it('starts a visible animation for rings and bars in full-motion mode', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    useMotionStore(pinia).setPreference('full')

    const ring = mount(ProgressRing, {
      props: { value: 64, label: 'Прогресс' },
      global: { plugins: [pinia] },
    })
    const bar = mount(ProgressBar, {
      props: { value: 64, label: 'Прогресс' },
      global: { plugins: [pinia] },
    })
    await nextTick()

    expect(ring.get('.progress-ring').classes()).toContain('progress-ring--animating')
    expect(bar.get('.progress-bar').classes()).toContain('progress-bar--animating')
    expect(bar.get('.progress-bar__fill').attributes('style')).toContain('scaleX(0)')
  })

  it('uses the final value immediately only in explicit reduced-motion mode', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    useMotionStore(pinia).setPreference('reduced')

    const ring = mount(ProgressRing, {
      props: { value: 42, label: 'Прогресс' },
      global: { plugins: [pinia] },
    })
    const bar = mount(ProgressBar, {
      props: { value: 42, label: 'Прогресс' },
      global: { plugins: [pinia] },
    })
    await nextTick()

    expect(ring.text()).toContain('42%')
    expect(ring.get('.progress-ring').classes()).not.toContain('progress-ring--animating')
    expect(bar.get('.progress-bar__fill').attributes('style')).toContain('scaleX(0.42)')
  })
})
