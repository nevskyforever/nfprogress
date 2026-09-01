<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import type { JSONContent } from '@tiptap/core'
import { onBeforeRouteLeave, useRouter } from 'vue-router'
import { createI18n, TiptapProEditor, setTheme, type TiptapProEditorExpose } from 'tiptap-ui-kit'
import 'tiptap-ui-kit/style.css'
import 'ant-design-vue/dist/reset.css'
import { pickDesktopWordFile } from '@/platform/files'
import { currentPlatform } from '@/platform/runtime'
import { useDocumentSync, type ConflictChoice } from '@/composables/useDocumentSync'
import { exportDocx, WORD_FONT_FAMILIES, WORD_FONT_SIZES } from '@/services/documentDocx'
import type { DocumentScope, TiptapDocument } from '@/types/documents'
import { projectsApi } from '@/api/projects'
import { documentsApi } from '@/api/documents'
import type { Project } from '@/types/api'
import { convertProjectUnit } from '@/utils/projectPlanning'
import { announceDataChange, onDataChange } from '@/services/dataChanges'
import { progressChangeNotification } from '@/utils/progressNotifications'
import { gameResponseMessages } from '@/utils/gameNotifications'
import DocumentConflictResolver from './DocumentConflictResolver.vue'
import { tiptapLocale } from './tiptapLocale'
import { useLocaleStore } from '@/stores/locale'
import { useNotificationsStore } from '@/stores/notifications'
import { useThemeStore } from '@/stores/theme'

const props = defineProps<{ scope: DocumentScope; title: string }>()
const router = useRouter()
const locale = useLocaleStore()
const notifications = useNotificationsStore()
const theme = useThemeStore()
const t = locale.translate
const editorRef = shallowRef<TiptapProEditorExpose | null>(null)
const showConflict = ref(false)
const pendingConflictResolve = ref<((choice: ConflictChoice) => void) | null>(null)
const editorContent = ref<TiptapDocument>({ type: 'doc', content: [{ type: 'paragraph' }] })
const projectEntity = ref<Project | null>(null)
const zoom = ref(100)
const selectedFontFamily = ref<(typeof WORD_FONT_FAMILIES)[number]>('Arial')
const selectedFontSize = ref<(typeof WORD_FONT_SIZES)[number]>(12)
const canLinkWord = currentPlatform() === 'tauri'
const saving = ref(false)
const recording = ref(false)
const processing = computed(() => saving.value || recording.value)
const { content, documentState, status, save, scheduleSave, link, checkExternal, acknowledgeExternal } = useDocumentSync(
  props.scope,
  () => new Promise<ConflictChoice>((resolve) => { showConflict.value = true; pendingConflictResolve.value = resolve }),
)
let externalTimer: number | undefined
let stopCloseListener: (() => void) | undefined
let stopProjectDataChanges: (() => void) | undefined
let projectLoadSequence = 0
let closeInProgress = false
const linked = computed(() => Boolean(documentState.value?.docx_path))
const textSymbols = computed(() => countTextSymbols(editorContent.value))
const textUnits = computed(() => projectEntity.value
  ? convertProjectUnit(textSymbols.value, 'symbols', projectEntity.value.unit)
  : null)
const entityFractionDigits = computed(() => projectEntity.value?.unit === 'symbols' ? 0 : 2)
const entityProgressLabel = computed(() => {
  const entity = projectEntity.value
  if (!entity) return ''
  const goalLabel = entity.goal === null
    ? t('Без лимита')
    : locale.formatNumber(entity.goal, entityFractionDigits.value)
  const unitValue = entity.goal ?? entity.total
  return `${locale.formatNumber(entity.total, entityFractionDigits.value)} / ${goalLabel} ${locale.formatUnit(entity.unit, unitValue)}`
})
const todayGoalCompleted = computed(() => {
  const entity = projectEntity.value
  if (!entity || entity.today_goal === null) return false
  // today_goal is the cumulative target calculated by the existing project plan.
  return entity.total >= entity.today_goal
})
const todayGoalLabel = computed(() => {
  const entity = projectEntity.value
  if (!entity || entity.today_goal === null) return ''
  return `${locale.formatNumber(entity.today_goal, entityFractionDigits.value)} ${locale.formatUnit(entity.unit, entity.today_goal)}`
})
const todayGoalProgressPercent = computed(() => {
  const entity = projectEntity.value
  if (!entity || entity.today_goal === null || entity.plan_daily_goal === null || entity.plan_daily_goal <= 0) return 0
  // Show a live preview from the editor while the next progress record is pending.
  const currentValue = textSymbols.value > 0 ? textUnits.value ?? entity.total : entity.total
  const writtenToday = entity.added_today + currentValue - entity.total
  return Math.min(100, Math.max(0, (writtenToday / entity.plan_daily_goal) * 100))
})
const canRecordText = computed(() => Boolean(
  projectEntity.value
  && textSymbols.value > 0
  && textUnits.value !== null
  && Math.abs(textUnits.value - projectEntity.value.total) >= 0.009,
))

function setWordTheme(value: 'light' | 'dark') { setTheme('word', value) }
function configureKitLocale() {
  // The package's public type only lists bundled locales, while its runtime
  // intentionally accepts host locale keys and message dictionaries.
  createI18n({ locale: 'en-US', messages: tiptapLocale(t) as never })
}
function update(next: JSONContent) { const json = next as TiptapDocument; editorContent.value = json; scheduleSave(json) }
function countTextSymbols(value: unknown): number {
  if (!value || typeof value !== 'object') return 0
  const node = value as { text?: unknown; content?: unknown }
  return (typeof node.text === 'string' ? Array.from(node.text).length : 0)
    + (Array.isArray(node.content) ? node.content.reduce((total, child) => total + countTextSymbols(child), 0) : 0)
}
function setZoom(next: number) { zoom.value = Math.min(500, Math.max(70, next)) }
function setFontFamily(): void {
  editorRef.value?.getEditor()?.chain().focus().setMark('textStyle', { fontFamily: selectedFontFamily.value }).run()
}
function setFontSize(): void {
  editorRef.value?.getEditor()?.chain().focus().setMark('textStyle', { fontSize: `${selectedFontSize.value}pt` }).run()
}
async function loadProjectEntity() {
  const sequence = ++projectLoadSequence
  try {
    const project = await projectsApi.get(props.scope.projectId)
    if (sequence !== projectLoadSequence) return
    projectEntity.value = props.scope.stageId
      ? project.stages.find((stage) => stage.id === props.scope.stageId) ?? null
      : project
  } catch (error) {
    if (sequence === projectLoadSequence) projectEntity.value = null
    throw error
  }
}
function resolveConflict(choice: ConflictChoice) { showConflict.value = false; pendingConflictResolve.value?.(choice); pendingConflictResolve.value = null }
async function recordTextProgress(force = false): Promise<boolean> {
  if (recording.value || textSymbols.value <= 0 || (!force && !canRecordText.value)) return false
  recording.value = true
  try {
    const result = await documentsApi.recordProgress(props.scope)
    if (!result.progress) {
      status.value = t('Документ не изменился. Текущий объём уже актуален.')
      return false
    }
    announceDataChange('projects')
    const progress = result.progress
    const entity = props.scope.stageId
      ? progress.project.stages.find((stage) => stage.id === props.scope.stageId) ?? projectEntity.value
      : progress.project
    projectEntity.value = entity ?? null
    if (entity) {
      const feedback = progressChangeNotification(progress, entity, t, locale.formatNumber, locale.formatUnit)
      if (feedback) notifications.show(feedback.message, feedback.kind)
    }
    if (progress.game) {
      notifications.setGameHistory(progress.game.state.notifications)
      for (const message of gameResponseMessages(progress.game)) notifications.success(t(message))
      announceDataChange('game')
    }
    if (progress.warning) notifications.warning(progress.warning)
    status.value = t('Запись прогресса добавлена.')
    return true
  } catch (error) {
    status.value = t(error instanceof Error ? error.message : 'Не удалось сохранить')
    return false
  } finally {
    recording.value = false
  }
}
let flushPromise: Promise<void> | null = null
async function flushAndRecord(): Promise<void> {
  if (flushPromise) return flushPromise
  const operation = (async () => {
    const latest = editorRef.value?.getJSON()
    if (latest) {
      editorContent.value = latest as TiptapDocument
      content.value = editorContent.value
    }
    saving.value = true
    try {
      // The progress endpoint reads the persisted document, so its request
      // must follow this immediate save rather than the debounce timer.
      await save(false)
    } catch (error) {
      status.value = t(error instanceof Error ? error.message : 'Не удалось сохранить')
      return
    } finally {
      saving.value = false
    }
    const recorded = await recordTextProgress(true)
    // The document itself may have changed even when rounding/duplicate
    // protection correctly produced no progress entry. Keep project counters
    // and cached detail views in sync with that saved content as well.
    if (!recorded) announceDataChange('projects')
  })()
  flushPromise = operation
  try {
    await operation
  } finally {
    if (flushPromise === operation) flushPromise = null
  }
}
function onRecordClick(): void { void flushAndRecord() }
function closeEditor() {
  if (props.scope.stageId) {
    void router.push({ name: 'stage-detail', params: { projectId: props.scope.projectId, stageId: props.scope.stageId } })
    return
  }
  void router.push({ name: 'project-detail', params: { projectId: props.scope.projectId } })
}
function handleEscape(event: KeyboardEvent): void {
  if (event.key !== 'Escape' || showConflict.value || processing.value) return
  event.preventDefault()
  closeEditor()
}
function handleEditorKeydown(event: KeyboardEvent): void {
  if (event.key !== 'Tab' || event.altKey || event.ctrlKey || event.metaKey) return
  const target = event.target
  if (!(target instanceof Element) || !target.closest('.ProseMirror[contenteditable="true"]')) return

  event.preventDefault()
  event.stopPropagation()
  editorRef.value?.getEditor()?.commands.insertContent({ type: 'text', text: '\t' })
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
onMounted(() => {
  window.addEventListener('keydown', handleEscape, true)
  externalTimer = window.setInterval(() => void importExternal().catch(() => undefined), 5000)
  void loadProjectEntity().catch(() => undefined)
  stopProjectDataChanges = onDataChange((scope) => {
    if (scope === 'projects') void loadProjectEntity().catch(() => undefined)
  })
  if (window.__TAURI_INTERNALS__) {
    void import('@tauri-apps/api/window').then(async ({ getCurrentWindow }) => {
      stopCloseListener = await getCurrentWindow().onCloseRequested(async (event) => {
        event.preventDefault()
        if (closeInProgress) return
        closeInProgress = true
        try { await flushAndRecord() } finally { await getCurrentWindow().destroy() }
      })
    })
  }
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleEscape, true)
  window.clearInterval(externalTimer)
  projectLoadSequence += 1
  stopProjectDataChanges?.()
  stopCloseListener?.()
})
onBeforeRouteLeave(async () => { await flushAndRecord() })
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
        <button class="nf-button" type="button" :disabled="processing || !canRecordText" @click="onRecordClick">
          {{ processing ? t('Сохраняем…') : t('Добавить запись') }}
        </button>
        <button class="nf-button nf-button--secondary" type="button" title="Импортировать документ Word" aria-label="Импортировать документ Word" @click="importWord">Импорт DOCX</button>
        <button class="nf-button nf-button--secondary" type="button" title="Экспортировать документ Word" aria-label="Экспортировать документ Word" @click="exportWord">Экспорт DOCX</button>
        <button v-if="canLinkWord" class="nf-button nf-button--secondary" type="button" title="Связать документ с локальным файлом Word" aria-label="Связать документ с локальным файлом Word" @click="linkWord">{{ linked ? 'Файл Word связан' : 'Связать с Word' }}</button>
      </div>
    </header>
    <div class="document-editor-view__workspace" @keydown.capture="handleEditorKeydown">
      <TiptapProEditor
        ref="editorRef"
        v-model="editorContent"
        class="nfprogress-word-editor"
        :style="{ '--nf-editor-zoom': `${zoom / 100}` }"
        version="advanced"
        locale="en-US"
        document-id="nfprogress-document"
        :features="{ headerNav: true, footerNav: false, table: false, tableToolbar: false, image: false, linkBubbleMenu: false, floatingMenu: false, slashCommand: false, dragHandleMenu: false, aiChat: false, aiSettings: false }"
        @update="update"
      />
      <div class="document-editor-view__font-controls">
        <label class="document-editor-view__font-control">
          <span class="sr-only">{{ t('Шрифт') }}</span>
          <select v-model="selectedFontFamily" :aria-label="t('Шрифт')" @change="setFontFamily">
            <option v-for="font in WORD_FONT_FAMILIES" :key="font" :value="font">{{ font }}</option>
          </select>
        </label>
        <label class="document-editor-view__font-control">
          <span class="sr-only">{{ t('Размер текста') }}</span>
          <select v-model="selectedFontSize" :aria-label="t('Размер текста')" @change="setFontSize">
            <option v-for="size in WORD_FONT_SIZES" :key="size" :value="size">{{ size }} pt</option>
          </select>
        </label>
      </div>
      <footer class="document-editor-view__statusbar" aria-label="Статус документа">
        <div v-if="projectEntity" class="document-editor-view__status-info">
          <span class="document-editor-view__unit-count">{{ t('Прогресс') }}: <strong>{{ entityProgressLabel }}</strong></span>
          <span
            v-if="projectEntity.today_goal !== null"
            class="document-editor-view__today-goal"
            :class="{ 'document-editor-view__today-goal--complete': todayGoalCompleted }"
            role="status"
          >
            <template v-if="todayGoalCompleted">{{ t('Цель на день выполнена!') }}</template>
            <template v-else>{{ t('Цель на сегодня') }}: <strong>{{ todayGoalLabel }}</strong></template>
            <span
              class="document-editor-view__today-goal-progress"
              role="progressbar"
              :aria-label="t('Цель на сегодня')"
              aria-valuemin="0"
              aria-valuemax="100"
              :aria-valuenow="Math.round(todayGoalProgressPercent)"
            >
              <span class="document-editor-view__today-goal-progress-fill" :style="{ width: `${todayGoalProgressPercent}%` }" />
            </span>
          </span>
        </div>
        <span v-else class="document-editor-view__unit-count">{{ t('Единицы проекта загружаются…') }}</span>
        <div class="document-editor-view__zoom" role="group" :aria-label="t('Масштаб документа')">
          <button type="button" :title="t('Уменьшить масштаб')" :aria-label="t('Уменьшить масштаб')" :disabled="zoom <= 70" @click="setZoom(zoom - 10)">−</button>
          <button type="button" :title="t('Сбросить масштаб')" :aria-label="t('Сбросить масштаб')" @click="setZoom(100)">{{ zoom }}%</button>
          <button type="button" :title="t('Увеличить масштаб')" :aria-label="t('Увеличить масштаб')" :disabled="zoom >= 500" @click="setZoom(zoom + 10)">+</button>
        </div>
      </footer>
    </div>
    <DocumentConflictResolver v-if="showConflict" @resolve="resolveConflict" />
  </section>
</template>

<style scoped>
.document-editor-view{width:min(100%,88rem);margin:0 auto;padding:var(--nf-space-5);color:var(--nf-color-text)}.document-editor-view__header{display:flex;align-items:center;justify-content:space-between;gap:1rem;margin-bottom:.75rem}.document-editor-view__title{display:grid;gap:.35rem}.document-editor-view__back{display:inline-flex;align-items:center;width:max-content;min-height:2rem;padding:0 .45rem;color:var(--nf-color-text-muted);font:inherit;font-size:.85rem;font-weight:700;cursor:pointer;background:transparent;border:0;border-radius:var(--nf-radius-sm)}.document-editor-view__back:hover,.document-editor-view__back:focus-visible{color:var(--nf-color-text);background:color-mix(in srgb,var(--nf-color-primary) 10%,transparent);outline:none}.document-editor-view__header h1,.document-editor-view__eyebrow{margin:0}.document-editor-view__eyebrow{color:var(--nf-color-text-muted);font-size:.78rem;font-weight:800;text-transform:uppercase}.document-editor-view__actions{display:flex;flex-wrap:wrap;align-items:center;justify-content:flex-end;gap:.5rem}.document-editor-view__actions span{font-size:.82rem;color:var(--nf-color-text-muted)}.document-editor-view__font-control select{height:2rem;padding:0 .45rem;color:var(--nf-color-text);font:inherit;font-size:.85rem;background:var(--nf-color-canvas);border:1px solid var(--nf-color-border);border-radius:var(--nf-radius-sm)}.nfprogress-word-editor{--tiptap-bg:var(--nf-color-surface);--tiptap-bg-secondary:var(--nf-color-canvas);--tiptap-bg-hover:color-mix(in srgb,var(--nf-color-primary) 10%,var(--nf-color-surface));--tiptap-toolbar-bg:var(--nf-color-surface);--tiptap-text:var(--nf-color-text);--tiptap-text-secondary:var(--nf-color-text-muted);--tiptap-border:var(--nf-color-border);--tiptap-border-hover:var(--nf-color-primary);--tiptap-border-focus:var(--nf-color-primary);--tiptap-primary:var(--nf-color-primary);--tiptap-primary-hover:var(--nf-color-primary);--tiptap-link:var(--nf-color-primary);min-height:calc(100dvh - 11rem);border:1px solid var(--nf-color-border);border-radius:var(--nf-radius-lg);overflow:hidden;background:var(--nf-color-canvas);box-shadow:var(--nf-shadow-card)}.nfprogress-word-editor :deep(.word-toolbar){display:flex;flex-wrap:nowrap;align-items:center;min-height:46px;max-height:50px;padding:4px 8px!important;overflow-x:auto;overflow-y:hidden;background:var(--nf-color-surface)!important;border-bottom-color:var(--nf-color-border)!important;scrollbar-width:thin}.nfprogress-word-editor :deep(.editor-toolbar),.nfprogress-word-editor :deep(.toolbar-left){display:flex;flex:0 0 auto;flex-wrap:nowrap;align-items:center}.nfprogress-word-editor :deep(.toolbar-left>.tool-group:nth-child(4)),.nfprogress-word-editor :deep(.toolbar-left>.tool-group:nth-child(6)),.nfprogress-word-editor :deep(.toolbar-left>.tool-group:nth-child(9)),.nfprogress-word-editor :deep(.toolbar-left>.tool-group:nth-child(11)),.nfprogress-word-editor :deep(.toolbar-left>.tool-group:nth-child(12)),.nfprogress-word-editor :deep(.toolbar-left>.tool-group:nth-child(13)),.nfprogress-word-editor :deep(.toolbar-left>.tool-group:nth-child(5) .tt-toolbar-button:last-child),.nfprogress-word-editor :deep(.toolbar-left>.tool-group:nth-child(7) .tt-toolbar-button:last-child){display:none!important}.nfprogress-word-editor :deep(.tt-toolbar-button),.nfprogress-word-editor :deep(.tt-dropdown-btn){min-width:32px!important;height:32px!important;color:var(--nf-color-text)!important;border-radius:var(--nf-radius-sm)!important}.nfprogress-word-editor :deep(.tt-toolbar-button:hover),.nfprogress-word-editor :deep(.tt-dropdown-btn:hover){background:var(--tiptap-bg-hover)!important}.nfprogress-word-editor :deep(.word-document-container){min-height:calc(100dvh - 16rem);padding:1.5rem;background:var(--nf-color-canvas)!important;overflow:auto}.nfprogress-word-editor :deep(.document-pages){display:block!important;width:100%!important;margin:0 auto!important;transform:none!important;transform-origin:top center}.nfprogress-word-editor :deep(.continuous-pages){box-sizing:border-box;width:min(850px,100%)!important;max-width:850px!important;min-height:1120px;margin:0 auto!important;padding:5rem 5.5rem!important;zoom:var(--nf-editor-zoom,1);background:color-mix(in srgb,var(--nf-color-surface) 82%,white)!important;color:var(--nf-color-text)!important;box-shadow:0 3px 18px rgb(0 0 0 / 18%)!important}.nfprogress-word-editor :deep(.word-content-multi .ProseMirror){box-sizing:border-box;width:100%;min-height:1000px;padding:0!important;color:var(--nf-color-text)!important;background:transparent!important;font-family:Arial,sans-serif!important;font-size:12pt!important}.nfprogress-word-editor :deep(.template-list),.nfprogress-word-editor :deep(.gallery-grid){display:none!important}.nfprogress-word-editor :deep(.ant-upload-wrapper){max-width:26rem}.nfprogress-word-editor :deep(.ant-dropdown-menu),.nfprogress-word-editor :deep(.ant-select-dropdown){font-family:var(--nf-font-sans)}.document-editor-view__statusbar{display:flex;align-items:center;justify-content:space-between;gap:1rem;min-height:2.8rem;padding:.35rem .65rem;color:var(--nf-color-text-muted);font-size:.82rem;background:var(--nf-color-surface);border:1px solid var(--nf-color-border);border-top:0;border-radius:0 0 var(--nf-radius-lg) var(--nf-radius-lg)}.document-editor-view__unit-count strong{color:var(--nf-color-text)}.document-editor-view__zoom{display:inline-flex;align-items:center;overflow:hidden;border:1px solid var(--nf-color-border);border-radius:var(--nf-radius-sm)}.document-editor-view__zoom button{min-width:2rem;min-height:1.8rem;padding:0 .45rem;color:var(--nf-color-text);font:inherit;font-size:.8rem;font-weight:700;cursor:pointer;background:transparent;border:0}.document-editor-view__zoom button+button{border-left:1px solid var(--nf-color-border)}.document-editor-view__zoom button:hover:not(:disabled),.document-editor-view__zoom button:focus-visible{background:color-mix(in srgb,var(--nf-color-primary) 12%,transparent);outline:none}.document-editor-view__zoom button:disabled{color:var(--nf-color-text-muted);cursor:not-allowed;opacity:.55}@media(max-width:44rem){.document-editor-view{padding:var(--nf-space-3)}.document-editor-view__header{align-items:flex-start;flex-direction:column}.document-editor-view__actions{justify-content:flex-start}.nfprogress-word-editor{min-height:calc(100dvh - 15rem)}.nfprogress-word-editor :deep(.word-document-container){padding:.5rem}.nfprogress-word-editor :deep(.continuous-pages){min-height:calc(100dvh - 16rem);padding:2rem 1.25rem!important;box-shadow:none!important}.nfprogress-word-editor :deep(.word-content-multi .ProseMirror){min-height:calc(100dvh - 20rem)}.document-editor-view__statusbar{align-items:flex-start;flex-direction:column}.document-editor-view__zoom{align-self:flex-end}}
.document-editor-view__workspace{position:relative;display:flex;height:calc(100dvh - 12rem);min-height:30rem;flex-direction:column}.document-editor-view__font-controls{position:absolute;z-index:101;top:.45rem;right:.6rem;display:flex;align-items:center;gap:.4rem;padding:0 .2rem;background:var(--nf-color-surface)}.document-editor-view__font-controls .document-editor-view__font-control select{height:32px}.nfprogress-word-editor{flex:1;min-height:0!important;height:auto!important;border-radius:var(--nf-radius-lg) var(--nf-radius-lg) 0 0}.document-editor-view__statusbar{position:relative;z-index:11;flex-shrink:0}@media(max-width:44rem){.document-editor-view__workspace{height:calc(100dvh - 16rem);min-height:24rem}.document-editor-view__font-controls{right:.35rem}}
.document-editor-view__status-info{display:flex;align-items:center;flex-wrap:wrap;gap:1rem;min-width:0}.document-editor-view__today-goal{display:inline-flex;align-items:center;gap:.45rem}.document-editor-view__today-goal--complete{color:var(--nf-color-success);font-weight:700}.document-editor-view__today-goal strong{color:var(--nf-color-text)}.document-editor-view__today-goal-progress{display:block;width:4.5rem;height:.36rem;overflow:hidden;background:color-mix(in srgb,var(--nf-color-primary) 18%,var(--nf-color-canvas));border-radius:var(--nf-radius-pill)}.document-editor-view__today-goal-progress-fill{display:block;height:100%;background:var(--nf-color-primary);border-radius:inherit;transition:width .4s ease-out}.document-editor-view__today-goal--complete .document-editor-view__today-goal-progress-fill{background:var(--nf-color-success)}
</style>
