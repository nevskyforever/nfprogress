import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import type { JSONContent } from '@tiptap/core'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { documentsApi } from '@/api/documents'
import { projectsApi } from '@/api/projects'
import { announceDataChange } from '@/services/dataChanges'
import { projectFixture } from '@/test/fixtures'
import type { DocumentScope, ProjectDocument, TiptapDocument } from '@/types/documents'

import DocumentEditorView from './DocumentEditorView.vue'

const { destroyWindow, editorJson, editorSelection, editorUpdate, focusEditor, insertContent, onBeforeRouteLeave, onCloseRequested, scrollIntoView, setLineHeight, setTextSelection } = vi.hoisted(() => ({
  destroyWindow: vi.fn(),
  editorJson: { value: { type: 'doc', content: [{ type: 'paragraph', content: [{ type: 'text', text: 'x' }] }] } as JSONContent },
  editorSelection: { from: 1 },
  editorUpdate: { value: { type: 'doc', content: [{ type: 'paragraph', content: [{ type: 'text', text: 'x' }] }] } as JSONContent },
  focusEditor: vi.fn(),
  insertContent: vi.fn(),
  onBeforeRouteLeave: vi.fn(),
  onCloseRequested: vi.fn(),
  scrollIntoView: vi.fn(),
  setLineHeight: vi.fn(),
  setTextSelection: vi.fn(),
}))
const positionStorage = new Map<string, string>()

vi.mock('vue-router', () => ({
  onBeforeRouteLeave,
  useRouter: () => ({ push: vi.fn() }),
}))

vi.mock('@tauri-apps/api/window', () => ({
  getCurrentWindow: () => ({ destroy: destroyWindow, onCloseRequested }),
}))

vi.mock('tiptap-ui-kit', () => ({
  createI18n: vi.fn(),
  setTheme: vi.fn(),
  TiptapProEditor: {
    props: ['modelValue'],
    emits: ['update'],
    setup(_: unknown, { expose }: { expose: (value: unknown) => void }) {
      expose({
        getEditor: () => ({
          commands: { focus: focusEditor, insertContent, scrollIntoView, setTextSelection },
          state: { selection: editorSelection, doc: { content: { size: 100 } } },
          chain: () => ({ focus: () => ({ setLineHeight: (value: string) => ({ run: () => setLineHeight(value) }) }) }),
        }),
        getJSON: () => editorJson.value,
      })
      return { editorUpdate }
    },
    template: `<div><div class="word-toolbar"><div class="editor-toolbar" /></div><div class="word-document-container"><div class="tiptap-stub ProseMirror" contenteditable="true" @click="$emit('update', editorUpdate.value)" /><output class="tiptap-model">{{ JSON.stringify(modelValue) }}</output></div></div>`,
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
    recordProgress: vi.fn(),
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

function mountEditor(project = projectFixture(), scope: DocumentScope = { projectId: 'project-id' }, savedDocument = documentFixture) {
  vi.mocked(projectsApi.get).mockResolvedValue(project)
  vi.mocked(documentsApi.get).mockResolvedValue({ ...savedDocument, stage_id: scope.stageId ?? null })
  vi.mocked(documentsApi.save).mockResolvedValue({ ...documentFixture, stage_id: scope.stageId ?? null })
  return mount(DocumentEditorView, {
    props: { scope, title: 'Текст' },
    global: { plugins: [createPinia()] },
  })
}

describe('DocumentEditorView status bar', () => {
  beforeEach(() => {
    positionStorage.clear()
    Object.defineProperty(window, 'localStorage', {
      configurable: true,
      value: {
        getItem: (key: string) => positionStorage.get(key) ?? null,
        removeItem: (key: string) => { positionStorage.delete(key) },
        setItem: (key: string, value: string) => { positionStorage.set(key, value) },
      },
    })
    vi.mocked(projectsApi.get).mockReset()
    vi.mocked(documentsApi.get).mockReset()
    vi.mocked(documentsApi.recordProgress).mockReset()
    vi.mocked(documentsApi.save).mockReset()
    onBeforeRouteLeave.mockReset()
    editorJson.value = { type: 'doc', content: [{ type: 'paragraph', content: [{ type: 'text', text: 'x' }] }] }
    editorUpdate.value = editorJson.value
    insertContent.mockReset()
    focusEditor.mockReset()
    setTextSelection.mockReset()
    scrollIntoView.mockReset()
    setLineHeight.mockReset()
    destroyWindow.mockReset()
    onCloseRequested.mockReset()
    delete window.__TAURI_INTERNALS__
    editorSelection.from = 1
    window.localStorage?.removeItem('nfprogress:document-position:project-id:project')
  })

  it('uses the work written today for the daily goal progress bar', async () => {
    const wrapper = mountEditor(projectFixture({
      total: 25_000,
      goal: 100_000,
      today_goal: 26_000,
      plan_daily_goal: 1_000,
      added_today: 400,
    }))
    await flushPromises()

    expect(wrapper.get('.document-editor-view__unit-count').text()).toContain('0')
    expect(wrapper.get('.document-editor-view__unit-count').text()).toContain('/ 100')
    expect(wrapper.get('.document-editor-view__today-goal').text()).toContain('Цель на сегодня')
    expect(wrapper.get('.document-editor-view__today-goal').text()).toContain('26')
    expect(wrapper.get('[role="progressbar"]').attributes('aria-valuenow')).toBe('40')
    wrapper.unmount()
  })

  it('updates the cumulative daily goal preview while text is edited', async () => {
    const wrapper = mountEditor(projectFixture({
      total: 0,
      today_goal: 100,
      plan_daily_goal: 100,
      added_today: 40,
    }))
    await flushPromises()

    const progress = wrapper.get('[role="progressbar"]')
    expect(progress.attributes('aria-valuenow')).toBe('40')
    expect(wrapper.get('.document-editor-view__unit-count').text()).toContain('0 / 100')

    await wrapper.get('.tiptap-stub').trigger('click')

    expect(progress.attributes('aria-valuenow')).toBe('41')
    expect(wrapper.get('.document-editor-view__today-goal-progress-fill').attributes('style')).toContain('width: 41%')
    expect(wrapper.get('.document-editor-view__unit-count').text()).toContain('1 / 100')
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
    expect(wrapper.get('.word-toolbar .document-editor-view__font-controls').findAll('select')).toHaveLength(3)
    wrapper.unmount()
  })

  it('sets the selected line spacing for the current paragraph', async () => {
    const wrapper = mountEditor()
    await flushPromises()

    await wrapper.get('select[aria-label="Межстрочный интервал"]').setValue('2')

    expect(setLineHeight).toHaveBeenCalledWith('2')
    wrapper.unmount()
  })

  it('closes the desktop window when there are no pending changes', async () => {
    let closeHandler: ((event: { preventDefault: () => void }) => Promise<void>) | undefined
    onCloseRequested.mockImplementation(async (handler) => {
      closeHandler = handler
      return vi.fn()
    })
    window.__TAURI_INTERNALS__ = {}
    const wrapper = mountEditor()
    await flushPromises()

    const preventDefault = vi.fn()
    await closeHandler?.({ preventDefault })

    expect(preventDefault).toHaveBeenCalledOnce()
    expect(documentsApi.save).toHaveBeenCalled()
    expect(destroyWindow).toHaveBeenCalledOnce()
    wrapper.unmount()
  })

  it('does not record progress during save-only route navigation', async () => {
    const wrapper = mountEditor(projectFixture({ total: 804 }))
    await flushPromises()

    const routeLeave = onBeforeRouteLeave.mock.calls[0]?.[0] as (() => Promise<void>) | undefined
    await routeLeave?.()

    expect(documentsApi.save).toHaveBeenCalled()
    expect(documentsApi.recordProgress).not.toHaveBeenCalled()
    wrapper.unmount()
  })

  it('records only the actual positive delta from the explicit add action', async () => {
    const project = projectFixture({ total: 804 })
    vi.mocked(documentsApi.recordProgress).mockResolvedValue({
      changed: true,
      symbols: 805,
      progress: {
        project: projectFixture({ total: 805 }),
        entry: {
          id: 'entry-id',
          new_total: 805,
          new_total_symbols: 805,
          added: 1,
          added_symbols: 1,
          added_progress: 0.001,
          created_at: '2026-09-04T01:00:00+00:00',
        },
        added_symbols: 1,
        game: null,
        warning: null,
      },
    })
    const wrapper = mountEditor(project)
    await flushPromises()
    await wrapper.get('.tiptap-stub').trigger('click')
    await wrapper.get('.document-editor-view__actions .nf-button').trigger('click')
    await flushPromises()

    expect(documentsApi.recordProgress).toHaveBeenCalledOnce()
    expect(wrapper.text()).not.toContain('Из проекта удалено')
    wrapper.unmount()
  })

  it('keeps the latest update when getJSON returns an empty transient document', async () => {
    const edited: TiptapDocument = {
      type: 'doc',
      content: [{ type: 'paragraph', content: [{ type: 'text', text: 'Текст проекта' }] }],
    }
    const existing = { ...documentFixture, content: edited, exists: true, has_content: true }
    editorUpdate.value = edited
    editorJson.value = { type: 'doc', content: [{ type: 'paragraph' }] }
    vi.mocked(documentsApi.recordProgress).mockResolvedValue({ changed: false, symbols: 12, progress: null })
    const wrapper = mountEditor(projectFixture({ total: 804 }), { projectId: 'project-id' }, existing)
    await flushPromises()
    await wrapper.get('.tiptap-stub').trigger('click')
    await wrapper.get('.document-editor-view__actions .nf-button').trigger('click')
    await flushPromises()

    expect(documentsApi.save).toHaveBeenCalledWith({ projectId: 'project-id' }, edited)
    wrapper.unmount()
  })

  it('ignores a transient empty update while the record request is in flight', async () => {
    const edited: TiptapDocument = {
      type: 'doc',
      content: [{ type: 'paragraph', content: [{ type: 'text', text: 'Текст проекта' }] }],
    }
    editorUpdate.value = edited
    editorJson.value = edited
    let wrapper: ReturnType<typeof mount>
    vi.mocked(documentsApi.save).mockImplementation(async () => {
      editorUpdate.value = { type: 'doc', content: [{ type: 'paragraph' }] }
      await wrapper.get('.tiptap-stub').trigger('click')
      return documentFixture
    })
    vi.mocked(documentsApi.recordProgress).mockResolvedValue({ changed: false, symbols: 12, progress: null })
    wrapper = mountEditor(projectFixture({ total: 804 }))
    await flushPromises()
    await wrapper.get('.tiptap-stub').trigger('click')
    await wrapper.get('.document-editor-view__actions .nf-button').trigger('click')
    await flushPromises()

    expect(JSON.parse(wrapper.get('.tiptap-model').text())).toEqual(edited)
    expect(documentsApi.save).toHaveBeenCalledOnce()
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

  it('restores the last text position for the opened document', async () => {
    window.localStorage?.setItem(
      'nfprogress:document-position:project-id:project',
      JSON.stringify({ selection: 48, scrollTop: 360 }),
    )
    const wrapper = mountEditor()
    await flushPromises()

    expect(setTextSelection).toHaveBeenCalledWith(48)
    expect(focusEditor).toHaveBeenCalledOnce()
    expect(scrollIntoView).toHaveBeenCalled()
    expect(wrapper.get('.word-document-container').element.scrollTop).toBe(360)
    wrapper.unmount()
  })

  it('does not restore the cursor again while the user edits', async () => {
    window.localStorage?.setItem(
      'nfprogress:document-position:project-id:project',
      JSON.stringify({ selection: 48, scrollTop: 360 }),
    )
    const wrapper = mountEditor()
    await flushPromises()
    await wrapper.get('.tiptap-stub').trigger('click')
    await flushPromises()

    expect(setTextSelection).toHaveBeenCalledTimes(1)
    wrapper.unmount()
  })

  it('remembers the cursor position when the editor closes', async () => {
    editorSelection.from = 37
    const wrapper = mountEditor()
    await flushPromises()
    wrapper.unmount()

    expect(JSON.parse(window.localStorage?.getItem('nfprogress:document-position:project-id:project') ?? '{}'))
      .toMatchObject({ selection: 37 })
  })

  it('marks the daily goal complete after enough work is written today', async () => {
    const wrapper = mountEditor(projectFixture({ total: 26_000, today_goal: 26_000, added_today: 1_000 }))
    await flushPromises()

    const dailyGoal = wrapper.get('.document-editor-view__today-goal')
    expect(dailyGoal.text()).toBe('Цель на день выполнена!')
    expect(dailyGoal.classes()).toContain('document-editor-view__today-goal--complete')
    wrapper.unmount()
  })

  it('uses the selected stage goal and daily target while displaying document text', async () => {
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

    expect(wrapper.get('.document-editor-view__unit-count').text()).toContain('0')
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

    vi.mocked(projectsApi.get).mockResolvedValue(projectFixture({ total: 30_000, goal: 120_000, today_goal: 30_000, added_today: 1_000 }))
    announceDataChange('projects')
    await flushPromises()

    expect(wrapper.get('.document-editor-view__unit-count').text()).toContain('0')
    expect(wrapper.get('.document-editor-view__unit-count').text()).toContain('/ 120')
    expect(wrapper.get('.document-editor-view__today-goal').text()).toBe('Цель на день выполнена!')
    wrapper.unmount()
  })
})
