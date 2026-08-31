import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { notesApi } from '@/api/notes'
import { mindMapFixture, noteFixture } from '@/test/noteFixtures'

import NotesPage from './NotesPage.vue'

const replaceRoute = vi.fn()
const pushRoute = vi.fn()

vi.mock('vue-router', () => ({
  useRoute: () => ({
    params: { projectId: 'project-id' },
    query: {},
    name: 'project-notes',
  }),
  useRouter: () => ({ replace: replaceRoute, push: pushRoute }),
}))

vi.mock('@/api/notes', () => ({
  notesApi: {
    list: vi.fn(),
    create: vi.fn(),
    get: vi.fn(),
    update: vi.fn(),
    remove: vi.fn(),
    reorder: vi.fn(),
    mindMap: vi.fn(),
    saveMindMap: vi.fn(),
  },
}))

describe('NotesPage', () => {
  beforeEach(() => {
    replaceRoute.mockReset()
    pushRoute.mockReset()
    vi.mocked(notesApi.list).mockResolvedValue({
      notes: [noteFixture()],
      read_only: false,
      context: { hasStages: false, stages: [] },
    })
    vi.mocked(notesApi.mindMap).mockResolvedValue(mindMapFixture())
  })

  it('loads real note and mind-map endpoints as one responsive workspace', async () => {
    const wrapper = mount(NotesPage, {
      global: {
        plugins: [createPinia()],
        stubs: {
          IonIcon: true,
          IonSpinner: true,
          RouterLink: { template: '<a><slot /></a>' },
          MindMapEditor: true,
          NoteEditorDialog: true,
        },
      },
    })
    await flushPromises()

    expect(notesApi.list).toHaveBeenCalledWith({ projectId: 'project-id', stageId: null })
    expect(notesApi.mindMap).toHaveBeenCalledWith({ projectId: 'project-id', stageId: null })
    expect(wrapper.get('h1').text()).toBe('Дом у моря')
    expect(wrapper.text()).toContain('Первая встреча')
    expect(wrapper.get('[role="tablist"]').attributes('aria-label')).toBe('Заметки и карта')
    expect(wrapper.get('input[type="search"]').attributes('placeholder')).toBe('Поиск по заметкам')
    expect(wrapper.get('.new-note-button').text()).toBe('Новая заметка')
    wrapper.unmount()
  })

  it('returns to the project when Escape is pressed', async () => {
    const wrapper = mount(NotesPage, {
      global: {
        plugins: [createPinia()],
        stubs: {
          IonIcon: true,
          IonSpinner: true,
          RouterLink: { template: '<a><slot /></a>' },
          MindMapEditor: true,
          NoteEditorDialog: true,
        },
      },
    })
    await flushPromises()

    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))

    expect(pushRoute).toHaveBeenCalledWith({ name: 'project-detail', params: { projectId: 'project-id' } })
    wrapper.unmount()
  })
})
