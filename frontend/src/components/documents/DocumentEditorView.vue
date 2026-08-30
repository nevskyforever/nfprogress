<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import type { JSONContent } from '@tiptap/core'
import { useRouter } from 'vue-router'
import { createI18n, TiptapProEditor, setTheme, type TiptapProEditorExpose } from 'tiptap-ui-kit'
import 'tiptap-ui-kit/style.css'
import 'ant-design-vue/dist/reset.css'
import { pickDesktopWordFile } from '@/platform/files'
import { useDocumentSync, type ConflictChoice } from '@/composables/useDocumentSync'
import { exportDocx } from '@/services/documentDocx'
import type { DocumentScope, TiptapDocument } from '@/types/documents'
import DocumentConflictResolver from './DocumentConflictResolver.vue'
import { tiptapLocale } from './tiptapLocale'
import { useLocaleStore } from '@/stores/locale'
import { useThemeStore } from '@/stores/theme'

const props = defineProps<{ scope: DocumentScope; title: string }>()
const router = useRouter()
const locale = useLocaleStore()
const theme = useThemeStore()
const t = locale.translate
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

function setWordTheme(value: 'light' | 'dark') { setTheme('word', value) }
function configureKitLocale() {
  // The package's public type only lists bundled locales, while its runtime
  // intentionally accepts host locale keys and message dictionaries.
  createI18n({ locale: 'en-US', messages: tiptapLocale(t) as never })
}
function update(next: JSONContent) { const json = next as TiptapDocument; editorContent.value = json; scheduleSave(json) }
function resolveConflict(choice: ConflictChoice) { showConflict.value = false; pendingConflictResolve.value?.(choice); pendingConflictResolve.value = null }
function closeEditor() {
  if (props.scope.stageId) {
    void router.push({ name: 'stage-detail', params: { projectId: props.scope.projectId, stageId: props.scope.stageId } })
    return
  }
  void router.push({ name: 'project-detail', params: { projectId: props.scope.projectId } })
}
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
async function linkWord() {
  try {
    const path = await pickDesktopWordFile('Связать с файлом Word', 'Word')
    if (!path) return
    await link(path)
    status.value = t('Файл Word связан')
  } catch (error) {
    status.value = t(error instanceof Error ? error.message : 'Произошла непредвиденная ошибка.')
  }
}
async function exportWord() {
  const blob = await exportDocx(editorContent.value); const url = URL.createObjectURL(blob); const anchor = document.createElement('a')
  anchor.href = url; anchor.download = `${props.title}.docx`; anchor.click(); URL.revokeObjectURL(url)
}
function importWord() { const input = document.createElement('input'); input.type = 'file'; input.accept = '.docx'; input.onchange = async () => { const file = input.files?.[0]; if (!file || !editorRef.value) return; const { importDocx } = await import('@/services/documentDocx'); const html = await importDocx(await file.arrayBuffer()); editorRef.value.getEditor()?.commands.setContent(html) }; input.click() }

watch(content, (next) => { editorContent.value = next }, { deep: true })
watch(() => locale.language, configureKitLocale)
watch(() => theme.resolved, setWordTheme, { immediate: true })
configureKitLocale()
onMounted(() => { externalTimer = window.setInterval(() => void importExternal().catch(() => undefined), 5000) })
onBeforeUnmount(() => window.clearInterval(externalTimer))
</script>

<template>
  <section class="document-editor-view">
    <header class="document-editor-view__header">
      <div class="document-editor-view__title">
        <button class="document-editor-view__back" type="button" :title="scope.stageId ? 'Вернуться к этапу' : 'Вернуться к проекту'" :aria-label="scope.stageId ? 'Вернуться к этапу' : 'Вернуться к проекту'" @click="closeEditor">← {{ scope.stageId ? 'К этапу' : 'К проекту' }}</button>
        <div><p class="document-editor-view__eyebrow">Текст</p><h1>{{ title }}</h1></div>
      </div>
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
      version="advanced"
      locale="en-US"
      document-id="nfprogress-document"
      :features="{ headerNav: true, footerNav: false, table: true, tableToolbar: true, image: true, linkBubbleMenu: true, floatingMenu: false, slashCommand: false, dragHandleMenu: false, aiChat: false, aiSettings: false }"
      @update="update"
    />
    <DocumentConflictResolver v-if="showConflict" @resolve="resolveConflict" />
  </section>
</template>

<style scoped>
.document-editor-view{width:min(100%,88rem);margin:0 auto;padding:var(--nf-space-5);color:var(--nf-color-text)}.document-editor-view__header{display:flex;align-items:center;justify-content:space-between;gap:1rem;margin-bottom:.75rem}.document-editor-view__title{display:grid;gap:.35rem}.document-editor-view__back{display:inline-flex;align-items:center;width:max-content;min-height:2rem;padding:0 .45rem;color:var(--nf-color-text-muted);font:inherit;font-size:.85rem;font-weight:700;cursor:pointer;background:transparent;border:0;border-radius:var(--nf-radius-sm)}.document-editor-view__back:hover,.document-editor-view__back:focus-visible{color:var(--nf-color-text);background:color-mix(in srgb,var(--nf-color-primary) 10%,transparent);outline:none}.document-editor-view__header h1,.document-editor-view__eyebrow{margin:0}.document-editor-view__eyebrow{color:var(--nf-color-text-muted);font-size:.78rem;font-weight:800;text-transform:uppercase}.document-editor-view__actions{display:flex;flex-wrap:wrap;align-items:center;justify-content:flex-end;gap:.5rem}.document-editor-view__actions span{font-size:.82rem;color:var(--nf-color-text-muted)}.nfprogress-word-editor{--tiptap-bg:var(--nf-color-surface);--tiptap-bg-secondary:var(--nf-color-canvas);--tiptap-bg-hover:color-mix(in srgb,var(--nf-color-primary) 10%,var(--nf-color-surface));--tiptap-toolbar-bg:var(--nf-color-surface);--tiptap-text:var(--nf-color-text);--tiptap-text-secondary:var(--nf-color-text-muted);--tiptap-border:var(--nf-color-border);--tiptap-border-hover:var(--nf-color-primary);--tiptap-border-focus:var(--nf-color-primary);--tiptap-primary:var(--nf-color-primary);--tiptap-primary-hover:var(--nf-color-primary);--tiptap-link:var(--nf-color-primary);min-height:calc(100dvh - 11rem);border:1px solid var(--nf-color-border);border-radius:var(--nf-radius-lg);overflow:hidden;background:var(--nf-color-canvas);box-shadow:var(--nf-shadow-card)}.nfprogress-word-editor :deep(.word-toolbar){display:flex;flex-wrap:nowrap;align-items:center;min-height:46px;max-height:50px;padding:4px 8px!important;overflow-x:auto;overflow-y:hidden;background:var(--nf-color-surface)!important;border-bottom-color:var(--nf-color-border)!important;scrollbar-width:thin}.nfprogress-word-editor :deep(.editor-toolbar),.nfprogress-word-editor :deep(.toolbar-left){display:flex;flex:0 0 auto;flex-wrap:nowrap;align-items:center}.nfprogress-word-editor :deep(.toolbar-left>.tool-group:nth-child(11)),.nfprogress-word-editor :deep(.toolbar-left>.tool-group:nth-child(12)),.nfprogress-word-editor :deep(.toolbar-left>.tool-group:nth-child(13)){display:none!important}.nfprogress-word-editor :deep(.tt-toolbar-button),.nfprogress-word-editor :deep(.tt-dropdown-btn){min-width:32px!important;height:32px!important;color:var(--nf-color-text)!important;border-radius:var(--nf-radius-sm)!important}.nfprogress-word-editor :deep(.tt-toolbar-button:hover),.nfprogress-word-editor :deep(.tt-dropdown-btn:hover){background:var(--tiptap-bg-hover)!important}.nfprogress-word-editor :deep(.font-family-select),.nfprogress-word-editor :deep(.font-size-select){display:block;min-width:0}.nfprogress-word-editor :deep(.ant-select){min-width:7rem}.nfprogress-word-editor :deep(.ant-select-selector){height:32px!important;border-color:var(--nf-color-border)!important;background:var(--nf-color-canvas)!important;color:var(--nf-color-text)!important}.nfprogress-word-editor :deep(.ant-select-selection-item){line-height:30px!important}.nfprogress-word-editor :deep(.word-document-container){min-height:calc(100dvh - 16rem);padding:1.5rem;background:var(--nf-color-canvas)!important;overflow:auto}.nfprogress-word-editor :deep(.document-pages){display:block!important;width:100%!important;margin:0 auto!important;transform:none!important;transform-origin:top center}.nfprogress-word-editor :deep(.continuous-pages){box-sizing:border-box;width:min(850px,100%)!important;max-width:850px!important;min-height:1120px;margin:0 auto!important;padding:5rem 5.5rem!important;background:color-mix(in srgb,var(--nf-color-surface) 82%,white)!important;color:var(--nf-color-text)!important;box-shadow:0 3px 18px rgb(0 0 0 / 18%)!important}.nfprogress-word-editor :deep(.word-content-multi .ProseMirror){box-sizing:border-box;width:100%;min-height:1000px;padding:0!important;color:var(--nf-color-text)!important;background:transparent!important}.nfprogress-word-editor :deep(.template-list),.nfprogress-word-editor :deep(.gallery-grid){display:none!important}.nfprogress-word-editor :deep(.ant-upload-wrapper){max-width:26rem}.nfprogress-word-editor :deep(.ant-dropdown-menu),.nfprogress-word-editor :deep(.ant-select-dropdown){font-family:var(--nf-font-sans)}@media(max-width:44rem){.document-editor-view{padding:var(--nf-space-3)}.document-editor-view__header{align-items:flex-start;flex-direction:column}.document-editor-view__actions{justify-content:flex-start}.nfprogress-word-editor{min-height:calc(100dvh - 15rem)}.nfprogress-word-editor :deep(.word-document-container){padding:.5rem}.nfprogress-word-editor :deep(.continuous-pages){min-height:calc(100dvh - 16rem);padding:2rem 1.25rem!important;box-shadow:none!important}.nfprogress-word-editor :deep(.word-content-multi .ProseMirror){min-height:calc(100dvh - 20rem)}}
</style>
