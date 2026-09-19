import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { documentsApi } from '@/api/documents'
import { projectsApi } from '@/api/projects'
import { projectFixture } from '@/test/fixtures'
import type { ProjectDocument, TiptapDocument } from '@/types/documents'
import NFDocumentEditor from './editor/NFDocumentEditor.vue'
import DocumentEditorView from './DocumentEditorView.vue'

const { onBeforeRouteLeave } = vi.hoisted(() => ({ onBeforeRouteLeave: vi.fn() }))
const positionStorage = new Map<string, string>()

vi.mock('vue-router', () => ({
  onBeforeRouteLeave,
  useRouter: () => ({ push: vi.fn() }),
}))
vi.mock('@/api/projects', () => ({ projectsApi: { get: vi.fn() } }))
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

const initialContent: TiptapDocument = {
  type: 'doc',
  content: [{ type: 'paragraph', content: [{ type: 'text', text: 'Исходный текст' }] }],
}
const documentFixture: ProjectDocument = {
  project_id: 'project-id',
  stage_id: null,
  content: initialContent,
  exists: true,
  updated_at: null,
  docx_path: null,
  sync_state: 'unlinked',
  last_synced_hash: null,
  last_synced_at: null,
  local_dirty: false,
  word_dirty: false,
  symbols: 14,
  has_content: true,
}

type CustomEditorExpose = {
  getJSON: () => TiptapDocument
  getSelection: () => number | null
  getScrollContainer: () => HTMLElement | null
  setContent: (content: TiptapDocument, emitUpdate?: boolean) => void
}

function mountEditor(project = projectFixture()) {
  vi.mocked(projectsApi.get).mockResolvedValue(project)
  vi.mocked(documentsApi.get).mockResolvedValue(documentFixture)
  vi.mocked(documentsApi.save).mockResolvedValue(documentFixture)
  return mount(DocumentEditorView, {
    props: { scope: { projectId: 'project-id' }, title: 'Текст' },
    global: { plugins: [createPinia()] },
  })
}

describe('DocumentEditorView custom editor integration', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    positionStorage.clear()
    Object.defineProperty(window, 'localStorage', {
      configurable: true,
      value: {
        getItem: (key: string) => positionStorage.get(key) ?? null,
        removeItem: (key: string) => { positionStorage.delete(key) },
        setItem: (key: string, value: string) => { positionStorage.set(key, value) },
      },
    })
    vi.mocked(documentsApi.get).mockReset()
    vi.mocked(documentsApi.save).mockReset()
    vi.mocked(documentsApi.recordProgress).mockReset()
    vi.mocked(documentsApi.external).mockReset()
    vi.mocked(projectsApi.get).mockReset()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('loads the document and autosaves emitted JSON through useDocumentSync', async () => {
    const wrapper = mountEditor()
    await flushPromises()
    const customEditor = wrapper.getComponent(NFDocumentEditor)
    const api = customEditor.vm as unknown as CustomEditorExpose
    expect(api.getJSON()).toMatchObject(initialContent)

    const next: TiptapDocument = {
      type: 'doc',
      content: [{ type: 'paragraph', content: [{ type: 'text', text: 'Черновик' }] }],
    }
    api.setContent(next, true)
    await vi.advanceTimersByTimeAsync(700)

    expect(documentsApi.save).toHaveBeenCalledTimes(1)
    expect(vi.mocked(documentsApi.save).mock.calls[0]?.[0]).toEqual({ projectId: 'project-id' })
    expect(vi.mocked(documentsApi.save).mock.calls[0]?.[1]).toMatchObject(next)
    wrapper.unmount()
  })

  it('restores the custom editor selection and viewport scroll position', async () => {
    window.localStorage.setItem(
      'nfprogress:document-position:project-id:project',
      JSON.stringify({ selection: 4, scrollTop: 37 }),
    )
    const wrapper = mountEditor()
    await flushPromises()
    await vi.advanceTimersByTimeAsync(50)
    await flushPromises()

    const api = wrapper.getComponent(NFDocumentEditor).vm as unknown as CustomEditorExpose
    expect(api.getSelection()).toBe(4)
    expect(api.getScrollContainer()?.scrollTop).toBe(37)
    expect(wrapper.getComponent(NFDocumentEditor).props('zoom')).toBe(100)
    expect(wrapper.getComponent(NFDocumentEditor).props('typewriterMode')).toBe(false)
    wrapper.unmount()
  })

  it('restores zoom and Typewriter before the saved selection and scroll position', async () => {
    window.localStorage.setItem(
      'nfprogress:document-position:project-id:project',
      JSON.stringify({ selection: 6, scrollTop: 83, zoom: 170, typewriterMode: true }),
    )
    const wrapper = mountEditor()
    await flushPromises()

    const customEditor = wrapper.getComponent(NFDocumentEditor)
    expect(customEditor.props('zoom')).toBe(170)
    expect(customEditor.props('typewriterMode')).toBe(true)
    expect(wrapper.get('.document-editor-view__typewriter-toggle').attributes('aria-pressed')).toBe('true')
    expect(wrapper.get('.document-editor-view__zoom').text()).toContain('170%')

    await vi.advanceTimersByTimeAsync(50)
    await flushPromises()
    const api = customEditor.vm as unknown as CustomEditorExpose
    expect(api.getSelection()).toBe(6)
    expect(api.getScrollContainer()?.scrollTop).toBe(83)
    wrapper.unmount()
  })

  it('repairs invalid optional view state fields with backward-compatible defaults', async () => {
    window.localStorage.setItem(
      'nfprogress:document-position:project-id:project',
      JSON.stringify({ selection: 3, scrollTop: 21, zoom: 900, typewriterMode: 'yes' }),
    )
    const wrapper = mountEditor()
    await flushPromises()
    await vi.advanceTimersByTimeAsync(50)
    await flushPromises()

    const customEditor = wrapper.getComponent(NFDocumentEditor)
    const api = customEditor.vm as unknown as CustomEditorExpose
    expect(customEditor.props('zoom')).toBe(100)
    expect(customEditor.props('typewriterMode')).toBe(false)
    expect(api.getSelection()).toBe(3)
    expect(api.getScrollContainer()?.scrollTop).toBe(21)
    wrapper.unmount()
  })

  it('saves zoom and Typewriter through the existing per-document view state', async () => {
    const wrapper = mountEditor()
    await flushPromises()

    await wrapper.get('.document-editor-view__zoom button:last-child').trigger('click')
    await wrapper.get('.document-editor-view__typewriter-toggle').trigger('click')
    await vi.advanceTimersByTimeAsync(250)

    expect(JSON.parse(positionStorage.get('nfprogress:document-position:project-id:project') ?? '{}')).toMatchObject({
      version: 1,
      zoom: 110,
      typewriterMode: true,
    })
    wrapper.unmount()
  })

  it('keeps document and daily-goal progress in the shared status bar', async () => {
    const wrapper = mountEditor(projectFixture({
      total: 0,
      goal: 100,
      today_goal: 100,
      plan_daily_goal: 100,
      added_today: 40,
    }))
    await flushPromises()

    expect(wrapper.get('.document-editor-view__unit-count').text()).toContain('14 / 100')
    expect(wrapper.get('[role="progressbar"]').attributes('aria-valuenow')).toBe('54')
    wrapper.unmount()
  })

  it('records the exact current editor snapshot through the existing progress flow', async () => {
    vi.mocked(documentsApi.recordProgress).mockResolvedValue({
      changed: true,
      symbols: 8,
      progress: null,
      document: documentFixture,
    })
    const wrapper = mountEditor(projectFixture({ total: 0 }))
    await flushPromises()
    const api = wrapper.getComponent(NFDocumentEditor).vm as unknown as CustomEditorExpose
    const next: TiptapDocument = {
      type: 'doc',
      content: [{ type: 'paragraph', content: [{ type: 'text', text: 'Черновик' }] }],
    }
    api.setContent(next, true)
    await wrapper.vm.$nextTick()

    const recordButton = wrapper.findAll('button').find((button) => button.text().includes('Добавить запись'))
    expect(recordButton).toBeDefined()
    await recordButton!.trigger('click')
    await flushPromises()

    expect(documentsApi.recordProgress).toHaveBeenCalledTimes(1)
    expect(vi.mocked(documentsApi.recordProgress).mock.calls[0]?.[0]).toEqual({ projectId: 'project-id' })
    expect(vi.mocked(documentsApi.recordProgress).mock.calls[0]?.[1]).toMatchObject(next)
    wrapper.unmount()
  })
})
