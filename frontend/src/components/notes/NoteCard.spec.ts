import { createPinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import { noteFixture } from '@/test/noteFixtures'

import NoteCard from './NoteCard.vue'

describe('NoteCard', () => {
  it('renders sanitized rich text as a plain preview and exposes keyboard actions', async () => {
    const wrapper = mount(NoteCard, {
      props: {
        note: noteFixture({
          content: '<p>Тайна <strong>старого маяка</strong></p>',
          pinned: true,
          color: 'yellow',
        }),
        canMoveDown: true,
      },
      global: {
        plugins: [createPinia()],
        stubs: { IonIcon: true },
      },
    })

    expect(wrapper.text()).toContain('Тайна старого маяка')
    expect(wrapper.get('article').attributes('data-color')).toBe('yellow')
    expect(wrapper.text()).not.toContain('<strong>')
    const pinButton = wrapper.get('button[aria-label="Открепить заметку"]')
    await pinButton.trigger('click')
    expect(wrapper.emitted('togglePin')?.[0]?.[0]).toMatchObject({ id: 'note-id' })
    expect(wrapper.get('button[aria-label="Переместить заметку выше"]').attributes()).toHaveProperty(
      'disabled',
    )
  })

  it('offers a map focus action only for linked Mind Elixir notes', () => {
    const wrapper = mount(NoteCard, {
      props: {
        note: noteFixture({
          source_type: 'mindmap',
          source_node_id: 'floating-note',
          content_format: 'plain',
          system_tags: ['карта'],
        }),
      },
      global: {
        plugins: [createPinia()],
        stubs: { IonIcon: true },
      },
    })

    expect(wrapper.find('button[aria-label="Показать заметку на карте"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('#карта')
  })

  it('uses the legacy note palette and emits a color change from the card', async () => {
    const wrapper = mount(NoteCard, {
      props: { note: noteFixture({ color: 'yellow' }) },
      global: {
        plugins: [createPinia()],
        stubs: { IonIcon: true },
      },
    })

    await wrapper.get('button[aria-label="Цвет заметки"]').trigger('click')

    const swatches = wrapper.findAll('.note-card__swatch')
    expect(swatches).toHaveLength(11)
    expect(wrapper.get('.note-card__swatch[data-color="yellow"]').attributes('aria-pressed')).toBe('true')

    await wrapper.get('.note-card__swatch[data-color="blue"]').trigger('click')
    expect(wrapper.emitted('setColor')?.[0]).toEqual([
      expect.objectContaining({ id: 'note-id' }),
      'blue',
    ])
  })
})
