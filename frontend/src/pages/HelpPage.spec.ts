import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { contentApi } from '@/api/content'

import HelpPage from './HelpPage.vue'

vi.mock('@/api/content', () => ({
  contentApi: {
    help: vi.fn(),
    locale: vi.fn(),
  },
}))

describe('HelpPage', () => {
  beforeEach(() => {
    vi.mocked(contentApi.help).mockReset()
    vi.mocked(contentApi.help).mockResolvedValue([
      {
        key: 'quick-start',
        title: 'Quick start',
        content: '<html><body><h2>Quick start</h2><p>Begin writing.</p></body></html>',
        children: [],
      },
      {
        key: 'projects',
        title: 'Projects',
        content:
          '<html><body><h2>Projects</h2><p>Use <strong>deadlines</strong> carefully.</p></body></html>',
        children: [],
      },
    ])
  })

  it('searches the localized article text while retaining canonical section keys', async () => {
    const wrapper = mount(HelpPage, {
      global: {
        plugins: [createPinia()],
        stubs: {
          IonContent: { template: '<div><slot /></div>' },
          IonPage: { template: '<div><slot /></div>' },
          IonIcon: true,
          StatePanel: true,
        },
      },
    })
    await flushPromises()

    await wrapper.get('#help-search-input').setValue('deadlines')
    const result = wrapper.get('.help-results button')
    expect(result.text()).toBe('Projects')
    await result.trigger('click')

    expect(wrapper.get('article').attributes('aria-labelledby')).toBe('help-projects')
    expect(wrapper.get('.help-article__body').html()).toContain('<strong>deadlines</strong>')
    wrapper.unmount()
  })

  it('moves keyboard focus to help search for the standard find shortcut', async () => {
    const wrapper = mount(HelpPage, {
      attachTo: document.body,
      global: {
        plugins: [createPinia()],
        stubs: {
          IonContent: { template: '<div><slot /></div>' },
          IonPage: { template: '<div><slot /></div>' },
          IonIcon: true,
          StatePanel: true,
        },
      },
    })
    await flushPromises()

    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'f', ctrlKey: true }))

    expect(document.activeElement).toBe(wrapper.get('#help-search-input').element)
    wrapper.unmount()
  })
})
