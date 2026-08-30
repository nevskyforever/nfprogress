import { onBeforeUnmount, onMounted, ref } from 'vue'
import { documentsApi } from '@/api/documents'
import { blobToBase64, exportDocx, importDocx } from '@/services/documentDocx'
import type { DocumentScope, ProjectDocument, TiptapDocument } from '@/types/documents'

export type ConflictChoice = 'nfprogress' | 'word' | 'both'

export function useDocumentSync(scope: DocumentScope, onConflict: () => Promise<ConflictChoice>) {
  const documentState = ref<ProjectDocument | null>(null)
  const content = ref<TiptapDocument>({ type: 'doc', content: [{ type: 'paragraph' }] })
  const status = ref('')
  let saveTimer: number | undefined
  let watchTimer: number | undefined

  async function writeLinkedWord() {
    if (!documentState.value?.docx_path) return
    documentState.value = await documentsApi.writeDocx(scope, await blobToBase64(await exportDocx(content.value)))
  }
  async function save() {
    documentState.value = await documentsApi.save(scope, content.value)
    await writeLinkedWord()
    status.value = 'Сохранено'
  }
  function scheduleSave(next: TiptapDocument) {
    content.value = next
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
    content.value = next
    documentState.value = await documentsApi.acceptWord(scope, next, hash)
    status.value = 'Изменения Word импортированы'
  }
  async function link(path: string) { documentState.value = await documentsApi.link(scope, path); await writeLinkedWord() }
  async function downloadWordCopy() {
    const blob = await exportDocx(content.value); const url = URL.createObjectURL(blob); const anchor = document.createElement('a')
    anchor.href = url; anchor.download = 'nfprogress-conflict-copy.docx'; anchor.click(); URL.revokeObjectURL(url)
  }
  onMounted(async () => {
    documentState.value = await documentsApi.get(scope); content.value = documentState.value.content
  })
  onBeforeUnmount(() => { window.clearTimeout(saveTimer); window.clearInterval(watchTimer); void save() })
  return { content, documentState, status, save, scheduleSave, link, writeLinkedWord, checkExternal, acknowledgeExternal }
}
