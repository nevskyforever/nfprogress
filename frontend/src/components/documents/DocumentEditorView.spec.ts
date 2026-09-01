import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { documentsApi } from '@/api/documents'
import { projectsApi } from '@/api/projects'
import { announceDataChange } from '@/services/dataChanges'
import { projectFixture } from '@/test/fixtures'
import type { DocumentScope, ProjectDocument } from '@/types/documents'

import DocumentEditorView from './DocumentEditorView.vue'

const { destroyWindow, insertContent, onCloseRequested } = vi.hoisted(() => ({
  destroyWindow: vi.fn(),
  insertContent: vi.fn(),
  onCloseRequested: vi.fn(),
}))

vi.mock('vue-router', () => ({
  onBeforeRouteLeave: vi.fn(),
  useRouter: () => ({ push: vi.fn() }),
}))

vi.mock('@tauri-apps/api/window', () => ({
  getCurrentWindow: () => ({ destroy: destroyWindow, onCloseRequested }),
}))

vi.mock('tiptap-ui-kit', () => ({
  createI18n: vi.fn(),
  setTheme: vi.fn(),
  TiptapProEditor: {
    emits: ['update'],
    setup(_: unknown, { expose }: { expose: (value: unknown) => void }) {
      expose({
        getEditor: () => ({ commands: { insertContent } }),
        getJSON: () => ({ type: 'doc', content: [{ type: 'paragraph', content: [{ type: 'text', text: 'x' }] }] }),
      })
      return {}
    },
    template: `<div class="tiptap-stub ProseMirror" contenteditable="true" @click="$emit('update', { type: 'doc', content: [{ type: 'paragraph', content: [{ type: 'text', text: 'x' }] }] })" />`,
  },
}))

vi.mock('@/api/projects', () => ({
  projectsApi: { get: vi.fn() },
}))

vi.mock('@/api/documents', () => ({
  documentsApi: {
    acceptWord: vi.fn(),
    external: vi.fn(),
    get: vi.fn(),
    link: vi.fn(),
    save: vi.fn(),
    writeDocx: vi.fn(),
  },
}))

const documentFixture: ProjectDocument = {
  project_id: 'project-id',
  stage_id: null,
  content: { type: 'doc', content: [{ type: 'paragraph' }] },
  exists: false,
  updated_at: null,
  docx_path: null,
  sync_state: 'unlinked',
  last_synced_hash: null,
  last_synced_at: null,
  local_dirty: false,
  word_dirty: false,
  symbols: 0,
  has_content: false,
}

function mountEditor(project = projectFixture(), scope: DocumentScope = { projectId: 'project-id' }) {
  vi.mocked(projectsApi.get).mockResolvedValue(project)
  vi.mocked(documentsApi.get).mockResolvedValue({ ...documentFixture, stage_id: scope.stageId ?? null })
  vi.mocked(documentsApi.save).mockResolvedValue({ ...documentFixture, stage_id: scope.stageId ?? null })
  return mount(DocumentEditorView, {
    props: { scope, title: 'Текст' },
    global: { plugins: [createPinia()] },
  })
}

describe('DocumentEditorView status bar', () => {
  beforeEach(() => {
    vi.mocked(projectsApi.get).mockReset()
    vi.mocked(documentsApi.get).mockReset()
    vi.mocked(documentsApi.save).mockReset()
    insertContent.mockReset()
    destroyWindow.mockReset()
    onCloseRequested.mockReset()
    delete window.__TAURI_INTERNALS__
  })

  it('uses written-today progress against the daily plan target', async () => {
    const wrapper = mountEditor(projectFixture({
      total: 25_000,
      goal: 100_000,
      today_goal: 26_000,
      plan_daily_goal: 1_000,
      added_today: 400,
    }))
    await flushPromises()

    expect(wrapper.get('.document-editor-view__unit-count').text()).toContain('25')
    expect(wrapper.get('.document-editor-view__unit-count').text()).toContain('/ 100')
    expect(wrapper.get('.document-editor-view__today-goal').text()).toContain('Цель на сегодня')
    expect(wrapper.get('.document-editor-view__today-goal').text()).toContain('26')
    expect(wrapper.get('[role="progressbar"]').attributes('aria-valuenow')).toBe('40')
    wrapper.unmount()
  })

  it('animates the daily goal preview while text is edited', async () => {
    const wrapper = mountEditor(projectFixture({
      total: 0,
      today_goal: 100,
      plan_daily_goal: 100,
      added_today: 40,
    }))
    await flushPromises()

    const progress = wrapper.get('[role="progressbar"]')
    expect(progress.attributes('aria-valuenow')).toBe('40')

    await wrapper.get('.tiptap-stub').trigger('click')

    expect(progress.attributes('aria-valuenow')).toBe('41')
    expect(wrapper.get('.document-editor-view__today-goal-progress-fill').attributes('style')).toContain('width: 41%')
    wrapper.unmount()
  })

  it('does not offer desktop Word linking in the web editor', async () => {
    const wrapper = mountEditor()
    await flushPromises()

    expect(wrapper.text()).not.toContain('Связать с Word')
    wrapper.unmount()
  })

  it('keeps font controls within the editor toolbar area', async () => {
    const wrapper = mountEditor()
    await flushPromises()

    expect(wrapper.find('.document-editor-view__actions select').exists()).toBe(false)
    expect(wrapper.get('.document-editor-view__workspace .document-editor-view__font-controls').findAll('select')).toHaveLength(2)
    wrapper.unmount()
  })

  it('saves and records changes before a desktop close request', async () => {
    let closeHandler: ((event: { preventDefault: () => void }) => Promise<void>) | undefined
    onCloseRequested.mockImplementation(async (handler) => {
      closeHandler = handler
      return vi.fn()
    })
    window.__TAURI_INTERNALS__ = {}
    const wrapper = mountEditor()
    await flushPromises()

    await wrapper.get('.tiptap-stub').trigger('click')
    const preventDefault = vi.fn()
    await closeHandler?.({ preventDefault })

    expect(preventDefault).toHaveBeenCalledOnce()
    expect(documentsApi.save).toHaveBeenCalled()
    expect(destroyWindow).toHaveBeenCalledOnce()
    wrapper.unmount()
  })

  it('inserts a tab character instead of moving focus outside the editor', async () => {
    const wrapper = mountEditor()
    await flushPromises()

    const event = new KeyboardEvent('keydown', { key: 'Tab', bubbles: true, cancelable: true })
    wrapper.get('.tiptap-stub').element.dispatchEvent(event)

    expect(event.defaultPrevented).toBe(true)
    expect(insertContent).toHaveBeenCalledWith({ type: 'text', text: '\t' })
    wrapper.unmount()
  })

  it('uses the existing total-versus-today-goal state for completion', async () => {
    const wrapper = mountEditor(projectFixture({ total: 26_000, today_goal: 26_000 }))
    await flushPromises()

    const dailyGoal = wrapper.get('.document-editor-view__today-goal')
    expect(dailyGoal.text()).toBe('Цель на день выполнена!')
    expect(dailyGoal.classes()).toContain('document-editor-view__today-goal--complete')
    wrapper.unmount()
  })

  it('uses the selected stage total, goal, and daily target', async () => {
    const stage = projectFixture({
      id: 'stage-id',
      total: 4_000,
      goal: 10_000,
      today_goal: 4_500,
      parent_project_id: 'project-id',
    })
    const wrapper = mountEditor(
      projectFixture({ total: 90_000, goal: 100_000, today_goal: 99_000, stages: [stage] }),
      { projectId: 'project-id', stageId: 'stage-id' },
    )
    await flushPromises()

    expect(wrapper.get('.document-editor-view__unit-count').text()).toContain('4')
    expect(wrapper.get('.document-editor-view__unit-count').text()).toContain('/ 10')
    expect(wrapper.get('.document-editor-view__today-goal').text()).toContain('4')
    expect(wrapper.get('.document-editor-view__today-goal').text()).not.toContain('99')
    wrapper.unmount()
  })

  it('does not render a daily target when the project has none', async () => {
    const wrapper = mountEditor(projectFixture({ goal: null, infinite: true, today_goal: null }))
    await flushPromises()

    expect(wrapper.find('.document-editor-view__today-goal').exists()).toBe(false)
    expect(wrapper.get('.document-editor-view__unit-count').text()).toContain('Без лимита')
    wrapper.unmount()
  })

  it('refreshes the toolbar when the project or stage is changed elsewhere', async () => {
    const wrapper = mountEditor(projectFixture({ total: 25_000, goal: 100_000, today_goal: 26_000 }))
    await flushPromises()

    vi.mocked(projectsApi.get).mockResolvedValue(projectFixture({ total: 30_000, goal: 120_000, today_goal: 30_000 }))
    announceDataChange('projects')
    await flushPromises()

    expect(wrapper.get('.document-editor-view__unit-count').text()).toContain('30')
    expect(wrapper.get('.document-editor-view__unit-count').text()).toContain('/ 120')
    expect(wrapper.get('.document-editor-view__today-goal').text()).toBe('Цель на день выполнена!')
    wrapper.unmount()
  })
})
