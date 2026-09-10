<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import type { Editor, JSONContent } from '@tiptap/core'
import { onBeforeRouteLeave, useRouter } from 'vue-router'
import { createI18n, TiptapProEditor, setTheme, type TiptapProEditorExpose } from 'tiptap-ui-kit'
import 'tiptap-ui-kit/style.css'
import 'ant-design-vue/dist/reset.css'
import { pickDesktopWordFile, pickDesktopWordSavePath } from '@/platform/files'
import { currentPlatform } from '@/platform/runtime'
import { useDocumentSync, type ConflictChoice } from '@/composables/useDocumentSync'
import { exportDocx, WORD_FONT_FAMILIES, WORD_FONT_SIZES } from '@/services/documentDocx'
import type { DocumentScope, TiptapDocument } from '@/types/documents'
import { projectsApi } from '@/api/projects'
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
const editorShell = ref<HTMLElement | null>(null)
const toolbarTarget = ref<HTMLElement | null>(null)
const showConflict = ref(false)
const pendingConflictResolve = ref<((choice: ConflictChoice) => void) | null>(null)
const editorContent = ref<TiptapDocument>({ type: 'doc', content: [{ type: 'paragraph' }] })
const projectEntity = ref<Project | null>(null)
const zoom = ref(100)
const typewriterMode = ref(false)
const selectedFontFamily = ref<(typeof WORD_FONT_FAMILIES)[number]>('Arial')
const selectedFontSize = ref<(typeof WORD_FONT_SIZES)[number]>(12)
const selectedLineHeight = ref('1.5')
const editorInstanceKey = ref(0)
const LINE_HEIGHTS = ['1', '1.15', '1.5', '2'] as const
const canLinkWord = currentPlatform() === 'tauri'
const saving = ref(false)
const recording = ref(false)
const processing = computed(() => saving.value || recording.value)
const { content, documentState, status, save, saveAndRecord, setContent, scheduleSave, link, checkExternal, acknowledgeExternal } = useDocumentSync(
  props.scope,
  () => new Promise<ConflictChoice>((resolve) => { showConflict.value = true; pendingConflictResolve.value = resolve }),
)
let externalTimer: number | undefined
let stopCloseListener: (() => void) | undefined
let stopProjectDataChanges: (() => void) | undefined
let projectLoadSequence = 0
let closeInProgress = false
let toolbarObserver: MutationObserver | undefined
let positionSaveTimer: number | undefined
let positionRestoreTimer: number | undefined
let hasRestoredEditorPosition = false
let typewriterResizeObserver: ResizeObserver | undefined
let observedTypewriterContainer: HTMLElement | null = null
let typewriterEditor: Editor | null = null
let typewriterActivationFrame: number | undefined
let typewriterActivationGeneration = 0
let typewriterTailFrame: number | undefined
let typewriterTailGeneration = 0
let typewriterZoomFrame: number | undefined
let typewriterZoomGeneration = 0
let pendingTypewriterZoomAnchor: TypewriterZoomAnchor | null = null
let typewriterManualBrowsing = false
let typewriterProgrammaticScrollTop: number | undefined
type EditorPosition = { selection: number; scrollTop: number }
type TypewriterZoomAnchor = {
  caretOffset: number
  layoutScrollTop: number
  keepWorkingLine: boolean
  readingOffset?: number
  readingPosition?: number
}
const TYPEWRITER_RATIO = 0.5
const TYPEWRITER_EPSILON = 2
const linked = computed(() => Boolean(documentState.value?.docx_path))
const editorDocumentId = computed(() => `nfprogress-document:${props.scope.projectId}:${props.scope.stageId ?? 'project'}`)
const textSymbols = computed(() => countTextSymbols(editorContent.value))
const textUnits = computed(() => projectEntity.value
  ? convertProjectUnit(textSymbols.value, 'symbols', projectEntity.value.unit)
  : null)
const entityFractionDigits = computed(() => projectEntity.value?.unit === 'symbols' ? 0 : 2)
const typewriterTitle = computed(() => t(
  typewriterMode.value ? 'Выключить режим печатной машинки' : 'Включить режим печатной машинки',
))
const entityProgressLabel = computed(() => {
  const entity = projectEntity.value
  if (!entity) return ''
  const goalLabel = entity.goal === null
    ? t('Без лимита')
    : locale.formatNumber(entity.goal, entityFractionDigits.value)
  const unitValue = entity.goal ?? entity.total
  const documentValue = textUnits.value ?? 0
  return `${locale.formatNumber(documentValue, entityFractionDigits.value)} / ${goalLabel} ${locale.formatUnit(entity.unit, unitValue)}`
})
const todayGoalCurrentValue = computed(() => {
  const entity = projectEntity.value
  if (!entity) return 0
  const unsavedChange = textSymbols.value > 0
    ? (textUnits.value ?? entity.total) - entity.total
    : 0
  return Math.max(0, entity.added_today + unsavedChange)
})
const todayGoalCompleted = computed(() => {
  const entity = projectEntity.value
  if (!entity || entity.plan_daily_goal === null) return false
  return todayGoalCurrentValue.value >= entity.plan_daily_goal
})
const todayGoalLabel = computed(() => {
  const entity = projectEntity.value
  if (!entity || entity.today_goal === null) return ''
  return `${locale.formatNumber(entity.today_goal, entityFractionDigits.value)} ${locale.formatUnit(entity.unit, entity.today_goal)}`
})
const todayGoalProgressPercent = computed(() => {
  const target = projectEntity.value?.plan_daily_goal
  if (target === null || target === undefined || target <= 0) return 0
  return Math.min(100, Math.max(0, (todayGoalCurrentValue.value / target) * 100))
})
const canRecordText = computed(() => Boolean(
  projectEntity.value
  && textSymbols.value > 0
  && textUnits.value !== null
  && Math.abs(textUnits.value - projectEntity.value.total) >= 0.009,
))

function setWordTheme(value: 'light' | 'dark') { setTheme('word', value) }
function positionStorageKey(): string {
  return `nfprogress:document-position:${props.scope.projectId}:${props.scope.stageId ?? 'project'}`
}
function savedEditorPosition(): EditorPosition | null {
  try {
    const stored = JSON.parse(localStorage.getItem(positionStorageKey()) ?? '') as Partial<EditorPosition>
    if (
      typeof stored.selection !== 'number'
      || typeof stored.scrollTop !== 'number'
      || !Number.isFinite(stored.selection)
      || !Number.isFinite(stored.scrollTop)
    ) return null
    return { selection: Math.max(1, Math.floor(stored.selection)), scrollTop: Math.max(0, stored.scrollTop) }
  } catch {
    return null
  }
}
function editorScrollContainer(): HTMLElement | null {
  return editorShell.value?.querySelector<HTMLElement>('.word-document-container') ?? null
}
function continuousSheet(): HTMLElement | null {
  return editorShell.value?.querySelector<HTMLElement>('.continuous-pages') ?? null
}
function documentPages(): HTMLElement | null {
  const pages = continuousSheet()?.parentElement
  return pages instanceof HTMLElement ? pages : null
}
function clearTypewriterPageExtent(): void {
  const pages = documentPages()
  pages?.style.removeProperty('height')
  pages?.style.removeProperty('overflow')
}
function removeTypewriterTail(): void {
  editorShell.value?.querySelectorAll<HTMLElement>('[data-nf-typewriter-tail]').forEach((tail) => tail.remove())
  clearTypewriterPageExtent()
}
function ensureTypewriterTail(): HTMLElement | null {
  const sheet = continuousSheet()
  if (!sheet) return null
  const existing = sheet.querySelector<HTMLElement>('[data-nf-typewriter-tail]')
  if (existing) return existing

  const tail = document.createElement('div')
  tail.dataset.nfTypewriterTail = ''
  tail.setAttribute('aria-hidden', 'true')
  tail.setAttribute('contenteditable', 'false')
  tail.tabIndex = -1
  const content = sheet.querySelector<HTMLElement>('.word-content-multi')
  if (content) content.after(tail)
  else sheet.append(tail)
  return tail
}
function sheetZoomScale(sheet: HTMLElement): number {
  const computedZoom = Number.parseFloat(window.getComputedStyle(sheet).zoom)
  if (Number.isFinite(computedZoom) && computedZoom > 0) return computedZoom
  const sheetRect = sheet.getBoundingClientRect()
  return sheet.offsetWidth > 0 && sheetRect.width > 0 ? sheetRect.width / sheet.offsetWidth : 1
}
function visualDeltaToScrollDelta(visualDelta: number, sheet: HTMLElement): number {
  // DOM rects and ProseMirror coordinates are rendered pixels. With CSS zoom,
  // WebKit's scrollTop advances in the sheet's unzoomed coordinate space.
  return visualDelta * sheetZoomScale(sheet)
}
function typewriterTailVisualScale(tail: HTMLElement, fallback: number): number {
  const layoutHeight = Number.parseFloat(tail.style.height)
  const visualHeight = tail.getBoundingClientRect().height
  if (layoutHeight > 0 && visualHeight > 0) {
    const measuredScale = visualHeight / layoutHeight
    if (Number.isFinite(measuredScale) && measuredScale > 0) return measuredScale
  }
  return fallback
}
function typewriterDocumentEndCenter(editor: Editor): number | null {
  try {
    const documentEnd = Math.max(1, editor.state.doc.content.size - 1)
    const coords = editor.view.coordsAtPos(documentEnd)
    return (coords.top + coords.bottom) / 2
  } catch {
    return null
  }
}
function updateTypewriterPageExtent(): void {
  if (!typewriterMode.value) return
  const editor = editorRef.value?.getEditor()
  const container = editorScrollContainer()
  const sheet = continuousSheet()
  const pages = documentPages()
  if (!editor || !container || !sheet || !pages) return

  const documentEndCenter = typewriterDocumentEndCenter(editor)
  if (documentEndCenter === null) return
  const targetY = container.getBoundingClientRect().top + container.clientHeight * TYPEWRITER_RATIO
  const currentMaxScrollTop = Math.max(0, container.scrollHeight - container.clientHeight)
  const desiredMaxScrollTop = Math.max(
    0,
    container.scrollTop + visualDeltaToScrollDelta(documentEndCenter - targetY, sheet),
  )
  // document-pages is normally a flex-fill viewport. In typewriter mode its
  // exact height owns the artificial trailing scroll range instead.
  const nextHeight = Math.max(0, pages.offsetHeight + desiredMaxScrollTop - currentMaxScrollTop)
  pages.style.overflow = 'hidden'
  if (Math.abs((Number.parseFloat(pages.style.height) || 0) - nextHeight) > TYPEWRITER_EPSILON) {
    pages.style.height = `${nextHeight}px`
  }
}
function cancelTypewriterTailCorrection(): void {
  typewriterTailGeneration += 1
  if (typewriterTailFrame !== undefined) {
    window.cancelAnimationFrame(typewriterTailFrame)
    typewriterTailFrame = undefined
  }
}
function scheduleTypewriterTailCorrection(): void {
  if (typewriterTailFrame !== undefined) return
  const generation = typewriterTailGeneration
  typewriterTailFrame = window.requestAnimationFrame(() => {
    typewriterTailFrame = undefined
    if (!typewriterMode.value || generation !== typewriterTailGeneration) return
    updateTypewriterTail(false)
  })
}
function updateTypewriterTail(scheduleCorrection = true): void {
  if (!typewriterMode.value) return
  const container = editorScrollContainer()
  const sheet = continuousSheet()
  const tail = ensureTypewriterTail()
  if (!container || !sheet || !tail) return

  const desiredVisualHeight = container.clientHeight * TYPEWRITER_RATIO
  const layoutHeight = desiredVisualHeight / typewriterTailVisualScale(tail, sheetZoomScale(sheet))
  const currentLayoutHeight = Number.parseFloat(tail.style.height)
  const heightChanged = !Number.isFinite(currentLayoutHeight)
    || Math.abs(currentLayoutHeight - layoutHeight) > TYPEWRITER_EPSILON
  if (heightChanged) {
    tail.style.height = `${layoutHeight}px`
  }
  updateTypewriterPageExtent()
  if (heightChanged && scheduleCorrection) scheduleTypewriterTailCorrection()
}
function handleTypewriterViewportResize(): void {
  updateTypewriterTail()
}
function setTypewriterScrollTop(container: HTMLElement, nextScrollTop: number): void {
  if (Math.abs(nextScrollTop - container.scrollTop) <= TYPEWRITER_EPSILON) return
  container.scrollTop = nextScrollTop
  typewriterProgrammaticScrollTop = container.scrollTop
}
function trackTypewriterCaret(restoreWorkingLine = false): void {
  if (!typewriterMode.value) return
  updateTypewriterTail()
  const editor = editorRef.value?.getEditor()
  const container = editorScrollContainer()
  const sheet = continuousSheet()
  if (!editor || !container || !sheet) return
  try {
    const coords = editor.view.coordsAtPos(editor.state.selection.from)
    const caretCenter = (coords.top + coords.bottom) / 2
    const targetY = container.getBoundingClientRect().top + container.clientHeight * TYPEWRITER_RATIO
    if (restoreWorkingLine || caretCenter >= targetY - TYPEWRITER_EPSILON) {
      setTypewriterScrollTop(container, container.scrollTop + visualDeltaToScrollDelta(caretCenter - targetY, sheet))
    }
  } catch {
    // The editor can briefly recreate its view while loading a document.
  }
}
function scheduleTypewriterTracking(): void {
  if (!typewriterMode.value) return
  typewriterManualBrowsing = false
  void nextTick(trackTypewriterCaret)
}
function cancelTypewriterActivation(): void {
  typewriterActivationGeneration += 1
  if (typewriterActivationFrame !== undefined) {
    window.cancelAnimationFrame(typewriterActivationFrame)
    typewriterActivationFrame = undefined
  }
}
function cancelTypewriterZoomAdjustment(): void {
  typewriterZoomGeneration += 1
  pendingTypewriterZoomAnchor = null
  if (typewriterZoomFrame !== undefined) {
    window.cancelAnimationFrame(typewriterZoomFrame)
    typewriterZoomFrame = undefined
  }
}
function captureTypewriterZoomAnchor(): TypewriterZoomAnchor | null {
  const editor = editorRef.value?.getEditor()
  const container = editorScrollContainer()
  const sheet = continuousSheet()
  if (!editor || !container || !sheet) return null
  try {
    const coords = editor.view.coordsAtPos(editor.state.selection.from)
    const caretCenter = (coords.top + coords.bottom) / 2
    const containerRect = container.getBoundingClientRect()
    const targetY = containerRect.top + container.clientHeight * TYPEWRITER_RATIO
    const anchor: TypewriterZoomAnchor = {
      caretOffset: caretCenter - containerRect.top,
      layoutScrollTop: container.scrollTop / sheetZoomScale(sheet),
      keepWorkingLine: !typewriterManualBrowsing && Math.abs(caretCenter - targetY) <= TYPEWRITER_EPSILON,
    }
    if (typewriterManualBrowsing) {
      const position = editor.view.posAtCoords({
        left: containerRect.left + containerRect.width / 2,
        top: containerRect.top + container.clientHeight * TYPEWRITER_RATIO,
      })?.pos
      if (position !== undefined) {
        const readingCoords = editor.view.coordsAtPos(position)
        anchor.readingPosition = position
        anchor.readingOffset = (readingCoords.top + readingCoords.bottom) / 2 - containerRect.top
      }
    }
    return anchor
  } catch {
    return null
  }
}
function scheduleTypewriterZoomAdjustment(anchor: TypewriterZoomAnchor | null): void {
  const preservedAnchor = pendingTypewriterZoomAnchor ?? anchor
  if (preservedAnchor) pendingTypewriterZoomAnchor = preservedAnchor
  const generation = ++typewriterZoomGeneration
  void nextTick(() => {
    if (!typewriterMode.value || generation !== typewriterZoomGeneration) return
    typewriterZoomFrame = window.requestAnimationFrame(() => {
      typewriterZoomFrame = undefined
      if (!typewriterMode.value || generation !== typewriterZoomGeneration) return
      pendingTypewriterZoomAnchor = null
      const container = editorScrollContainer()
      const sheet = continuousSheet()
      const editor = editorRef.value?.getEditor()
      if (!container || !sheet || !editor) return
      updateTypewriterTail()
      if (!preservedAnchor) return
      if (preservedAnchor.keepWorkingLine) {
        trackTypewriterCaret(true)
        return
      }
      if (typewriterManualBrowsing) {
        if (preservedAnchor.readingPosition !== undefined && preservedAnchor.readingOffset !== undefined) {
          try {
            const readingCoords = editor.view.coordsAtPos(preservedAnchor.readingPosition)
            const readingOffset = (readingCoords.top + readingCoords.bottom) / 2 - container.getBoundingClientRect().top
            setTypewriterScrollTop(
              container,
              container.scrollTop + visualDeltaToScrollDelta(readingOffset - preservedAnchor.readingOffset, sheet),
            )
            return
          } catch {
            // Fall back to the scaled scroll offset while the editor recreates its view.
          }
        }
        setTypewriterScrollTop(container, preservedAnchor.layoutScrollTop * sheetZoomScale(sheet))
        return
      }
      try {
        const coords = editor.view.coordsAtPos(editor.state.selection.from)
        const caretOffset = (coords.top + coords.bottom) / 2 - container.getBoundingClientRect().top
        setTypewriterScrollTop(
          container,
          container.scrollTop + visualDeltaToScrollDelta(caretOffset - preservedAnchor.caretOffset, sheet),
        )
      } catch {
        // The editor may be recreating its view while the zoom is applied.
      }
    })
  })
}
function scheduleTypewriterActivation(): void {
  const generation = ++typewriterActivationGeneration
  void nextTick(() => {
    if (!typewriterMode.value || generation !== typewriterActivationGeneration) return
    observeTypewriterContainer()
    bindTypewriterEditor()
    updateTypewriterTail()
    typewriterActivationFrame = window.requestAnimationFrame(() => {
      typewriterActivationFrame = undefined
      if (!typewriterMode.value || generation !== typewriterActivationGeneration) return
      updateTypewriterTail()
      trackTypewriterCaret()
    })
  })
}
function bindTypewriterEditor(): void {
  const editor = editorRef.value?.getEditor()
  if (!editor || editor === typewriterEditor) return
  typewriterEditor?.off('update', scheduleTypewriterTracking)
  editor.on('update', scheduleTypewriterTracking)
  typewriterEditor = editor
}
function observeTypewriterContainer(): void {
  const container = editorScrollContainer()
  if (container === observedTypewriterContainer) return
  typewriterResizeObserver?.disconnect()
  typewriterResizeObserver = undefined
  observedTypewriterContainer = container
  if (!container || typeof ResizeObserver === 'undefined') return
  typewriterResizeObserver = new ResizeObserver(handleTypewriterViewportResize)
  typewriterResizeObserver.observe(container)
}
function toggleTypewriterMode(): void {
  typewriterMode.value = !typewriterMode.value
  if (!typewriterMode.value) {
    cancelTypewriterActivation()
    cancelTypewriterTailCorrection()
    cancelTypewriterZoomAdjustment()
    typewriterManualBrowsing = false
    typewriterProgrammaticScrollTop = undefined
    removeTypewriterTail()
    return
  }
  typewriterManualBrowsing = false
  typewriterProgrammaticScrollTop = undefined
  scheduleTypewriterActivation()
}
function saveEditorPosition(): void {
  const editor = editorRef.value?.getEditor()
  if (!editor) return
  try {
    const selection = editor.state.selection.from
    const scrollTop = editorScrollContainer()?.scrollTop ?? 0
    localStorage.setItem(positionStorageKey(), JSON.stringify({ selection, scrollTop } satisfies EditorPosition))
  } catch {
    // Position memory is optional in restricted embedded webviews.
  }
}
async function restoreEditorPosition(): Promise<boolean> {
  const saved = savedEditorPosition()
  if (!saved) return true
  const editor = editorRef.value?.getEditor()
  if (!editor) return false

  await nextTick()
  const position = Math.min(saved.selection, Math.max(1, editor.state.doc.content.size))
  editor.commands.setTextSelection(position)
  editor.commands.focus()
  editor.commands.scrollIntoView()
  const scrollContainer = editorScrollContainer()
  if (scrollContainer) scrollContainer.scrollTop = saved.scrollTop
  return true
}
function scheduleEditorPositionRestore(force = false): void {
  if (force) hasRestoredEditorPosition = false
  if (hasRestoredEditorPosition || positionRestoreTimer !== undefined) return
  let attempts = 0
  const attempt = async () => {
    positionRestoreTimer = undefined
    if (await restoreEditorPosition()) {
      hasRestoredEditorPosition = true
      return
    }
    attempts += 1
    if (attempts < 40) positionRestoreTimer = window.setTimeout(() => void attempt(), 50)
  }
  void attempt()
}
function schedulePositionSave(): void {
  if (positionSaveTimer !== undefined) return
  positionSaveTimer = window.setTimeout(() => {
    positionSaveTimer = undefined
    saveEditorPosition()
  }, 250)
}
function handleEditorSelectionChange(): void {
  const selection = window.getSelection()
  const anchor = selection?.anchorNode
  if (!anchor || !editorShell.value?.contains(anchor)) return
  schedulePositionSave()
}
function handleEditorScroll(): void {
  schedulePositionSave()
  if (!typewriterMode.value) return
  const container = editorScrollContainer()
  if (!container) return
  if (
    typewriterProgrammaticScrollTop !== undefined
    && Math.abs(container.scrollTop - typewriterProgrammaticScrollTop) <= TYPEWRITER_EPSILON
  ) {
    typewriterProgrammaticScrollTop = undefined
    return
  }
  typewriterProgrammaticScrollTop = undefined
  typewriterManualBrowsing = true
}
function configureKitLocale() {
  // The package's public type only lists bundled locales, while its runtime
  // intentionally accepts host locale keys and message dictionaries.
  createI18n({ locale: 'en-US', messages: tiptapLocale(t) as never })
}
function update(next: JSONContent) {
  const json = next as TiptapDocument
  // The editor kit can emit an empty document while it refreshes after an
  // asynchronous save. That value is not a user edit and must not replace the
  // draft that was just recorded.
  if (processing.value && countTextSymbols(json) === 0 && countTextSymbols(editorContent.value) > 0) return
  editorContent.value = json
  scheduleSave(json)
  scheduleTypewriterTracking()
}
function captureEditorContent(): TiptapDocument {
  const latest = editorRef.value?.getJSON()
  if (!latest || typeof latest !== 'object') return content.value
  const json = latest as TiptapDocument
  if (countTextSymbols(json) === 0 && countTextSymbols(content.value) > 0) return content.value
  editorContent.value = json
  setContent(json)
  return json
}
function repairEditorSnapshot(snapshot: TiptapDocument): void {
  if (countTextSymbols(snapshot) === 0) return
  const editor = editorRef.value?.getEditor()
  if (editor && countTextSymbols(editor.getJSON()) > 0) return

  editorContent.value = snapshot
  setContent(snapshot)
  if (editor) {
    editor.commands.setContent(snapshot, { emitUpdate: false })
    scheduleEditorPositionRestore(true)
    return
  }
  // If the kit destroyed its internal editor during the update, recreate the
  // component from the saved snapshot instead of leaving an empty workspace.
  editorInstanceKey.value += 1
  scheduleEditorPositionRestore(true)
}
function countTextSymbols(value: unknown): number {
  if (!value || typeof value !== 'object') return 0
  const node = value as { text?: unknown; content?: unknown }
  return (typeof node.text === 'string' ? Array.from(node.text).length : 0)
    + (Array.isArray(node.content) ? node.content.reduce((total, child) => total + countTextSymbols(child), 0) : 0)
}
function setZoom(next: number) {
  const normalized = Math.min(500, Math.max(70, next))
  if (normalized === zoom.value) return
  const anchor = typewriterMode.value ? captureTypewriterZoomAnchor() : null
  zoom.value = normalized
  if (typewriterMode.value) scheduleTypewriterZoomAdjustment(anchor)
}
function setFontFamily(): void {
  editorRef.value?.getEditor()?.chain().focus().setMark('textStyle', { fontFamily: selectedFontFamily.value }).run()
}
function setFontSize(): void {
  editorRef.value?.getEditor()?.chain().focus().setMark('textStyle', { fontSize: `${selectedFontSize.value}pt` }).run()
}
function setLineHeight(): void {
  const editor = editorRef.value?.getEditor()
  if (!editor) return
  // The kit registers this command at runtime but does not expose it in its
  // public chained-command type.
  const commands = editor.chain() as unknown as { focus: () => { setLineHeight: (value: string) => { run: () => void } } }
  commands.focus().setLineHeight(selectedLineHeight.value).run()
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
async function recordTextProgress(force = false, snapshot = captureEditorContent()): Promise<boolean> {
  if (recording.value || countTextSymbols(snapshot) <= 0 || (!force && !canRecordText.value)) return false
  recording.value = true
  try {
    const result = await saveAndRecord(snapshot)
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
async function flushAndRecord(recordProgress = false): Promise<void> {
  if (flushPromise) return flushPromise
  const operation = (async () => {
    const snapshot = captureEditorContent()
    try {
      if (recordProgress) {
        const recorded = await recordTextProgress(true, snapshot)
        // The document itself may have changed even when rounding/duplicate
        // protection correctly produced no progress entry. Keep project counters
        // and cached detail views in sync with that saved content as well.
        if (!recorded) announceDataChange('projects')
        return
      }
      saving.value = true
      try {
        await save(true, snapshot)
      } catch (error) {
        status.value = t(error instanceof Error ? error.message : 'Не удалось сохранить')
      } finally {
        saving.value = false
      }
    } finally {
      await nextTick()
      repairEditorSnapshot(snapshot)
    }
  })()
  flushPromise = operation
  try {
    await operation
  } finally {
    if (flushPromise === operation) flushPromise = null
  }
}
function onRecordClick(): void { void flushAndRecord(true) }
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
  if (external.content) {
    editor.commands.setContent(external.content)
  } else if (external.html) {
    editor.commands.setContent(external.html)
  }
  const json = external.content ?? editor.getJSON() as TiptapDocument
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
  if (currentPlatform() === 'tauri') {
    const targetPath = await pickDesktopWordSavePath('Экспортировать документ Word', `${props.title}.docx`)
    if (!targetPath) return
    const { invoke } = await import('@tauri-apps/api/core')
    await invoke('export_word_document', { command: { content: editorContent.value, targetPath } })
    return
  }
  const blob = await exportDocx(editorContent.value); const url = URL.createObjectURL(blob); const anchor = document.createElement('a')
  anchor.href = url; anchor.download = `${props.title}.docx`; anchor.click(); URL.revokeObjectURL(url)
}
function importWord() { const input = document.createElement('input'); input.type = 'file'; input.accept = '.docx'; input.onchange = async () => { const file = input.files?.[0]; if (!file || !editorRef.value) return; if (currentPlatform() === 'tauri') { const parsed = await (await import('@/api/documents')).documentsApi.parseWord(new Uint8Array(await file.arrayBuffer()), file.name); setContent(parsed.content); editorRef.value.getEditor()?.commands.setContent(parsed.content); return } const { importDocx } = await import('@/services/documentDocx'); const html = await importDocx(await file.arrayBuffer()); editorRef.value.getEditor()?.commands.setContent(html) }; input.click() }

function findToolbarTarget(): void {
  const toolbar = editorShell.value?.querySelector<HTMLElement>('.word-toolbar')
  if (!toolbar) return
  toolbarTarget.value = toolbar
  toolbarObserver?.disconnect()
  toolbarObserver = undefined
}

watch(content, (next) => { editorContent.value = next }, { deep: true })
watch(documentState, async (next) => {
  if (!next) return
  await nextTick()
  scheduleEditorPositionRestore()
  observeTypewriterContainer()
  bindTypewriterEditor()
})
watch(() => locale.language, configureKitLocale)
watch(() => theme.resolved, setWordTheme, { immediate: true })
configureKitLocale()
onMounted(() => {
  window.addEventListener('keydown', handleEscape, true)
  window.addEventListener('pagehide', saveEditorPosition)
  document.addEventListener('selectionchange', handleEditorSelectionChange)
  editorShell.value?.addEventListener('scroll', handleEditorScroll, true)
  window.addEventListener('resize', handleTypewriterViewportResize)
  void nextTick(bindTypewriterEditor)
  externalTimer = window.setInterval(() => void importExternal().catch(() => undefined), 5000)
  void loadProjectEntity().catch(() => undefined)
  stopProjectDataChanges = onDataChange((scope) => {
    if (scope === 'projects') void loadProjectEntity().catch(() => undefined)
  })
  findToolbarTarget()
  if (!toolbarTarget.value && editorShell.value) {
    toolbarObserver = new MutationObserver(findToolbarTarget)
    toolbarObserver.observe(editorShell.value, { childList: true, subtree: true })
  }
  if (window.__TAURI_INTERNALS__) {
    void import('@tauri-apps/api/window').then(async ({ getCurrentWindow }) => {
      stopCloseListener = await getCurrentWindow().onCloseRequested(async (event) => {
        event.preventDefault()
        if (closeInProgress) return
        closeInProgress = true
        try {
          saveEditorPosition()
          await flushAndRecord()
        } finally {
          const removeCloseListener = stopCloseListener
          stopCloseListener = undefined
          removeCloseListener?.()
          await getCurrentWindow().destroy()
        }
      })
    })
  }
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleEscape, true)
  window.removeEventListener('pagehide', saveEditorPosition)
  document.removeEventListener('selectionchange', handleEditorSelectionChange)
  editorShell.value?.removeEventListener('scroll', handleEditorScroll, true)
  window.removeEventListener('resize', handleTypewriterViewportResize)
  if (positionSaveTimer !== undefined) window.clearTimeout(positionSaveTimer)
  if (positionRestoreTimer !== undefined) window.clearTimeout(positionRestoreTimer)
  saveEditorPosition()
  window.clearInterval(externalTimer)
  projectLoadSequence += 1
  toolbarObserver?.disconnect()
  toolbarObserver = undefined
  typewriterResizeObserver?.disconnect()
  typewriterResizeObserver = undefined
  observedTypewriterContainer = null
  cancelTypewriterActivation()
  cancelTypewriterTailCorrection()
  cancelTypewriterZoomAdjustment()
  typewriterProgrammaticScrollTop = undefined
  typewriterEditor?.off('update', scheduleTypewriterTracking)
  typewriterEditor = null
  removeTypewriterTail()
  stopProjectDataChanges?.()
  stopCloseListener?.()
})
onBeforeRouteLeave(async () => { saveEditorPosition(); await flushAndRecord() })
</script>

<template>
  <section class="document-editor-view">
    <header class="document-editor-view__header">
      <div class="document-editor-view__title">
        <button class="document-editor-view__back" type="button" :title="scope.stageId ? t('Вернуться к источнику') : t('Вернуться к проекту')" :aria-label="scope.stageId ? t('Вернуться к источнику') : t('Вернуться к проекту')" @click="closeEditor">← {{ scope.stageId ? t('К источнику') : t('К проекту') }}</button>
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
      <div ref="editorShell" class="document-editor-view__editor-shell">
        <TiptapProEditor
          v-if="documentState"
          :key="editorInstanceKey"
          ref="editorRef"
          :initial-content="content"
          class="nfprogress-word-editor"
          :class="{ 'nfprogress-word-editor--typewriter': typewriterMode }"
          :style="{ '--nf-editor-zoom': `${zoom / 100}` }"
          version="advanced"
          locale="en-US"
          :document-id="editorDocumentId"
          :features="{ headerNav: true, footerNav: false, table: false, tableToolbar: false, image: false, linkBubbleMenu: false, floatingMenu: false, slashCommand: false, dragHandleMenu: false, aiChat: false, aiSettings: false }"
          @update="update"
        />
        <Teleport v-if="toolbarTarget" :to="toolbarTarget">
          <div class="document-editor-view__font-controls">
            <label class="document-editor-view__font-control">
              <select v-model="selectedFontFamily" :aria-label="t('Шрифт')" @change="setFontFamily">
                <option v-for="font in WORD_FONT_FAMILIES" :key="font" :value="font">{{ font }}</option>
              </select>
            </label>
            <label class="document-editor-view__font-control">
              <select v-model="selectedFontSize" :aria-label="t('Размер текста')" @change="setFontSize">
                <option v-for="size in WORD_FONT_SIZES" :key="size" :value="size">{{ size }} pt</option>
              </select>
            </label>
            <label class="document-editor-view__font-control">
              <select v-model="selectedLineHeight" :aria-label="t('Межстрочный интервал')" @change="setLineHeight">
                <option v-for="lineHeight in LINE_HEIGHTS" :key="lineHeight" :value="lineHeight">{{ lineHeight }}</option>
              </select>
            </label>
          </div>
        </Teleport>
      </div>
      <footer class="document-editor-view__statusbar" aria-label="Статус документа">
        <div v-if="projectEntity" class="document-editor-view__status-info">
          <span class="document-editor-view__unit-count" aria-live="polite">{{ t('Прогресс') }}: <strong>{{ entityProgressLabel }}</strong></span>
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
        <div class="document-editor-view__view-controls">
          <button
            type="button"
            class="document-editor-view__typewriter-toggle"
            :class="{ 'document-editor-view__typewriter-toggle--active': typewriterMode }"
            :title="typewriterTitle"
            :aria-label="typewriterTitle"
            :aria-pressed="typewriterMode"
            @click="toggleTypewriterMode"
          >
            <svg class="document-editor-view__typewriter-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
              <path d="M7 8.5V4h10v4.5" />
              <path d="M5.5 8.5h13a3 3 0 0 1 3 3V16h-3v4H5.5v-4h-3v-4.5a3 3 0 0 1 3-3Z" />
              <path d="M6.5 13h11M7.5 16.5h9" />
              <circle cx="8" cy="18.5" r=".65" />
              <circle cx="11" cy="18.5" r=".65" />
              <circle cx="14" cy="18.5" r=".65" />
              <circle cx="17" cy="18.5" r=".65" />
            </svg>
          </button>
          <div class="document-editor-view__zoom" role="group" :aria-label="t('Масштаб документа')">
            <button type="button" :title="t('Уменьшить масштаб')" :aria-label="t('Уменьшить масштаб')" :disabled="zoom <= 70" @click="setZoom(zoom - 10)">−</button>
            <button type="button" :title="t('Сбросить масштаб')" :aria-label="t('Сбросить масштаб')" @click="setZoom(100)">{{ zoom }}%</button>
            <button type="button" :title="t('Увеличить масштаб')" :aria-label="t('Увеличить масштаб')" :disabled="zoom >= 500" @click="setZoom(zoom + 10)">+</button>
          </div>
        </div>
      </footer>
    </div>
    <DocumentConflictResolver v-if="showConflict" @resolve="resolveConflict" />
  </section>
</template>

<style scoped>
.document-editor-view{width:min(100%,88rem);margin:0 auto;padding:var(--nf-space-5);color:var(--nf-color-text)}.document-editor-view__header{display:flex;align-items:center;justify-content:space-between;gap:1rem;margin-bottom:.75rem}.document-editor-view__title{display:grid;gap:.35rem}.document-editor-view__back{display:inline-flex;align-items:center;width:max-content;min-height:2rem;padding:0 .45rem;color:var(--nf-color-text-muted);font:inherit;font-size:.85rem;font-weight:700;cursor:pointer;background:transparent;border:0;border-radius:var(--nf-radius-sm)}.document-editor-view__back:hover,.document-editor-view__back:focus-visible{color:var(--nf-color-text);background:color-mix(in srgb,var(--nf-color-primary) 10%,transparent);outline:none}.document-editor-view__header h1,.document-editor-view__eyebrow{margin:0}.document-editor-view__eyebrow{color:var(--nf-color-text-muted);font-size:.78rem;font-weight:800;text-transform:uppercase}.document-editor-view__actions{display:flex;flex-wrap:wrap;align-items:center;justify-content:flex-end;gap:.5rem}.document-editor-view__actions span{font-size:.82rem;color:var(--nf-color-text-muted)}.document-editor-view__font-control select{height:2rem;padding:0 .45rem;color:var(--nf-color-text);font:inherit;font-size:.85rem;background:var(--nf-color-canvas);border:1px solid var(--nf-color-border);border-radius:var(--nf-radius-sm)}.nfprogress-word-editor{--tiptap-bg:var(--nf-color-surface);--tiptap-bg-secondary:var(--nf-color-canvas);--tiptap-bg-hover:color-mix(in srgb,var(--nf-color-primary) 10%,var(--nf-color-surface));--tiptap-toolbar-bg:var(--nf-color-surface);--tiptap-text:var(--nf-color-text);--tiptap-text-secondary:var(--nf-color-text-muted);--tiptap-border:var(--nf-color-border);--tiptap-border-hover:var(--nf-color-primary);--tiptap-border-focus:var(--nf-color-primary);--tiptap-primary:var(--nf-color-primary);--tiptap-primary-hover:var(--nf-color-primary);--tiptap-link:var(--nf-color-primary);min-height:calc(100dvh - 11rem);border:1px solid var(--nf-color-border);border-radius:var(--nf-radius-lg);overflow:hidden;background:var(--nf-color-canvas);box-shadow:var(--nf-shadow-card)}.nfprogress-word-editor :deep(.word-toolbar){display:flex;flex-wrap:nowrap;align-items:center;min-height:46px;max-height:50px;padding:4px 8px!important;overflow-x:auto;overflow-y:hidden;background:var(--nf-color-surface)!important;border-bottom-color:var(--nf-color-border)!important;scrollbar-width:thin}.nfprogress-word-editor :deep(.editor-toolbar),.nfprogress-word-editor :deep(.toolbar-left){display:flex;flex:0 0 auto;flex-wrap:nowrap;align-items:center}.nfprogress-word-editor :deep(.toolbar-left>.tool-group:nth-child(4)),.nfprogress-word-editor :deep(.toolbar-left>.tool-group:nth-child(6)),.nfprogress-word-editor :deep(.toolbar-left>.tool-group:nth-child(9)),.nfprogress-word-editor :deep(.toolbar-left>.tool-group:nth-child(11)),.nfprogress-word-editor :deep(.toolbar-left>.tool-group:nth-child(12)),.nfprogress-word-editor :deep(.toolbar-left>.tool-group:nth-child(13)),.nfprogress-word-editor :deep(.toolbar-left>.tool-group:nth-child(5) .tt-toolbar-button:last-child),.nfprogress-word-editor :deep(.toolbar-left>.tool-group:nth-child(7) .tt-toolbar-button:last-child){display:none!important}.nfprogress-word-editor :deep(.tt-toolbar-button),.nfprogress-word-editor :deep(.tt-dropdown-btn){min-width:32px!important;height:32px!important;color:var(--nf-color-text)!important;border-radius:var(--nf-radius-sm)!important}.nfprogress-word-editor :deep(.tt-toolbar-button:hover),.nfprogress-word-editor :deep(.tt-dropdown-btn:hover){background:var(--tiptap-bg-hover)!important}.nfprogress-word-editor :deep(.word-document-container){min-height:calc(100dvh - 16rem);padding:1.5rem;background:var(--nf-color-canvas)!important;overflow:auto}.nfprogress-word-editor :deep(.document-pages){display:block!important;width:100%!important;margin:0 auto!important;transform:none!important;transform-origin:top center}.nfprogress-word-editor :deep(.continuous-pages){box-sizing:border-box;width:min(850px,100%)!important;max-width:850px!important;min-height:1120px;margin:0 auto!important;padding:5rem 5.5rem!important;zoom:var(--nf-editor-zoom,1);background:color-mix(in srgb,var(--nf-color-surface) 82%,white)!important;color:var(--nf-color-text)!important;box-shadow:0 3px 18px rgb(0 0 0 / 18%)!important}.nfprogress-word-editor :deep(.word-content-multi .ProseMirror){box-sizing:border-box;width:100%;min-height:1000px;padding:0!important;color:var(--nf-color-text)!important;background:transparent!important;font-family:Arial,sans-serif!important;font-size:12pt!important;line-height:1.5}.nfprogress-word-editor :deep(.template-list),.nfprogress-word-editor :deep(.gallery-grid){display:none!important}.nfprogress-word-editor :deep(.ant-upload-wrapper){max-width:26rem}.nfprogress-word-editor :deep(.ant-dropdown-menu),.nfprogress-word-editor :deep(.ant-select-dropdown){font-family:var(--nf-font-sans)}.document-editor-view__statusbar{display:flex;align-items:center;justify-content:space-between;gap:1rem;min-height:2.8rem;padding:.35rem .65rem;color:var(--nf-color-text-muted);font-size:.82rem;background:var(--nf-color-surface);border:1px solid var(--nf-color-border);border-top:0;border-radius:0 0 var(--nf-radius-lg) var(--nf-radius-lg)}.document-editor-view__unit-count strong{color:var(--nf-color-text)}.document-editor-view__zoom{display:inline-flex;align-items:center;overflow:hidden;border:1px solid var(--nf-color-border);border-radius:var(--nf-radius-sm)}.document-editor-view__zoom button{min-width:2rem;min-height:1.8rem;padding:0 .45rem;color:var(--nf-color-text);font:inherit;font-size:.8rem;font-weight:700;cursor:pointer;background:transparent;border:0}.document-editor-view__zoom button+button{border-left:1px solid var(--nf-color-border)}.document-editor-view__zoom button:hover:not(:disabled),.document-editor-view__zoom button:focus-visible{background:color-mix(in srgb,var(--nf-color-primary) 12%,transparent);outline:none}.document-editor-view__zoom button:disabled{color:var(--nf-color-text-muted);cursor:not-allowed;opacity:.55}@media(max-width:44rem){.document-editor-view{padding:var(--nf-space-3)}.document-editor-view__header{align-items:flex-start;flex-direction:column}.document-editor-view__actions{justify-content:flex-start}.nfprogress-word-editor{min-height:calc(100dvh - 15rem)}.nfprogress-word-editor :deep(.word-document-container){padding:.5rem}.nfprogress-word-editor :deep(.continuous-pages){min-height:calc(100dvh - 16rem);padding:2rem 1.25rem!important;box-shadow:none!important}.nfprogress-word-editor :deep(.word-content-multi .ProseMirror){min-height:calc(100dvh - 20rem)}.document-editor-view__statusbar{align-items:flex-start;flex-direction:column}.document-editor-view__zoom{align-self:flex-end}}
.document-editor-view__workspace{display:flex;height:calc(100dvh - 12rem);min-height:30rem;flex-direction:column}.document-editor-view__editor-shell{display:flex;flex:1;min-height:0}.document-editor-view__font-controls{display:flex;order:-1;flex:0 0 auto;align-items:center;gap:.4rem;margin-right:.5rem;padding:0 .65rem 0 0;background:var(--nf-color-surface);border-right:1px solid var(--nf-color-border)}.document-editor-view__font-controls .document-editor-view__font-control select{height:32px}.nfprogress-word-editor{flex:1;min-height:0!important;height:auto!important;border-radius:var(--nf-radius-lg) var(--nf-radius-lg) 0 0}.document-editor-view__statusbar{position:relative;z-index:11;flex-shrink:0}@media(max-width:44rem){.document-editor-view__workspace{height:calc(100dvh - 16rem);min-height:24rem}}
.document-editor-view__status-info{display:flex;align-items:center;flex-wrap:wrap;gap:1rem;min-width:0}.document-editor-view__today-goal{display:inline-flex;align-items:center;gap:.45rem}.document-editor-view__today-goal--complete{color:var(--nf-color-success);font-weight:700}.document-editor-view__today-goal strong{color:var(--nf-color-text)}.document-editor-view__today-goal-progress{display:block;width:4.5rem;height:.36rem;overflow:hidden;background:color-mix(in srgb,var(--nf-color-primary) 18%,var(--nf-color-canvas));border-radius:var(--nf-radius-pill)}.document-editor-view__today-goal-progress-fill{display:block;height:100%;background:var(--nf-color-primary);border-radius:inherit;transition:width .4s ease-out}.document-editor-view__today-goal--complete .document-editor-view__today-goal-progress-fill{background:var(--nf-color-success)}
.nfprogress-word-editor :deep(.word-content-multi .ProseMirror.ProseMirror-focused) { caret-color: var(--nf-color-primary) !important; }
.nfprogress-word-editor--typewriter :deep(.document-pages){flex:0 0 auto!important}
.nfprogress-word-editor--typewriter :deep(.continuous-pages){min-height:0!important;padding-bottom:0!important}
.nfprogress-word-editor--typewriter :deep(.word-content-multi .ProseMirror){min-height:0!important}
.nfprogress-word-editor :deep([data-nf-typewriter-tail]){display:block;box-sizing:border-box;width:100%;pointer-events:none}
.nfprogress-word-editor :deep(.word-document-container){scrollbar-gutter:stable}
.document-editor-view__view-controls{display:inline-flex;flex:0 0 auto;align-items:center;gap:.4rem}.document-editor-view__typewriter-toggle{display:inline-grid;place-items:center;box-sizing:border-box;flex:0 0 auto;width:2rem;height:1.8rem;padding:0;color:var(--nf-color-text);cursor:pointer;background:transparent;border:1px solid var(--nf-color-border);border-radius:var(--nf-radius-sm)}.document-editor-view__typewriter-toggle:hover,.document-editor-view__typewriter-toggle:focus-visible{background:color-mix(in srgb,var(--nf-color-primary) 12%,transparent);outline:none}.document-editor-view__typewriter-toggle--active{color:var(--nf-color-primary);background:color-mix(in srgb,var(--nf-color-primary) 16%,transparent);border-color:var(--nf-color-primary)}.document-editor-view__typewriter-icon{width:1.1rem;height:1.1rem;fill:none;stroke:currentColor;stroke-linecap:round;stroke-linejoin:round;stroke-width:1.6}
</style>
