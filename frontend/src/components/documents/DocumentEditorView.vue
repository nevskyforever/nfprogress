<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import type { JSONContent } from '@tiptap/core'
import { TiptapProEditor, setTheme, type TiptapProEditorExpose } from 'tiptap-ui-kit'
import 'tiptap-ui-kit/style.css'
import { pickDesktopWordFile } from '@/platform/files'
import { useDocumentSync, type ConflictChoice } from '@/composables/useDocumentSync'
import { exportDocx } from '@/services/documentDocx'
import type { DocumentScope, TiptapDocument } from '@/types/documents'
import DocumentConflictResolver from './DocumentConflictResolver.vue'

const props = defineProps<{ scope: DocumentScope; title: string }>()
const editorRef = shallowRef<TiptapProEditorExpose | null>(null)
const showConflict = ref(false)
const pendingConflictResolve = ref<((choice: ConflictChoice) => void) | null>(null)
const editorContent = ref<TiptapDocument>({ type: 'doc', content: [{ type: 'paragraph' }] })
const { content, documentState, status, scheduleSave, link, checkExternal, acknowledgeExternal } = useDocumentSync(
  props.scope,
  () => new Promise<ConflictChoice>((resolve) => { showConflict.value = true; pendingConflictResolve.value = resolve }),
)
let externalTimer: number | undefined
const linked = computed(() => Boolean(documentState.value?.docx_path))

function setWordTheme() { setTheme('word', document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light') }
function update(next: JSONContent) { const json = next as TiptapDocument; editorContent.value = json; scheduleSave(json) }
function resolveConflict(choice: ConflictChoice) { showConflict.value = false; pendingConflictResolve.value?.(choice); pendingConflictResolve.value = null }
async function importExternal() {
  const external = await checkExternal()
  if (!external || !editorRef.value) return
  const editor = editorRef.value.getEditor()
  if (!editor) return
  editor.commands.setContent(external.html)
  const json = editor.getJSON() as TiptapDocument
  editorContent.value = json
  await acknowledgeExternal(json, external.hash)
}
async function linkWord() { const path = await pickDesktopWordFile('Связать с файлом Word', 'Word'); if (path) await link(path) }
async function exportWord() {
  const blob = await exportDocx(editorContent.value); const url = URL.createObjectURL(blob); const anchor = document.createElement('a')
  anchor.href = url; anchor.download = `${props.title}.docx`; anchor.click(); URL.revokeObjectURL(url)
}
function importWord() { const input = document.createElement('input'); input.type = 'file'; input.accept = '.docx'; input.onchange = async () => { const file = input.files?.[0]; if (!file || !editorRef.value) return; const { importDocx } = await import('@/services/documentDocx'); const html = await importDocx(await file.arrayBuffer()); editorRef.value.getEditor()?.commands.setContent(html) }; input.click() }

watch(content, (next) => { editorContent.value = next }, { deep: true })
onMounted(() => { setWordTheme(); const observer = new MutationObserver(setWordTheme); observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] }); externalTimer = window.setInterval(() => void importExternal().catch(() => undefined), 5000); onBeforeUnmount(() => observer.disconnect()) })
onBeforeUnmount(() => window.clearInterval(externalTimer))
</script>

<template>
  <section class="document-editor-view">
    <header class="document-editor-view__header">
      <div><p class="document-editor-view__eyebrow">Текст</p><h1>{{ title }}</h1></div>
      <div class="document-editor-view__actions">
        <span aria-live="polite">{{ status }}</span>
        <button class="nf-button nf-button--secondary" type="button" title="Импортировать документ Word" aria-label="Импортировать документ Word" @click="importWord">Импорт DOCX</button>
        <button class="nf-button nf-button--secondary" type="button" title="Экспортировать документ Word" aria-label="Экспортировать документ Word" @click="exportWord">Экспорт DOCX</button>
        <button class="nf-button nf-button--secondary" type="button" title="Связать документ с локальным файлом Word" aria-label="Связать документ с локальным файлом Word" @click="linkWord">{{ linked ? 'Файл Word связан' : 'Связать с Word' }}</button>
      </div>
    </header>
    <TiptapProEditor
      ref="editorRef"
      v-model="editorContent"
      class="nfprogress-word-editor"
      version="premium"
      locale="en-US"
      document-id="nfprogress-document"
      :features="{ headerNav: true, footerNav: true, table: true, tableToolbar: true, image: true, linkBubbleMenu: true, floatingMenu: true, slashCommand: true, aiChat: false, aiSettings: false }"
      @update="update"
    />
    <DocumentConflictResolver v-if="showConflict" @resolve="resolveConflict" />
  </section>
</template>

<style scoped>
.document-editor-view{width:min(100%,80rem);margin:0 auto;padding:var(--nf-space-6);color:var(--nf-color-text)}.document-editor-view__header{display:flex;align-items:center;justify-content:space-between;gap:1rem;margin-bottom:1rem}.document-editor-view__header h1,.document-editor-view__eyebrow{margin:0}.document-editor-view__eyebrow{color:var(--nf-color-text-muted);font-size:.78rem;font-weight:800;text-transform:uppercase}.document-editor-view__actions{display:flex;flex-wrap:wrap;align-items:center;justify-content:flex-end;gap:.5rem}.document-editor-view__actions span{font-size:.82rem;color:var(--nf-color-text-muted)}.nfprogress-word-editor{min-height:calc(100dvh - 14rem);border:1px solid var(--nf-color-border);border-radius:var(--nf-radius-lg);overflow:hidden;background:var(--nf-color-surface);box-shadow:var(--nf-shadow-card)}.nfprogress-word-editor :deep(.editor-container),.nfprogress-word-editor :deep(.tiptap-editor-container){background:var(--nf-color-surface)}.nfprogress-word-editor :deep(.ProseMirror){color:var(--nf-color-text)}@media(max-width:44rem){.document-editor-view{padding:var(--nf-space-4)}.document-editor-view__header{align-items:flex-start;flex-direction:column}.document-editor-view__actions{justify-content:flex-start}.nfprogress-word-editor{min-height:calc(100dvh - 17rem)}}</style>
