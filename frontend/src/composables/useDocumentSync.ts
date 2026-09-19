import { onBeforeUnmount, onMounted, ref } from 'vue'
import { documentsApi } from '@/api/documents'
import { currentPlatform } from '@/platform/runtime'
import { announceDataChange } from '@/services/dataChanges'
import { blobToBase64, exportDocx, importDocx } from '@/services/documentDocx'
import type { DocumentProgressResult, DocumentScope, ProjectDocument, TiptapDocument } from '@/types/documents'

export type ConflictChoice = 'nfprogress' | 'word' | 'both'
export type ExternalDocumentChange = {
  state: string
  html?: string
  content?: TiptapDocument
  hash: string
}

export function useDocumentSync(scope: DocumentScope) {
  const documentState = ref<ProjectDocument | null>(null)
  const content = ref<TiptapDocument>({ type: 'doc', content: [{ type: 'paragraph' }] })
  const status = ref('')
  let saveTimer: number | undefined
  let watchTimer: number | undefined
  let localRevision = 0
  let initialLoadComplete = false
  let persistenceQueue: Promise<void> = Promise.resolve()

  function copyContent(value: TiptapDocument): TiptapDocument {
    return JSON.parse(JSON.stringify(value)) as TiptapDocument
  }
  function hasText(value: unknown): boolean {
    if (!value || typeof value !== 'object') return false
    const node = value as { text?: unknown; content?: unknown }
    return (typeof node.text === 'string' && node.text.length > 0)
      || (Array.isArray(node.content) && node.content.some(hasText))
  }
  function enqueuePersistence<T>(operation: () => Promise<T>): Promise<T> {
    const queued = persistenceQueue.catch(() => undefined).then(operation)
    persistenceQueue = queued.then(() => undefined, () => undefined)
    return queued
  }
  async function writeLinkedWord(next = content.value) {
    if (!documentState.value?.docx_path) return
    documentState.value = currentPlatform() === 'tauri'
      ? await documentsApi.writeDocxContent(scope, next)
      : await documentsApi.writeDocx(scope, await blobToBase64(await exportDocx(next)))
  }
  function save(announce = true, requestedContent?: TiptapDocument): Promise<void> {
    window.clearTimeout(saveTimer)
    saveTimer = undefined
    const requestedSnapshot = requestedContent ? copyContent(requestedContent) : undefined
    const pendingSnapshot = requestedSnapshot ?? content.value
    if (!initialLoadComplete && localRevision === 0 && !hasText(pendingSnapshot)) {
      return Promise.resolve()
    }
    return enqueuePersistence(async () => {
      // A queued autosave snapshots the newest draft when it starts. An
      // explicit save passes its own snapshot, captured from the editor when
      // the user initiated the action.
      const snapshot = requestedSnapshot ?? copyContent(content.value)
      documentState.value = await documentsApi.save(scope, snapshot)
      await writeLinkedWord(snapshot)
      if (announce) announceDataChange('projects')
      status.value = 'Сохранено'
    })
  }
  function saveAndRecord(requestedContent = content.value): Promise<DocumentProgressResult> {
    window.clearTimeout(saveTimer)
    saveTimer = undefined
    // Unlike a regular autosave, an explicit record must use the exact draft
    // visible when the user pressed the button.
    const snapshot = copyContent(requestedContent)
    return enqueuePersistence(async () => {
      const result = await documentsApi.recordProgress(scope, snapshot)
      if (result.document) documentState.value = result.document
      await writeLinkedWord(snapshot)
      status.value = 'Сохранено'
      return result
    })
  }
  function setContent(next: TiptapDocument) {
    localRevision += 1
    content.value = next
  }
  function scheduleSave(next: TiptapDocument) {
    setContent(next)
    window.clearTimeout(saveTimer)
    saveTimer = window.setTimeout(() => void save().catch(() => { status.value = 'Не удалось сохранить' }), 700)
  }
  async function checkExternal(): Promise<ExternalDocumentChange | undefined> {
    if (!documentState.value?.docx_path) return
    const external = await documentsApi.external(scope)
    if (!external.content_base64 || !external.hash) return
    // Native writes persist their resulting file hash. Even if a delayed or
    // stale polling response still includes the bytes, never parse and apply
    // the exact version NFProgress has just written or already accepted.
    if (external.hash === documentState.value.last_synced_hash) return
    if (!['external_changed', 'word_changed', 'conflict'].includes(external.state)) return
    const bytes = Uint8Array.from(atob(external.content_base64), (letter) => letter.charCodeAt(0))
    if (currentPlatform() === 'tauri') {
      const parsed = await documentsApi.parseWord(bytes, 'document.docx')
      return { state: external.state, content: parsed.content, hash: external.hash }
    }
    return { state: external.state, html: await importDocx(bytes.buffer), hash: external.hash }
  }
  async function acknowledgeExternal(next: TiptapDocument, hash: string) {
    setContent(next)
    documentState.value = await documentsApi.acceptWord(scope, next, hash)
    announceDataChange('projects')
    status.value = 'Изменения Word импортированы'
  }
  async function link(path: string) { documentState.value = await documentsApi.link(scope, path); await writeLinkedWord() }
  async function downloadWordCopy() {
    const blob = await exportDocx(content.value); const url = URL.createObjectURL(blob); const anchor = document.createElement('a')
    anchor.href = url; anchor.download = 'nfprogress-conflict-copy.docx'; anchor.click(); URL.revokeObjectURL(url)
  }
  onMounted(async () => {
    const revisionAtStart = localRevision
    const loaded = await documentsApi.get(scope)
    // A slow initial read (including a migration-backed read) must not replace
    // text entered while it was in flight.  The local edit is already the
    // current source of truth and its autosave will persist it.
    if (revisionAtStart === localRevision) content.value = loaded.content
    documentState.value = loaded
    initialLoadComplete = true
  })
  onBeforeUnmount(() => {
    window.clearTimeout(saveTimer)
    window.clearInterval(watchTimer)
    void save().catch(() => { status.value = 'Не удалось сохранить' })
  })
  return { content, documentState, status, save, saveAndRecord, setContent, scheduleSave, link, writeLinkedWord, checkExternal, acknowledgeExternal, downloadWordCopy }
}
