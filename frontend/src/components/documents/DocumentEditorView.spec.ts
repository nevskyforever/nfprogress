import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import type { JSONContent } from '@tiptap/core'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { documentsApi } from '@/api/documents'
import { projectsApi } from '@/api/projects'
import { announceDataChange } from '@/services/dataChanges'
import { projectFixture } from '@/test/fixtures'
import type { DocumentScope, ProjectDocument, TiptapDocument } from '@/types/documents'

import DocumentEditorView from './DocumentEditorView.vue'

const { destroyWindow, editorCoordsAtPos, editorJson, editorModelValue, editorOff, editorOn, editorReady, editorSelection, editorUpdate, focusEditor, insertContent, onBeforeRouteLeave, onCloseRequested, scrollIntoView, setEditorContent, setLineHeight, setTextSelection } = vi.hoisted(() => ({
  destroyWindow: vi.fn(),
  editorCoordsAtPos: vi.fn(),
  editorJson: { value: { type: 'doc', content: [{ type: 'paragraph', content: [{ type: 'text', text: 'x' }] }] } as JSONContent },
  editorModelValue: { value: { type: 'doc', content: [{ type: 'paragraph', content: [{ type: 'text', text: 'x' }] }] } as JSONContent },
  editorOff: vi.fn(),
  editorOn: vi.fn(),
  editorReady: { value: true },
  editorSelection: { from: 1 },
  editorUpdate: { value: { type: 'doc', content: [{ type: 'paragraph', content: [{ type: 'text', text: 'x' }] }] } as JSONContent },
  focusEditor: vi.fn(),
  insertContent: vi.fn(),
  onBeforeRouteLeave: vi.fn(),
  onCloseRequested: vi.fn(),
  scrollIntoView: vi.fn(),
  setEditorContent: vi.fn(),
  setLineHeight: vi.fn(),
  setTextSelection: vi.fn(),
}))
const positionStorage = new Map<string, string>()

type TypewriterGeometry = {
  caretOffset: number
  clientHeight: number
  contentHeight: number
  top: number
}

let typewriterGeometry: TypewriterGeometry | null = null

function editorZoom(element: Element): number {
  const root = element.closest('.nfprogress-word-editor') as HTMLElement | null
  return Number(root?.style.getPropertyValue('--nf-editor-zoom') || 1)
}

function installTypewriterGeometry(wrapper: ReturnType<typeof mountEditor>, next: TypewriterGeometry): HTMLElement {
  typewriterGeometry = next
  const container = wrapper.get('.word-document-container').element as HTMLElement
  let scrollTop = 0
  Object.defineProperties(container, {
    clientHeight: { configurable: true, get: () => typewriterGeometry?.clientHeight ?? 0 },
    scrollHeight: {
      configurable: true,
      get: () => {
        const tail = container.querySelector<HTMLElement>('[data-nf-typewriter-tail]')
        const visualTail = tail ? Number.parseFloat(tail.style.height || '0') * editorZoom(tail) : 0
        return (typewriterGeometry?.contentHeight ?? 0) * editorZoom(container) + visualTail
      },
    },
    scrollTop: {
      configurable: true,
      get: () => scrollTop,
      set: (value: number) => {
        const maximum = Math.max(0, container.scrollHeight - container.clientHeight)
        scrollTop = Math.max(0, Math.min(maximum, value))
      },
    },
  })
  container.getBoundingClientRect = () => new DOMRect(0, next.top, 700, next.clientHeight)
  const sheet = wrapper.get('.continuous-pages').element as HTMLElement
  Object.defineProperties(sheet, {
    offsetWidth: { configurable: true, get: () => 800 },
  })
  sheet.getBoundingClientRect = () => new DOMRect(0, next.top, 800 * editorZoom(sheet), next.contentHeight)
  new MutationObserver(() => { container.scrollTop = scrollTop }).observe(sheet, { childList: true })
  editorCoordsAtPos.mockImplementation(() => {
    const geometry = typewriterGeometry
    const top = (geometry?.top ?? 0) + (geometry?.caretOffset ?? 0) * editorZoom(container) - container.scrollTop
    return { top, bottom: top + 20, left: 0, right: 1 }
  })
  return container
}

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
    name: 'TiptapProEditor',
    props: ['initialContent', 'modelValue'],
    emits: ['update', 'update:modelValue'],
    setup(_: unknown, { expose }: { expose: (value: unknown) => void }) {
      expose({
        getEditor: () => editorReady.value ? ({
          commands: { focus: focusEditor, insertContent, scrollIntoView, setContent: setEditorContent, setTextSelection },
          getJSON: () => editorJson.value,
          off: editorOff,
          on: editorOn,
          state: { selection: editorSelection, doc: { content: { size: 100 } } },
          view: { coordsAtPos: editorCoordsAtPos },
          chain: () => ({ focus: () => ({ setLineHeight: (value: string) => ({ run: () => setLineHeight(value) }) }) }),
        }) : null,
        getJSON: () => editorJson.value,
      })
      return { editorModelValue, editorUpdate }
    },
    template: `<div><div class="word-toolbar"><div class="editor-toolbar" /></div><div class="word-document-container"><div class="document-pages"><div class="continuous-pages"><div class="word-content-multi"><div class="tiptap-stub ProseMirror" contenteditable="true" @click="$emit('update', editorUpdate.value)" /></div></div></div><button class="tiptap-model-update" type="button" @click="$emit('update:modelValue', editorModelValue.value)" /><output class="tiptap-model">{{ JSON.stringify(initialContent) }}</output></div></div>`,
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
    writeDocxContent: vi.fn(),
    parseWord: vi.fn(),
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
    editorModelValue.value = editorJson.value
    editorUpdate.value = editorJson.value
    editorReady.value = true
    insertContent.mockReset()
    focusEditor.mockReset()
    setTextSelection.mockReset()
    scrollIntoView.mockReset()
    setLineHeight.mockReset()
    setEditorContent.mockReset()
    destroyWindow.mockReset()
    onCloseRequested.mockReset()
    delete window.__TAURI_INTERNALS__
    editorSelection.from = 1
    editorCoordsAtPos.mockReset()
    editorOff.mockReset()
    editorOn.mockReset()
    typewriterGeometry = null
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

  it('captures the current editor document before the debounced update', async () => {
    const edited: TiptapDocument = {
      type: 'doc',
      content: [{ type: 'paragraph', content: [{ type: 'text', text: 'Новая запись' }] }],
    }
    editorJson.value = edited
    vi.mocked(documentsApi.recordProgress).mockResolvedValue({ changed: false, symbols: 12, progress: null })
    const wrapper = mountEditor(projectFixture({ total: 804 }), { projectId: 'project-id' }, {
      ...documentFixture,
      content: { type: 'doc', content: [{ type: 'paragraph', content: [{ type: 'text', text: 'Черновик' }] }] },
      exists: true,
      has_content: true,
    })
    await flushPromises()
    await wrapper.get('.document-editor-view__actions .nf-button').trigger('click')
    await flushPromises()

    expect(documentsApi.recordProgress).toHaveBeenCalledWith({ projectId: 'project-id' }, edited)
    expect(documentsApi.save).not.toHaveBeenCalled()
    wrapper.unmount()
  })

  it('waits for the initial document before mounting the editor', async () => {
    let finishLoad: ((value: ProjectDocument) => void) | undefined
    vi.mocked(projectsApi.get).mockResolvedValue(projectFixture({ total: 804 }))
    vi.mocked(documentsApi.get).mockReturnValue(new Promise((resolve) => { finishLoad = resolve }))
    const wrapper = mount(DocumentEditorView, {
      props: { scope: { projectId: 'project-id' }, title: 'Текст' },
      global: { plugins: [createPinia()] },
    })
    await flushPromises()

    expect(wrapper.find('.tiptap-stub').exists()).toBe(false)

    const loaded = {
      ...documentFixture,
      content: { type: 'doc', content: [{ type: 'paragraph', content: [{ type: 'text', text: 'Черновик' }] }] } as TiptapDocument,
    }
    finishLoad?.(loaded)
    await flushPromises()

    expect(JSON.parse(wrapper.get('.tiptap-model').text())).toEqual(loaded.content)
    wrapper.unmount()
  })

  it('mounts an empty editor for a document that does not exist yet', async () => {
    const wrapper = mountEditor(projectFixture({ total: 804 }), { projectId: 'project-id' }, documentFixture)
    await flushPromises()

    expect(wrapper.find('.document-editor-view__workspace .tiptap-stub').exists()).toBe(true)
    expect(JSON.parse(wrapper.get('.tiptap-model').text())).toEqual(documentFixture.content)
    wrapper.unmount()
  })

  it('keeps the editor uncontrolled after loading the initial document', async () => {
    const edited: TiptapDocument = {
      type: 'doc',
      content: [{ type: 'paragraph', content: [{ type: 'text', text: 'Текст проекта' }] }],
    }
    const existing = { ...documentFixture, content: edited, exists: true, has_content: true }
    editorUpdate.value = edited
    editorJson.value = edited
    vi.mocked(documentsApi.recordProgress).mockResolvedValue({ changed: false, symbols: 12, progress: null })
    const wrapper = mountEditor(projectFixture({ total: 804 }), { projectId: 'project-id' }, existing)
    await flushPromises()

    const editor = wrapper.findComponent({ name: 'TiptapProEditor' })
    expect(editor.props('modelValue')).toBeUndefined()
    expect(editor.props('initialContent')).toEqual(edited)

    await wrapper.get('.document-editor-view__actions .nf-button').trigger('click')
    await flushPromises()

    expect(documentsApi.recordProgress).toHaveBeenCalledWith({ projectId: 'project-id' }, edited)
    wrapper.unmount()
  })

  it('restores the draft when the editor becomes empty during recording', async () => {
    const initial: TiptapDocument = {
      type: 'doc',
      content: [{ type: 'paragraph', content: [{ type: 'text', text: 'а'.repeat(801) }] }],
    }
    const edited: TiptapDocument = {
      type: 'doc',
      content: [{ type: 'paragraph', content: [{ type: 'text', text: 'а'.repeat(802) }] }],
    }
    editorJson.value = edited
    editorUpdate.value = edited
    vi.mocked(documentsApi.recordProgress).mockImplementation(async () => {
      editorJson.value = { type: 'doc', content: [{ type: 'paragraph' }] }
      editorModelValue.value = { type: 'doc', content: [{ type: 'paragraph' }] }
      await wrapper.get('.tiptap-model-update').trigger('click')
      return {
        changed: true,
        symbols: 802,
        progress: {
          project: projectFixture({ total: 802 }),
          entry: {
            id: 'entry-id',
            new_total: 802,
            new_total_symbols: 802,
            added: 1,
            added_symbols: 1,
            added_progress: 0.1,
            created_at: '2026-09-04T01:00:00+00:00',
          },
          added_symbols: 1,
          game: null,
          warning: null,
        },
      }
    })
    const wrapper = mountEditor(projectFixture({ total: 801 }), { projectId: 'project-id' }, {
      ...documentFixture,
      content: initial,
      exists: true,
      has_content: true,
    })
    await flushPromises()
    await wrapper.get('.tiptap-stub').trigger('click')
    await wrapper.get('.document-editor-view__actions .nf-button').trigger('click')
    await flushPromises()

    expect(documentsApi.recordProgress).toHaveBeenCalledWith({ projectId: 'project-id' }, edited)
    expect(setEditorContent).toHaveBeenCalledWith(edited, { emitUpdate: false })
    expect(JSON.parse(wrapper.get('.tiptap-model').text())).toEqual(edited)
    expect(wrapper.text()).not.toContain('Из проекта удалено')
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

  it('waits until the internal editor is ready before restoring its position', async () => {
    vi.useFakeTimers()
    try {
      editorReady.value = false
      window.localStorage?.setItem(
        'nfprogress:document-position:project-id:project',
        JSON.stringify({ selection: 48, scrollTop: 360 }),
      )
      const wrapper = mountEditor()
      await flushPromises()

      expect(setTextSelection).not.toHaveBeenCalled()

      editorReady.value = true
      await vi.advanceTimersByTimeAsync(50)

      expect(setTextSelection).toHaveBeenCalledWith(48)
      expect(wrapper.get('.word-document-container').element.scrollTop).toBe(360)
      wrapper.unmount()
    } finally {
      vi.useRealTimers()
    }
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

  it('mounts a stage editor with the parent project and stage scope', async () => {
    const scope = { projectId: 'project-id', stageId: 'stage-id' }
    const wrapper = mountEditor(
      projectFixture({ stages: [projectFixture({ id: 'stage-id', parent_project_id: 'project-id' })] }),
      scope,
      { ...documentFixture, stage_id: 'stage-id' },
    )
    await flushPromises()

    expect(documentsApi.get).toHaveBeenCalledWith(scope)
    expect(wrapper.find('.document-editor-view__workspace .tiptap-stub').exists()).toBe(true)
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

describe('DocumentEditorView typewriter mode', () => {
  afterEach(() => vi.unstubAllGlobals())

  function deferAnimationFrames(): { runAll: () => void } {
    const callbacks = new Map<number, FrameRequestCallback>()
    let nextId = 1
    vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => {
      const id = nextId++
      callbacks.set(id, callback)
      return id
    })
    vi.stubGlobal('cancelAnimationFrame', (id: number) => callbacks.delete(id))
    return {
      runAll: () => {
        for (const [id, callback] of callbacks) {
          callbacks.delete(id)
          callback(0)
        }
      },
    }
  }

  function tailVisualHeight(wrapper: ReturnType<typeof mountEditor>): number {
    const tail = wrapper.get<HTMLElement>('[data-nf-typewriter-tail]').element
    tail.getBoundingClientRect = () => new DOMRect(0, 0, 800, Number.parseFloat(tail.style.height) * editorZoom(tail))
    return tail.getBoundingClientRect().height
  }

  function caretCenter(): number {
    const coords = editorCoordsAtPos(editorSelection.from) as { top: number; bottom: number }
    return (coords.top + coords.bottom) / 2
  }

  async function enableTypewriter(wrapper: ReturnType<typeof mountEditor>): Promise<void> {
    await wrapper.get('.document-editor-view__typewriter-toggle').trigger('click')
    await flushPromises()
  }

  async function setDocumentZoom(wrapper: ReturnType<typeof mountEditor>, zoom: number): Promise<void> {
    const current = Number(wrapper.get('.document-editor-view__zoom button:nth-child(2)').text().replace('%', ''))
    const button = zoom > current
      ? wrapper.get('.document-editor-view__zoom button[title="Увеличить масштаб"]')
      : wrapper.get('.document-editor-view__zoom button[title="Уменьшить масштаб"]')
    for (let value = current; value !== zoom; value += zoom > current ? 10 : -10) await button.trigger('click')
    await flushPromises()
  }

  it('adds exactly one presentation-only tail when enabled and removes it when disabled', async () => {
    const wrapper = mountEditor()
    await flushPromises()
    installTypewriterGeometry(wrapper, { top: 100, clientHeight: 600, contentHeight: 1_200, caretOffset: 100 })

    expect(wrapper.find('[data-nf-typewriter-tail]').exists()).toBe(false)
    await enableTypewriter(wrapper)
    expect(wrapper.findAll('[data-nf-typewriter-tail]')).toHaveLength(1)
    const tail = wrapper.get('[data-nf-typewriter-tail]')
    expect(wrapper.get('.ProseMirror').find('[data-nf-typewriter-tail]').exists()).toBe(false)
    expect(tail.attributes('contenteditable')).toBeUndefined()
    expect(tail.attributes('aria-hidden')).toBe('true')

    await wrapper.get('.document-editor-view__typewriter-toggle').trigger('click')
    expect(wrapper.find('[data-nf-typewriter-tail]').exists()).toBe(false)
    await enableTypewriter(wrapper)
    expect(wrapper.findAll('[data-nf-typewriter-tail]')).toHaveLength(1)
    wrapper.unmount()
  })

  it.each([70, 100, 130, 140, 170, 200, 500])('keeps the visual tail at half the viewport at %i zoom', async (zoom) => {
    const wrapper = mountEditor()
    await flushPromises()
    installTypewriterGeometry(wrapper, { top: 100, clientHeight: 600, contentHeight: 1_200, caretOffset: 100 })
    const editor = wrapper.get('.nfprogress-word-editor').element as HTMLElement
    editor.style.setProperty('--nf-editor-zoom', String(zoom / 100))

    await enableTypewriter(wrapper)

    expect(tailVisualHeight(wrapper)).toBeCloseTo(300, 5)
    wrapper.unmount()
  })

  it('recalculates the visual tail after a viewport resize', async () => {
    const wrapper = mountEditor()
    await flushPromises()
    installTypewriterGeometry(wrapper, { top: 100, clientHeight: 600, contentHeight: 1_200, caretOffset: 100 })
    await enableTypewriter(wrapper)
    expect(tailVisualHeight(wrapper)).toBeCloseTo(300, 5)

    typewriterGeometry = { top: 100, clientHeight: 800, contentHeight: 1_200, caretOffset: 100 }
    window.dispatchEvent(new Event('resize'))
    await flushPromises()
    expect(tailVisualHeight(wrapper)).toBeCloseTo(400, 5)
    wrapper.unmount()
  })

  it('does not move early lines, then keeps the caret on the working line through consecutive edits', async () => {
    const wrapper = mountEditor()
    await flushPromises()
    const container = installTypewriterGeometry(wrapper, { top: 100, clientHeight: 600, contentHeight: 1_600, caretOffset: 120 })
    await enableTypewriter(wrapper)

    await wrapper.get('.tiptap-stub').trigger('click')
    expect(container.scrollTop).toBe(0)

    typewriterGeometry = { top: 100, clientHeight: 600, contentHeight: 1_600, caretOffset: 520 }
    await wrapper.get('.tiptap-stub').trigger('click')
    expect(container.scrollTop).toBeCloseTo(230, 5)

    typewriterGeometry = { top: 100, clientHeight: 600, contentHeight: 1_600, caretOffset: 560 }
    await wrapper.get('.tiptap-stub').trigger('click')
    expect(container.scrollTop).toBeCloseTo(270, 5)
    wrapper.unmount()
  })

  it('uses the native ProseMirror update event for immediate caret tracking', async () => {
    const wrapper = mountEditor()
    await flushPromises()
    const container = installTypewriterGeometry(wrapper, { top: 100, clientHeight: 600, contentHeight: 1_600, caretOffset: 520 })
    await enableTypewriter(wrapper)
    const listener = [...editorOn.mock.calls].reverse().find(([event]) => event === 'update')?.[1] as (() => void) | undefined

    listener?.()
    await flushPromises()

    expect(listener).toBeTypeOf('function')
    expect(container.scrollTop).toBeCloseTo(230, 5)
    wrapper.unmount()
  })

  it('leaves manual scrolling alone until the next edit resumes caret tracking', async () => {
    const wrapper = mountEditor()
    await flushPromises()
    const container = installTypewriterGeometry(wrapper, { top: 100, clientHeight: 600, contentHeight: 2_000, caretOffset: 800 })
    await enableTypewriter(wrapper)
    container.scrollTop = 350
    container.dispatchEvent(new Event('scroll'))
    await flushPromises()
    expect(container.scrollTop).toBe(350)

    await wrapper.get('.tiptap-stub').trigger('click')
    expect(container.scrollTop).toBeCloseTo(510, 5)
    wrapper.unmount()
  })

  it('can bring the final line to the working line while keeping its tail after the real content', async () => {
    const animationFrames = deferAnimationFrames()
    const wrapper = mountEditor()
    await flushPromises()
    const container = installTypewriterGeometry(wrapper, { top: 100, clientHeight: 600, contentHeight: 700, caretOffset: 600 })
    await enableTypewriter(wrapper)
    animationFrames.runAll()

    expect(container.scrollTop).toBeCloseTo(310, 5)
    expect(caretCenter()).toBeCloseTo(400, 5)
    expect(tailVisualHeight(wrapper)).toBeCloseTo(300, 5)
    expect(wrapper.get('[data-nf-typewriter-tail]').element.previousElementSibling?.classList.contains('word-content-multi')).toBe(true)
    wrapper.unmount()
  })

  it('does not move an early caret during initial activation', async () => {
    const animationFrames = deferAnimationFrames()
    const wrapper = mountEditor()
    await flushPromises()
    const container = installTypewriterGeometry(wrapper, { top: 100, clientHeight: 600, contentHeight: 1_200, caretOffset: 150 })

    await enableTypewriter(wrapper)
    animationFrames.runAll()

    expect(container.scrollTop).toBe(0)
    wrapper.unmount()
  })

  it.each([70, 100, 130, 140, 170, 200, 500])('positions a low caret immediately at %i zoom', async (zoom) => {
    const animationFrames = deferAnimationFrames()
    const wrapper = mountEditor()
    await flushPromises()
    const container = installTypewriterGeometry(wrapper, { top: 100, clientHeight: 600, contentHeight: 700, caretOffset: 600 })
    const editor = wrapper.get('.nfprogress-word-editor').element as HTMLElement
    editor.style.setProperty('--nf-editor-zoom', String(zoom / 100))

    await enableTypewriter(wrapper)
    animationFrames.runAll()

    expect(caretCenter()).toBeCloseTo(400, 5)
    expect(container.scrollTop).toBeGreaterThan(0)
    expect(tailVisualHeight(wrapper)).toBeCloseTo(300, 5)
    wrapper.unmount()
  })

  it('cancels a pending activation pass when the mode is switched off', async () => {
    const animationFrames = deferAnimationFrames()
    const wrapper = mountEditor()
    await flushPromises()
    const container = installTypewriterGeometry(wrapper, { top: 100, clientHeight: 600, contentHeight: 700, caretOffset: 600 })

    await enableTypewriter(wrapper)
    await wrapper.get('.document-editor-view__typewriter-toggle').trigger('click')
    const scrollTopAfterOff = container.scrollTop
    animationFrames.runAll()

    expect(wrapper.find('[data-nf-typewriter-tail]').exists()).toBe(false)
    expect(wrapper.get('.document-editor-view__typewriter-toggle').attributes('aria-pressed')).toBe('false')
    expect(container.scrollTop).toBe(scrollTopAfterOff)
    wrapper.unmount()
  })

  it('removes the tail once on off and leaves the browser-clamped position alone', async () => {
    const animationFrames = deferAnimationFrames()
    const wrapper = mountEditor()
    await flushPromises()
    const container = installTypewriterGeometry(wrapper, { top: 100, clientHeight: 600, contentHeight: 700, caretOffset: 600 })
    await enableTypewriter(wrapper)
    animationFrames.runAll()
    expect(container.scrollTop).toBeCloseTo(310, 5)

    await wrapper.get('.document-editor-view__typewriter-toggle').trigger('click')
    await flushPromises()
    const clampedScrollTop = container.scrollTop
    animationFrames.runAll()

    expect(wrapper.find('[data-nf-typewriter-tail]').exists()).toBe(false)
    expect(clampedScrollTop).toBe(100)
    expect(container.scrollTop).toBe(clampedScrollTop)
    wrapper.unmount()
  })

  it('leaves no tail or deferred scroll after rapid on-off-on-off toggling', async () => {
    const animationFrames = deferAnimationFrames()
    const wrapper = mountEditor()
    await flushPromises()
    const container = installTypewriterGeometry(wrapper, { top: 100, clientHeight: 600, contentHeight: 700, caretOffset: 600 })
    const button = wrapper.get('.document-editor-view__typewriter-toggle')

    await button.trigger('click')
    await button.trigger('click')
    await button.trigger('click')
    await button.trigger('click')
    const scrollTopAfterOff = container.scrollTop
    animationFrames.runAll()

    expect(wrapper.findAll('[data-nf-typewriter-tail]')).toHaveLength(0)
    expect(button.attributes('aria-pressed')).toBe('false')
    expect(container.scrollTop).toBe(scrollTopAfterOff)
    wrapper.unmount()
  })

  it('updates the tail on resize without recentering a manually scrolled caret', async () => {
    const animationFrames = deferAnimationFrames()
    const wrapper = mountEditor()
    await flushPromises()
    const container = installTypewriterGeometry(wrapper, { top: 100, clientHeight: 600, contentHeight: 2_000, caretOffset: 800 })
    await enableTypewriter(wrapper)
    animationFrames.runAll()
    container.scrollTop = 350

    typewriterGeometry = { top: 100, clientHeight: 800, contentHeight: 2_000, caretOffset: 800 }
    window.dispatchEvent(new Event('resize'))
    await flushPromises()

    expect(container.scrollTop).toBe(350)
    expect(tailVisualHeight(wrapper)).toBeCloseTo(400, 5)
    wrapper.unmount()
  })

  it.each([170, 200, 500])('keeps the last real caret visible at maximum scroll at %i zoom', async (zoom) => {
    const animationFrames = deferAnimationFrames()
    const wrapper = mountEditor()
    await flushPromises()
    const container = installTypewriterGeometry(wrapper, { top: 100, clientHeight: 600, contentHeight: 700, caretOffset: 700 })
    const editor = wrapper.get('.nfprogress-word-editor').element as HTMLElement
    editor.style.setProperty('--nf-editor-zoom', String(zoom / 100))

    await enableTypewriter(wrapper)
    animationFrames.runAll()
    container.scrollTop = Number.POSITIVE_INFINITY

    expect(caretCenter()).toBeCloseTo(410, 5)
    expect(tailVisualHeight(wrapper)).toBeCloseTo(300, 5)
    wrapper.unmount()
  })

  it('preserves the working-line caret while changing zoom', async () => {
    const animationFrames = deferAnimationFrames()
    const wrapper = mountEditor()
    await flushPromises()
    installTypewriterGeometry(wrapper, { top: 100, clientHeight: 600, contentHeight: 1_200, caretOffset: 600 })
    await enableTypewriter(wrapper)
    animationFrames.runAll()
    expect(caretCenter()).toBeCloseTo(400, 5)

    await setDocumentZoom(wrapper, 130)
    animationFrames.runAll()
    expect(caretCenter()).toBeCloseTo(400, 5)

    await setDocumentZoom(wrapper, 170)
    animationFrames.runAll()
    expect(caretCenter()).toBeCloseTo(400, 5)

    await setDocumentZoom(wrapper, 100)
    animationFrames.runAll()
    expect(caretCenter()).toBeCloseTo(400, 5)
    expect(editorSelection.from).toBe(1)
    wrapper.unmount()
  })

  it('keeps the document end visible while zooming from 100 to 170 and back', async () => {
    const animationFrames = deferAnimationFrames()
    const wrapper = mountEditor()
    await flushPromises()
    const container = installTypewriterGeometry(wrapper, { top: 100, clientHeight: 600, contentHeight: 700, caretOffset: 700 })
    await enableTypewriter(wrapper)
    animationFrames.runAll()
    expect(caretCenter()).toBeCloseTo(410, 5)

    await setDocumentZoom(wrapper, 170)
    animationFrames.runAll()
    expect(caretCenter()).toBeCloseTo(410, 5)
    expect(tailVisualHeight(wrapper)).toBeCloseTo(300, 5)
    container.scrollTop = Number.POSITIVE_INFINITY
    expect(caretCenter()).toBeCloseTo(410, 5)

    await setDocumentZoom(wrapper, 100)
    animationFrames.runAll()
    expect(caretCenter()).toBeCloseTo(410, 5)
    expect(tailVisualHeight(wrapper)).toBeCloseTo(300, 5)
    wrapper.unmount()
  })

  it('preserves a manually browsed reading anchor during zoom and resumes tracking on edit', async () => {
    const animationFrames = deferAnimationFrames()
    const wrapper = mountEditor()
    await flushPromises()
    const container = installTypewriterGeometry(wrapper, { top: 100, clientHeight: 600, contentHeight: 3_000, caretOffset: 1_200 })
    await enableTypewriter(wrapper)
    animationFrames.runAll()
    container.scrollTop = 100
    container.dispatchEvent(new Event('scroll'))

    await setDocumentZoom(wrapper, 170)
    animationFrames.runAll()
    expect(container.scrollTop).toBeCloseTo(170, 5)

    await wrapper.get('.tiptap-stub').trigger('click')
    expect(caretCenter()).toBeCloseTo(400, 5)
    wrapper.unmount()
  })

  it('places an icon-only typewriter button immediately before the zoom controls', async () => {
    const wrapper = mountEditor()
    await flushPromises()
    const button = wrapper.get<HTMLButtonElement>('.document-editor-view__typewriter-toggle')

    expect(button.attributes('aria-pressed')).toBe('false')
    expect(button.attributes('title')).toBe('Включить режим печатной машинки')
    expect(button.text()).toBe('')
    expect(button.find('svg.document-editor-view__typewriter-icon').exists()).toBe(true)
    expect(button.element.nextElementSibling?.classList.contains('document-editor-view__zoom')).toBe(true)
    const offStyle = getComputedStyle(button.element)
    const offBox = [offStyle.boxSizing, offStyle.width, offStyle.height, offStyle.padding, offStyle.borderWidth]

    await button.trigger('click')
    expect(button.attributes('aria-pressed')).toBe('true')
    expect(button.attributes('title')).toBe('Выключить режим печатной машинки')
    expect(button.classes()).toContain('document-editor-view__typewriter-toggle--active')
    const onStyle = getComputedStyle(button.element)
    expect([onStyle.boxSizing, onStyle.width, onStyle.height, onStyle.padding, onStyle.borderWidth]).toEqual(offBox)
    wrapper.unmount()
  })
})
