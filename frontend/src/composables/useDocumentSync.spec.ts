import { flushPromises, mount } from '@vue/test-utils'
import { defineComponent } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { documentsApi } from '@/api/documents'
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
  },
}))

vi.mock('@/services/dataChanges', () => ({ announceDataChange: vi.fn() }))
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
  beforeEach(() => vi.clearAllMocks())

  it('does not let a slow initial read erase text entered in the editor', async () => {
    let finishLoad: ((value: ProjectDocument) => void) | undefined
    vi.mocked(documentsApi.get).mockReturnValue(new Promise((resolve) => { finishLoad = resolve }))
    const wrapper = mount(defineComponent({
      setup() {
        const sync = useDocumentSync({ projectId: 'project-id' }, async () => 'nfprogress')
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

  it('keeps local content when the save response contains only stale metadata', async () => {
    vi.mocked(documentsApi.get).mockResolvedValue(documentResponse())
    vi.mocked(documentsApi.save).mockResolvedValue(documentResponse())
    const wrapper = mount(defineComponent({
      setup() {
        const sync = useDocumentSync({ projectId: 'project-id' }, async () => 'nfprogress')
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
        const sync = useDocumentSync({ projectId: 'project-id' }, async () => 'nfprogress')
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
})
