import { flushPromises, mount } from '@vue/test-utils'
import { defineComponent } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { documentsApi } from '@/api/documents'
import { currentPlatform } from '@/platform/runtime'
import { blobToBase64, exportDocx, importDocx } from '@/services/documentDocx'
import type { ProjectDocument, TiptapDocument } from '@/types/documents'

import { useDocumentSync } from './useDocumentSync'

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

vi.mock('@/services/dataChanges', () => ({ announceDataChange: vi.fn() }))
vi.mock('@/platform/runtime', () => ({ currentPlatform: vi.fn(() => 'web') }))
vi.mock('@/services/documentDocx', () => ({
  blobToBase64: vi.fn(),
  exportDocx: vi.fn(),
  importDocx: vi.fn(),
}))

const emptyDocument: TiptapDocument = { type: 'doc', content: [{ type: 'paragraph' }] }
const editedDocument: TiptapDocument = {
  type: 'doc',
  content: [{ type: 'paragraph', content: [{ type: 'text', text: 'Новая глава' }] }],
}

function documentResponse(content = emptyDocument): ProjectDocument {
  return {
    project_id: 'project-id',
    stage_id: null,
    content,
    exists: content !== emptyDocument,
    updated_at: null,
    docx_path: null,
    sync_state: 'unlinked',
    last_synced_hash: null,
    last_synced_at: null,
    local_dirty: false,
    word_dirty: false,
    symbols: 0,
    has_content: content !== emptyDocument,
  }
}

describe('useDocumentSync', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(currentPlatform).mockReturnValue('web')
  })

  it('does not let a slow initial read erase text entered in the editor', async () => {
    let finishLoad: ((value: ProjectDocument) => void) | undefined
    vi.mocked(documentsApi.get).mockReturnValue(new Promise((resolve) => { finishLoad = resolve }))
    const wrapper = mount(defineComponent({
      setup() {
        const sync = useDocumentSync({ projectId: 'project-id' })
        return { sync }
      },
      template: '<button @click="sync.scheduleSave(edited)">edit</button>',
      data: () => ({ edited: editedDocument }),
    }))

    await wrapper.get('button').trigger('click')
    finishLoad?.(documentResponse())
    await flushPromises()

    expect(wrapper.vm.sync.content.value).toEqual(editedDocument)
    wrapper.unmount()
  })

  it('does not save transient empty content when unmounted before the initial load completes', () => {
    vi.mocked(documentsApi.get).mockReturnValue(new Promise(() => undefined))
    const wrapper = mount(defineComponent({
      setup() { return { sync: useDocumentSync({ projectId: 'project-id' }) } },
      template: '<div />',
    }))

    wrapper.unmount()

    expect(documentsApi.save).not.toHaveBeenCalled()
  })

  it('keeps loaded non-empty content authoritative through unmount saving', async () => {
    const loadedDocument = documentResponse(editedDocument)
    vi.mocked(documentsApi.get).mockResolvedValue(loadedDocument)
    vi.mocked(documentsApi.save).mockResolvedValue(loadedDocument)
    const wrapper = mount(defineComponent({
      setup() { return { sync: useDocumentSync({ projectId: 'project-id' }) } },
      template: '<div />',
    }))
    await flushPromises()

    expect(wrapper.vm.sync.content.value).toEqual(editedDocument)
    wrapper.unmount()
    await flushPromises()

    expect(documentsApi.save).toHaveBeenCalledWith({ projectId: 'project-id' }, editedDocument)
  })

  it('keeps local content when the save response contains only stale metadata', async () => {
    vi.mocked(documentsApi.get).mockResolvedValue(documentResponse())
    vi.mocked(documentsApi.save).mockResolvedValue(documentResponse())
    const wrapper = mount(defineComponent({
      setup() {
        const sync = useDocumentSync({ projectId: 'project-id' })
        return { sync }
      },
      template: '<button @click="sync.scheduleSave(edited)">edit</button>',
      data: () => ({ edited: editedDocument }),
    }))

    await flushPromises()
    await wrapper.get('button').trigger('click')
    await wrapper.vm.sync.save(false)

    expect(documentsApi.save).toHaveBeenCalledWith({ projectId: 'project-id' }, editedDocument)
    expect(wrapper.vm.sync.content.value).toEqual(editedDocument)
    wrapper.unmount()
  })

  it('records the explicit snapshot after an older autosave finishes', async () => {
    const staleDocument: TiptapDocument = {
      type: 'doc',
      content: [{ type: 'paragraph', content: [{ type: 'text', text: 'Старый текст' }] }],
    }
    let finishAutosave: ((value: ProjectDocument) => void) | undefined
    vi.mocked(documentsApi.get).mockResolvedValue(documentResponse())
    vi.mocked(documentsApi.save).mockReturnValue(new Promise((resolve) => { finishAutosave = resolve }))
    vi.mocked(documentsApi.recordProgress).mockResolvedValue({
      changed: true,
      symbols: 11,
      progress: null,
      document: documentResponse(editedDocument),
    })
    const wrapper = mount(defineComponent({
      setup() {
        const sync = useDocumentSync({ projectId: 'project-id' })
        return { sync }
      },
      template: '<div />',
    }))
    await flushPromises()

    wrapper.vm.sync.setContent(staleDocument)
    const autosave = wrapper.vm.sync.save(false)
    wrapper.vm.sync.setContent(editedDocument)
    const record = wrapper.vm.sync.saveAndRecord()

    expect(documentsApi.recordProgress).not.toHaveBeenCalled()
    finishAutosave?.(documentResponse(staleDocument))
    await autosave
    await record

    expect(documentsApi.recordProgress).toHaveBeenCalledWith({ projectId: 'project-id' }, editedDocument)
    expect(wrapper.vm.sync.content.value).toEqual(editedDocument)
    wrapper.unmount()
  })

  it('writes the current JSON to a linked Word document in web and desktop runtimes', async () => {
    const linkedDocument = { ...documentResponse(editedDocument), docx_path: '/tmp/document.docx' }
    vi.mocked(documentsApi.get).mockResolvedValue(linkedDocument)
    vi.mocked(documentsApi.save).mockResolvedValue(linkedDocument)
    vi.mocked(documentsApi.writeDocx).mockResolvedValue(linkedDocument)
    vi.mocked(documentsApi.writeDocxContent).mockResolvedValue(linkedDocument)
    vi.mocked(exportDocx).mockResolvedValue(new Blob(['docx']))
    vi.mocked(blobToBase64).mockResolvedValue('encoded-docx')
    const wrapper = mount(defineComponent({
      setup() { return { sync: useDocumentSync({ projectId: 'project-id' }) } },
      template: '<div />',
    }))
    await flushPromises()

    await wrapper.vm.sync.save(false, editedDocument)
    expect(exportDocx).toHaveBeenCalledWith(editedDocument)
    expect(documentsApi.writeDocx).toHaveBeenCalledWith({ projectId: 'project-id' }, 'encoded-docx')

    vi.mocked(currentPlatform).mockReturnValue('tauri')
    await wrapper.vm.sync.save(false, editedDocument)
    expect(documentsApi.writeDocxContent).toHaveBeenCalledWith({ projectId: 'project-id' }, editedDocument)
    wrapper.unmount()
  })

  it('does not reimport the hash produced by its own linked Word write', async () => {
    const linkedDocument = {
      ...documentResponse(editedDocument),
      docx_path: '/tmp/document.docx',
      last_synced_hash: 'self-write-hash',
    }
    vi.mocked(documentsApi.get).mockResolvedValue(linkedDocument)
    vi.mocked(documentsApi.external).mockResolvedValue({
      state: 'external_changed',
      content_base64: 'AQI=',
      hash: 'self-write-hash',
    })
    const wrapper = mount(defineComponent({
      setup() { return { sync: useDocumentSync({ projectId: 'project-id' }) } },
      template: '<div />',
    }))
    await flushPromises()

    expect(await wrapper.vm.sync.checkExternal()).toBeUndefined()
    expect(importDocx).not.toHaveBeenCalled()
    expect(documentsApi.parseWord).not.toHaveBeenCalled()
    expect(wrapper.vm.sync.content.value).toEqual(editedDocument)
    wrapper.unmount()
  })

  it('ignores a synced polling response even if it contains stale bytes', async () => {
    const linkedDocument = {
      ...documentResponse(editedDocument),
      docx_path: '/tmp/document.docx',
      last_synced_hash: 'accepted-hash',
    }
    vi.mocked(documentsApi.get).mockResolvedValue(linkedDocument)
    vi.mocked(documentsApi.external).mockResolvedValue({
      state: 'synced',
      content_base64: 'AQI=',
      hash: 'stale-response-hash',
    })
    const wrapper = mount(defineComponent({
      setup() { return { sync: useDocumentSync({ projectId: 'project-id' }) } },
      template: '<div />',
    }))
    await flushPromises()

    expect(await wrapper.vm.sync.checkExternal()).toBeUndefined()
    expect(importDocx).not.toHaveBeenCalled()
    expect(documentsApi.parseWord).not.toHaveBeenCalled()
    wrapper.unmount()
  })

  it('continues importing a real external Word hash change', async () => {
    const linkedDocument = {
      ...documentResponse(emptyDocument),
      docx_path: '/tmp/document.docx',
      last_synced_hash: 'self-write-hash',
    }
    vi.mocked(documentsApi.get).mockResolvedValue(linkedDocument)
    vi.mocked(documentsApi.external).mockResolvedValue({
      state: 'external_changed',
      content_base64: 'AQI=',
      hash: 'user-edit-hash',
    })
    vi.mocked(currentPlatform).mockReturnValue('tauri')
    vi.mocked(documentsApi.parseWord).mockResolvedValue({ content: editedDocument, symbols: 11, hash: 'user-edit-hash' })
    const wrapper = mount(defineComponent({
      setup() { return { sync: useDocumentSync({ projectId: 'project-id' }) } },
      template: '<div />',
    }))
    await flushPromises()

    expect(await wrapper.vm.sync.checkExternal()).toEqual({ state: 'external_changed', content: editedDocument, hash: 'user-edit-hash' })
    expect(documentsApi.parseWord).toHaveBeenCalledOnce()
    wrapper.unmount()
  })

  it('keeps native JSON and web HTML external Word import paths', async () => {
    const linkedDocument = { ...documentResponse(editedDocument), docx_path: '/tmp/document.docx' }
    vi.mocked(documentsApi.get).mockResolvedValue(linkedDocument)
    vi.mocked(documentsApi.external).mockResolvedValue({ state: 'external_changed', content_base64: 'AQI=', hash: 'word-hash' })
    vi.mocked(documentsApi.parseWord).mockResolvedValue({ content: editedDocument, symbols: 11, hash: 'parsed-hash' })
    vi.mocked(importDocx).mockResolvedValue('<p>Новая глава</p>')
    const wrapper = mount(defineComponent({
      setup() { return { sync: useDocumentSync({ projectId: 'project-id' }) } },
      template: '<div />',
    }))
    await flushPromises()

    expect(await wrapper.vm.sync.checkExternal()).toEqual({ state: 'external_changed', html: '<p>Новая глава</p>', hash: 'word-hash' })
    vi.mocked(currentPlatform).mockReturnValue('tauri')
    expect(await wrapper.vm.sync.checkExternal()).toEqual({ state: 'external_changed', content: editedDocument, hash: 'word-hash' })
    expect(documentsApi.parseWord).toHaveBeenCalledWith(new Uint8Array([1, 2]), 'document.docx')
    wrapper.unmount()
  })
})
