import { onBeforeUnmount, onMounted, ref } from 'vue'
import { documentsApi } from '@/api/documents'
import { announceDataChange } from '@/services/dataChanges'
import { blobToBase64, exportDocx, importDocx } from '@/services/documentDocx'
import type { DocumentProgressResult, DocumentScope, ProjectDocument, TiptapDocument } from '@/types/documents'

export type ConflictChoice = 'nfprogress' | 'word' | 'both'

export function useDocumentSync(scope: DocumentScope, onConflict: () => Promise<ConflictChoice>) {
  const documentState = ref<ProjectDocument | null>(null)
  const content = ref<TiptapDocument>({ type: 'doc', content: [{ type: 'paragraph' }] })
  const status = ref('')
  let saveTimer: number | undefined
  let watchTimer: number | undefined
  let localRevision = 0
  let persistenceQueue: Promise<void> = Promise.resolve()

  function copyContent(value: TiptapDocument): TiptapDocument {
    return JSON.parse(JSON.stringify(value)) as TiptapDocument
  }
  function enqueuePersistence<T>(operation: () => Promise<T>): Promise<T> {
    const queued = persistenceQueue.catch(() => undefined).then(operation)
    persistenceQueue = queued.then(() => undefined, () => undefined)
    return queued
  }
  async function writeLinkedWord(next = content.value) {
    if (!documentState.value?.docx_path) return
    documentState.value = await documentsApi.writeDocx(scope, await blobToBase64(await exportDocx(next)))
  }
  function save(announce = true): Promise<void> {
    window.clearTimeout(saveTimer)
    saveTimer = undefined
    return enqueuePersistence(async () => {
      // A queued autosave always snapshots the newest draft when it starts.
      // This prevents an older request from completing after a newer one.
      const snapshot = copyContent(content.value)
      documentState.value = await documentsApi.save(scope, snapshot)
      await writeLinkedWord(snapshot)
      if (announce) announceDataChange('projects')
      status.value = 'Сохранено'
    })
  }
  function saveAndRecord(): Promise<DocumentProgressResult> {
    window.clearTimeout(saveTimer)
    saveTimer = undefined
    // Unlike a regular autosave, an explicit record must use the exact draft
    // visible when the user pressed the button.
    const snapshot = copyContent(content.value)
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
  async function checkExternal(): Promise<{ html: string; hash: string } | undefined> {
    if (!documentState.value?.docx_path) return
    const external = await documentsApi.external(scope)
    if (!external.content_base64 || !external.hash) return
    if (external.state === 'conflict') {
      const choice = await onConflict()
      if (choice === 'nfprogress') { await writeLinkedWord(); return undefined }
      if (choice === 'both') await downloadWordCopy()
    }
    const bytes = Uint8Array.from(atob(external.content_base64), (letter) => letter.charCodeAt(0))
    return { html: await importDocx(bytes.buffer), hash: external.hash }
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
    documentState.value = loaded
    // A slow initial read (including a migration-backed read) must not replace
    // text entered while it was in flight.  The local edit is already the
    // current source of truth and its autosave will persist it.
    if (revisionAtStart === localRevision) content.value = loaded.content
  })
  onBeforeUnmount(() => { window.clearTimeout(saveTimer); window.clearInterval(watchTimer); void save() })
  return { content, documentState, status, save, saveAndRecord, setContent, scheduleSave, link, writeLinkedWord, checkExternal, acknowledgeExternal }
}
