import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const invokeMock = vi.hoisted(() => vi.fn())

vi.mock('@tauri-apps/api/core', () => ({ invoke: invokeMock }))
vi.mock('@/platform/runtime', () => ({ currentPlatform: () => 'tauri' }))

import { documentsApi } from './documents'

const projectScope = { projectId: 'project-id' }
const stageScope = { projectId: 'project-id', stageId: 'stage-id' }
const content = { type: 'doc' as const, content: [{ type: 'paragraph' }] }

describe('documentsApi native command contract', () => {
  beforeEach(() => {
    invokeMock.mockReset()
    invokeMock.mockResolvedValue({})
  })

  afterEach(() => vi.restoreAllMocks())

  it('passes project and stage scopes using the Rust command argument wrappers', async () => {
    await documentsApi.get(projectScope)
    await documentsApi.get(stageScope)

    expect(invokeMock).toHaveBeenNthCalledWith(1, 'get_document', {
      scope: { projectId: 'project-id', stageId: null },
    })
    expect(invokeMock).toHaveBeenNthCalledWith(2, 'get_document', {
      scope: { projectId: 'project-id', stageId: 'stage-id' },
    })
  })

  it('keeps the argument shape of native document and Word commands aligned with Rust', async () => {
    await documentsApi.save(stageScope, content)
    await documentsApi.link(stageScope, '/tmp/document.docx')
    await documentsApi.writeDocx(stageScope, 'base64')
    await documentsApi.writeDocxContent(stageScope, content)
    await documentsApi.parseWord(new Uint8Array([1, 2]), 'document.docx')
    await documentsApi.external(stageScope)
    await documentsApi.acceptWord(stageScope, content, 'hash')
    await documentsApi.recordProgress(stageScope, content)

    expect(invokeMock).toHaveBeenNthCalledWith(1, 'save_document', {
      command: { projectId: 'project-id', stageId: 'stage-id', content },
    })
    expect(invokeMock).toHaveBeenNthCalledWith(2, 'bind_document_file', {
      command: { projectId: 'project-id', stageId: 'stage-id', path: '/tmp/document.docx' },
    })
    expect(invokeMock).toHaveBeenNthCalledWith(3, 'write_document_word', {
      command: { projectId: 'project-id', stageId: 'stage-id', contentBase64: 'base64' },
    })
    expect(invokeMock).toHaveBeenNthCalledWith(4, 'write_document_word_content', {
      projectId: 'project-id', stageId: 'stage-id', content,
    })
    expect(invokeMock).toHaveBeenNthCalledWith(5, 'parse_word_document', {
      command: { bytes: [1, 2], filename: 'document.docx' },
    })
    expect(invokeMock).toHaveBeenNthCalledWith(6, 'read_document_external', {
      scope: { projectId: 'project-id', stageId: 'stage-id' },
    })
    expect(invokeMock).toHaveBeenNthCalledWith(7, 'accept_document_external', {
      command: { projectId: 'project-id', stageId: 'stage-id', content, sourceHash: 'hash' },
    })
    expect(invokeMock).toHaveBeenNthCalledWith(8, 'record_document_progress', {
      command: { projectId: 'project-id', stageId: 'stage-id', content },
    })
  })
})
