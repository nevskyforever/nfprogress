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

vi.mock('./editor/editorFeatureFlags', () => ({ USE_CUSTOM_DOCUMENT_EDITOR: true }))
vi.mock('vue-router', () => ({
  onBeforeRouteLeave,
  useRouter: () => ({ push: vi.fn() }),
}))
vi.mock('tiptap-ui-kit', () => ({
  createI18n: vi.fn(),
  setTheme: vi.fn(),
  TiptapProEditor: { template: '<div />' },
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

function mountEditor() {
  vi.mocked(projectsApi.get).mockResolvedValue(projectFixture())
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
    await vi.advanceTimersByTimeAsync(0)
    await flushPromises()

    const api = wrapper.getComponent(NFDocumentEditor).vm as unknown as CustomEditorExpose
    expect(api.getSelection()).toBe(4)
    expect(api.getScrollContainer()?.scrollTop).toBe(37)
    wrapper.unmount()
  })
})
