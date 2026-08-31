<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { IonIcon, IonSpinner } from '@ionic/vue'
import { locateOutline, saveOutline } from 'ionicons/icons'

import { apiErrorMessage } from '@/api/client'
import {
  mindMapBridge,
  parseMindMapData,
  parseMindMapEvents,
  type MindMapInitialization,
} from '@/components/notes/mindMapBridge'
import { useLocaleStore } from '@/stores/locale'
import type { JsonObject, MindMapResponse, NotesScope } from '@/types/notes'

const props = defineProps<{
  map: MindMapResponse
  persist: (data: JsonObject, scope: NotesScope) => Promise<MindMapResponse>
  focusNodeId?: string | null
}>()

const emit = defineEmits<{
  saved: [payload: MindMapResponse]
  escape: []
}>()

const locale = useLocaleStore()
const t = locale.translate
const frame = ref<HTMLIFrameElement | null>(null)
const ready = ref(false)
const saving = ref(false)
const statusMessage = ref(t('Загрузка карты…'))
const errorMessage = ref<string | null>(null)
let pollTimer: number | null = null
let pendingData: JsonObject | null = null
let saveLoopRunning = false
let initialized = false
let lastSavedSerialized = props.map.data ? JSON.stringify(props.map.data) : ''
const persistenceScope: NotesScope = {
  projectId: props.map.project_id,
  stageId: props.map.stage_id,
}

const editorSource = computed(
  () => `${import.meta.env.BASE_URL}mindmap-assets/index.html`,
)

function initialPayload(): MindMapInitialization {
  return {
    data: props.map.data
      ? (JSON.parse(JSON.stringify(props.map.data)) as JsonObject)
      : null,
    editorLabel: t('Редактор карты'),
    emptyStageMapText: t('Карта не была создана при работе над этапом.'),
    floatingNodeName: t('Свободный узел'),
    floatingNoteName: t('Новая заметка'),
    addFloatingNodeLabel: t('Добавить свободный узел'),
    addFloatingNoteLabel: t('Добавить плавающую заметку'),
    searchMapLabel: t('Поиск по карте'),
    searchPlaceholder: t('Поиск узлов и заметок'),
    nothingFoundText: t('Ничего не найдено'),
    detachBranchLabel: t('Отсоединить ветвь'),
    attachBranchLabel: t('Прикрепить к узлу карты'),
    attachTargetPrompt: t('Выберите родительский узел карты'),
    locale: locale.language,
    loadingText: t('Загрузка карты…'),
    newTopicName: t('Новая тема'),
    readOnly: props.map.read_only,
    rootTopic: props.map.name,
  }
}

function stopPolling(): void {
  if (pollTimer !== null) window.clearInterval(pollTimer)
  pollTimer = null
}

function iframeLoaded(): void {
  stopPolling()
  ready.value = false
  initialized = false
  errorMessage.value = null
  statusMessage.value = t('Загрузка карты…')
  const bridge = mindMapBridge(frame.value)
  if (!bridge) {
    errorMessage.value = t('Не удалось загрузить редактор карты.')
    return
  }
  try {
    bridge.initialize(initialPayload())
    initialized = true
    frame.value?.contentWindow?.addEventListener('keydown', handleFrameKeydown, true)
    pollTimer = window.setInterval(pollEvents, 150)
    pollEvents()
  } catch (reason) {
    errorMessage.value = reason instanceof Error ? reason.message : t('Не удалось загрузить редактор карты.')
  }
}

function handleFrameKeydown(event: KeyboardEvent): void {
  if (event.key !== 'Escape') return
  event.preventDefault()
  emit('escape')
}

function pollEvents(): void {
  const bridge = mindMapBridge(frame.value)
  if (!bridge || !initialized) return
  let payload: string
  try {
    payload = bridge.takeEvents()
  } catch {
    errorMessage.value = t('Связь с редактором карты прервана.')
    stopPolling()
    return
  }
  for (const event of parseMindMapEvents(payload)) {
    if (event.type === 'ready') {
      ready.value = true
      statusMessage.value = props.map.read_only
        ? t('Карта доступна только для просмотра.')
        : t('Карта готова.')
      if (props.focusNodeId) bridge.focusNode(props.focusNodeId)
    } else if (event.type === 'changed') {
      statusMessage.value = t('Есть несохранённые изменения.')
    } else if (event.type === 'save') {
      const data = parseMindMapData(event.payload)
      if (data) queueSave(data)
      else errorMessage.value = t('Редактор вернул повреждённые данные карты.')
    } else if (event.type === 'error' || event.type === 'exportError') {
      errorMessage.value = event.details || t('Не удалось обработать карту.')
    } else if (event.type === 'status' && event.message) {
      statusMessage.value = event.message
    }
  }
}

function queueSave(data: JsonObject): void {
  const serialized = JSON.stringify(data)
  if (serialized === lastSavedSerialized && !pendingData) {
    statusMessage.value = t('Все изменения сохранены.')
    return
  }
  pendingData = data
  if (!saveLoopRunning) void flushSaves()
}

async function flushSaves(): Promise<void> {
  saveLoopRunning = true
  saving.value = true
  errorMessage.value = null
  try {
    while (pendingData) {
      const current = pendingData
      pendingData = null
      statusMessage.value = t('Сохраняем карту…')
      try {
        const result = await props.persist(current, persistenceScope)
        lastSavedSerialized = JSON.stringify(result.data ?? current)
        emit('saved', result)
        statusMessage.value = pendingData
          ? t('Сохраняем карту…')
          : t('Все изменения сохранены.')
      } catch (reason) {
        errorMessage.value = apiErrorMessage(reason)
        statusMessage.value = t('Карта не сохранена.')
      }
    }
  } finally {
    saving.value = false
    saveLoopRunning = false
  }
}

function saveNow(): void {
  const bridge = mindMapBridge(frame.value)
  if (!bridge || props.map.read_only) return
  bridge.saveNow()
  pollEvents()
}

function centerMap(): void {
  mindMapBridge(frame.value)?.toCenter()
}

function focusNode(nodeId: string): boolean {
  return mindMapBridge(frame.value)?.focusNode(nodeId) ?? false
}

function updateNodeNote(nodeId: string, text: string): boolean {
  return mindMapBridge(frame.value)?.updateNodeNote(nodeId, text) ?? false
}

function removeNodeNote(nodeId: string): boolean {
  return mindMapBridge(frame.value)?.removeNodeNote(nodeId) ?? false
}

function flushCurrentMap(): void {
  const payload = mindMapBridge(frame.value)?.getDataString()
  const data = parseMindMapData(payload)
  if (data && !props.map.read_only) queueSave(data)
}

onBeforeUnmount(() => {
  flushCurrentMap()
  frame.value?.contentWindow?.removeEventListener('keydown', handleFrameKeydown, true)
  stopPolling()
})

watch(
  () => props.focusNodeId,
  (nodeId) => {
    if (nodeId && ready.value) focusNode(nodeId)
  },
)

defineExpose({ focusNode, updateNodeNote, removeNodeNote, saveNow })
</script>

<template>
  <section class="mindmap-editor" :aria-label="t('Карта проекта')">
    <header class="mindmap-editor__toolbar">
      <div class="mindmap-editor__status" aria-live="polite">
        <IonSpinner v-if="saving" name="dots" aria-hidden="true" />
        <span>{{ statusMessage }}</span>
      </div>
      <div class="mindmap-editor__actions">
        <button class="nf-button nf-button--secondary" type="button" :disabled="!ready" @click="centerMap">
          <IonIcon :icon="locateOutline" aria-hidden="true" />
          {{ t('По центру') }}
        </button>
        <button
          class="nf-button"
          type="button"
          :disabled="!ready || saving || map.read_only"
          @click="saveNow"
        >
          <IonIcon :icon="saveOutline" aria-hidden="true" />
          {{ t('Сохранить карту') }}
        </button>
      </div>
    </header>

    <p v-if="map.combined" class="mindmap-editor__notice">
      {{ t('Показана объединённая карта проекта и этапов.') }}
    </p>
    <p v-if="map.has_empty_completed_stage_map" class="mindmap-editor__notice">
      {{ t('У завершённого этапа нет сохранённой карты; его ветвь доступна только для просмотра.') }}
    </p>
    <p v-if="errorMessage" class="mindmap-editor__error" role="alert">{{ errorMessage }}</p>

    <iframe
      ref="frame"
      class="mindmap-editor__frame"
      :src="editorSource"
      :title="t('Редактор карты')"
      sandbox="allow-scripts allow-same-origin allow-downloads"
      referrerpolicy="no-referrer"
      @load="iframeLoaded"
    />
  </section>
</template>

<style scoped>
.mindmap-editor {
  display: grid;
  min-height: min(70dvh, 54rem);
  overflow: hidden;
  border: 1px solid var(--nf-color-border);
  border-radius: var(--nf-radius-lg);
  background: var(--nf-color-surface);
  box-shadow: var(--nf-shadow-card);
}

.mindmap-editor__toolbar {
  display: flex;
  gap: var(--nf-space-3);
  align-items: center;
  justify-content: space-between;
  padding: var(--nf-space-3) var(--nf-space-4);
  border-bottom: 1px solid var(--nf-color-border);
}

.mindmap-editor__status,
.mindmap-editor__actions {
  display: flex;
  gap: var(--nf-space-2);
  align-items: center;
}

.mindmap-editor__status {
  color: var(--nf-color-text-muted);
  font-size: 0.85rem;
}

.mindmap-editor__notice,
.mindmap-editor__error {
  margin: 0;
  padding: var(--nf-space-2) var(--nf-space-4);
  font-size: 0.82rem;
}

.mindmap-editor__notice {
  background: var(--nf-color-primary-soft);
  color: var(--nf-color-primary);
}

.mindmap-editor__error {
  background: color-mix(in srgb, var(--nf-color-danger) 12%, transparent);
  color: var(--nf-color-danger);
}

.mindmap-editor__frame {
  width: 100%;
  min-height: 36rem;
  border: 0;
  background: #f6f6f6;
}

@media (max-width: 39.99rem) {
  .mindmap-editor {
    min-height: calc(100dvh - 13rem);
    border-radius: var(--nf-radius-md);
  }

  .mindmap-editor__toolbar {
    align-items: stretch;
    flex-direction: column;
  }

  .mindmap-editor__actions {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .mindmap-editor__frame {
    min-height: calc(100dvh - 20rem);
  }
}
</style>
