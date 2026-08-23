<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { IonContent, IonIcon, IonPage } from '@ionic/vue'
import {
  addOutline,
  alertCircleOutline,
  arrowBackOutline,
  documentTextOutline,
  gitBranchOutline,
  searchOutline,
} from 'ionicons/icons'

import MindMapEditor from '@/components/notes/MindMapEditor.vue'
import NoteCard from '@/components/notes/NoteCard.vue'
import NoteEditorDialog from '@/components/notes/NoteEditorDialog.vue'
import StatePanel from '@/components/ui/StatePanel.vue'
import { useProjectNotes } from '@/composables/useProjectNotes'
import { useLocaleStore } from '@/stores/locale'
import type { ProjectNote, ProjectNotePatch } from '@/types/notes'

type WorkspaceView = 'notes' | 'mindmap'

const route = useRoute()
const router = useRouter()
const locale = useLocaleStore()
const t = locale.translate
const projectId = computed(() => String(route.params.projectId ?? ''))
const stageId = computed(() => {
  const value = route.query.stageId
  return typeof value === 'string' && value ? value : null
})
const workspace = useProjectNotes(projectId, stageId)
const activeView = ref<WorkspaceView>('notes')
const search = ref('')
const showArchived = ref(false)
const editingNote = ref<ProjectNote | null>(null)
const pendingFocusNode = ref<string | null>(null)
const mindMapEditor = ref<InstanceType<typeof MindMapEditor> | null>(null)

const visibleNotes = computed(() => {
  const query = search.value.trim().toLocaleLowerCase(locale.localeTag)
  return workspace.notes.value.filter((note) => {
    if (!showArchived.value && note.archived) return false
    if (!query) return true
    const searchable = [
      note.display_title,
      note.title,
      note.content,
      note.stage_name ?? '',
      ...note.tags,
      ...note.system_tags,
    ]
      .join(' ')
      .toLocaleLowerCase(locale.localeTag)
    return searchable.includes(query)
  })
})

function categoryNotes(note: ProjectNote): ProjectNote[] {
  return workspace.notes.value.filter(
    (candidate) => candidate.archived === note.archived && candidate.pinned === note.pinned,
  )
}

function canMove(note: ProjectNote, direction: -1 | 1): boolean {
  const group = categoryNotes(note)
  const index = group.findIndex(({ id }) => id === note.id)
  const target = index + direction
  return index >= 0 && target >= 0 && target < group.length
}

async function moveNote(note: ProjectNote, direction: -1 | 1): Promise<void> {
  const ordered = [...workspace.notes.value]
  const group = categoryNotes(note)
  const groupIndex = group.findIndex(({ id }) => id === note.id)
  const target = group[groupIndex + direction]
  if (!target) return
  const fromIndex = ordered.findIndex(({ id }) => id === note.id)
  const targetIndex = ordered.findIndex(({ id }) => id === target.id)
  if (fromIndex < 0 || targetIndex < 0) return
  ;[ordered[fromIndex], ordered[targetIndex]] = [ordered[targetIndex]!, ordered[fromIndex]!]
  await workspace.reorderNotes(ordered.map(({ id }) => id))
}

async function createNote(): Promise<void> {
  const note = await workspace.createNote()
  if (note) editingNote.value = note
}

async function saveNote(noteId: string, patch: ProjectNotePatch): Promise<void> {
  const previous = editingNote.value
  const updated = await workspace.updateNote(noteId, patch)
  if (!updated) return
  if (previous?.source_type === 'mindmap' && previous.source_node_id) {
    mindMapEditor.value?.updateNodeNote(previous.source_node_id, updated.content)
    await workspace.refreshMindMap()
  }
  editingNote.value = null
}

async function togglePin(note: ProjectNote): Promise<void> {
  await workspace.updateNote(note.id, { pinned: !note.pinned })
}

async function toggleArchive(note: ProjectNote): Promise<void> {
  await workspace.updateNote(note.id, { archived: !note.archived })
}

async function deleteNote(note: ProjectNote): Promise<void> {
  const confirmed = window.confirm(
    t('Удалить заметку «{name}»? Это действие нельзя отменить.', {
      name: note.display_title || note.title || t('Без названия'),
    }),
  )
  if (!confirmed) return
  const removed = await workspace.deleteNote(note.id)
  if (removed && note.source_type === 'mindmap' && note.source_node_id) {
    mindMapEditor.value?.removeNodeNote(note.source_node_id)
    await workspace.refreshMindMap()
  }
}

async function openOnMap(note: ProjectNote): Promise<void> {
  if (!note.source_node_id) return
  activeView.value = 'mindmap'
  pendingFocusNode.value = note.source_node_id
  if (note.owner_type === 'stage' && note.owner_id !== stageId.value) {
    await router.replace({
      name: route.name ?? undefined,
      params: route.params,
      query: { ...route.query, stageId: note.owner_id },
    })
    return
  }
  await nextTick()
  mindMapEditor.value?.focusNode(note.source_node_id)
}

function selectStage(event: Event): void {
  const value = (event.target as HTMLSelectElement).value
  pendingFocusNode.value = null
  const query = { ...route.query }
  if (value) query.stageId = value
  else delete query.stageId
  void router.replace({ name: route.name ?? undefined, params: route.params, query })
}

watch(
  [projectId, stageId],
  () => {
    editingNote.value = null
    void workspace.load()
  },
  { immediate: true },
)

onBeforeUnmount(workspace.invalidate)
</script>

<template>
  <IonPage>
    <IonContent :fullscreen="true" class="notes-content">
      <main class="notes-workspace">
        <RouterLink class="notes-back-link" :to="{ name: 'project-detail', params: { projectId } }">
          <IonIcon :icon="arrowBackOutline" aria-hidden="true" />
          {{ t('Вернуться к проекту') }}
        </RouterLink>

        <header class="notes-header">
          <div>
            <p>{{ t('Рабочее пространство') }}</p>
            <h1>{{ workspace.mindMap.value?.name || t('Заметки проекта') }}</h1>
          </div>
          <label v-if="workspace.context.value.hasStages" class="stage-picker">
            <span>{{ t('Область заметок') }}</span>
            <select :value="stageId ?? ''" @change="selectStage">
              <option value="">{{ t('Весь проект') }}</option>
              <option v-for="stage in workspace.context.value.stages" :key="stage.id" :value="stage.id">
                {{ stage.name }}
              </option>
            </select>
          </label>
        </header>

        <div class="workspace-tabs" role="tablist" :aria-label="t('Заметки и карта')">
          <button
            id="notes-tab"
            type="button"
            role="tab"
            :aria-selected="activeView === 'notes'"
            aria-controls="notes-panel"
            @click="activeView = 'notes'"
          >
            <IonIcon :icon="documentTextOutline" aria-hidden="true" />
            {{ t('Заметки') }}
            <span>{{ workspace.notes.value.length }}</span>
          </button>
          <button
            id="mindmap-tab"
            type="button"
            role="tab"
            :aria-selected="activeView === 'mindmap'"
            aria-controls="mindmap-panel"
            @click="activeView = 'mindmap'"
          >
            <IonIcon :icon="gitBranchOutline" aria-hidden="true" />
            {{ t('Карта') }}
          </button>
        </div>

        <StatePanel
          v-if="workspace.loading.value"
          :title="t('Открываем заметки')"
          :message="t('Сверяем карточки и данные карты.')"
          loading
        />

        <StatePanel
          v-else-if="workspace.error.value && !workspace.notes.value.length && !workspace.mindMap.value"
          :title="t('Не удалось открыть заметки')"
          :message="workspace.error.value"
          :icon="alertCircleOutline"
        >
          <button class="nf-button" type="button" @click="workspace.load">
            {{ t('Повторить') }}
          </button>
        </StatePanel>

        <section
          v-else-if="activeView === 'notes'"
          id="notes-panel"
          role="tabpanel"
          aria-labelledby="notes-tab"
          class="notes-panel"
        >
          <div v-if="workspace.error.value" class="workspace-error" role="alert">
            {{ workspace.error.value }}
          </div>

          <div class="notes-toolbar">
            <label class="notes-search">
              <span class="visually-hidden">{{ t('Поиск по заметкам') }}</span>
              <IonIcon :icon="searchOutline" aria-hidden="true" />
              <input v-model="search" type="search" :placeholder="t('Поиск по заметкам')" />
            </label>
            <label class="archive-filter">
              <input v-model="showArchived" type="checkbox" />
              <span>{{ t('Показывать архив') }}</span>
            </label>
          </div>

          <button
            class="new-note-button"
            type="button"
            :disabled="workspace.readOnly.value || workspace.mutating.value"
            @click="createNote"
          >
            <IonIcon :icon="addOutline" aria-hidden="true" />
            <span>{{ t('Новая заметка') }}</span>
          </button>

          <p v-if="workspace.readOnly.value" class="read-only-notice">
            {{ t('Заметки завершённого проекта доступны только для просмотра.') }}
          </p>

          <div v-if="visibleNotes.length" class="notes-grid">
            <NoteCard
              v-for="note in visibleNotes"
              :key="note.id"
              :note="note"
              :disabled="workspace.mutating.value"
              :can-move-up="canMove(note, -1)"
              :can-move-down="canMove(note, 1)"
              @edit="editingNote = $event"
              @toggle-pin="togglePin"
              @toggle-archive="toggleArchive"
              @delete="deleteNote"
              @move-up="moveNote($event, -1)"
              @move-down="moveNote($event, 1)"
              @open-map="openOnMap"
            />
          </div>

          <StatePanel
            v-else
            :title="search ? t('Ничего не найдено') : t('Заметок пока нет')"
            :message="search
              ? t('Попробуйте изменить запрос или показать архивные карточки.')
              : t('Создайте первую карточку или добавьте плавающую заметку на карте.')"
            :icon="documentTextOutline"
          />
        </section>

        <section
          v-else
          id="mindmap-panel"
          role="tabpanel"
          aria-labelledby="mindmap-tab"
        >
          <MindMapEditor
            v-if="workspace.mindMap.value"
            :key="`${projectId}:${stageId ?? 'project'}`"
            ref="mindMapEditor"
            :map="workspace.mindMap.value"
            :persist="workspace.saveMindMap"
            :focus-node-id="pendingFocusNode"
          />
        </section>
      </main>
    </IonContent>

    <NoteEditorDialog
      :open="editingNote !== null"
      :note="editingNote"
      :submitting="workspace.mutating.value"
      :api-error="workspace.error.value"
      @close="editingNote = null"
      @submit="saveNote"
    />
  </IonPage>
</template>

<style scoped>
.notes-content {
  --background: var(--nf-color-canvas);
}

.notes-workspace {
  width: min(100%, 84rem);
  min-height: 100%;
  margin: 0 auto;
  padding: calc(var(--nf-space-6) + env(safe-area-inset-top)) clamp(1rem, 4vw, 4rem)
    calc(var(--nf-space-7) + env(safe-area-inset-bottom));
}

.notes-back-link {
  display: inline-flex;
  gap: var(--nf-space-2);
  align-items: center;
  min-height: 2.75rem;
  margin-bottom: var(--nf-space-5);
  padding: 0 var(--nf-space-2);
  border-radius: var(--nf-radius-sm);
  color: var(--nf-color-primary);
  font-weight: 700;
  text-decoration: none;
}

.notes-header {
  display: flex;
  gap: var(--nf-space-5);
  align-items: end;
  justify-content: space-between;
}

.notes-header p,
.notes-header h1 {
  margin: 0;
}

.notes-header p {
  color: var(--nf-color-primary);
  font-size: 0.75rem;
  font-weight: 800;
  text-transform: uppercase;
}

.notes-header h1 {
  margin-top: var(--nf-space-2);
  color: var(--nf-color-text);
  font-family: var(--nf-font-serif);
  font-size: clamp(2.25rem, 6vw, 4.25rem);
  letter-spacing: -0.04em;
  line-height: 1;
  overflow-wrap: anywhere;
}

.stage-picker {
  display: grid;
  gap: var(--nf-space-2);
  min-width: min(20rem, 100%);
  color: var(--nf-color-text-muted);
  font-size: 0.78rem;
  font-weight: 700;
}

.stage-picker select {
  min-height: 2.75rem;
  padding: 0 var(--nf-space-3);
  border: 1px solid var(--nf-color-border);
  border-radius: var(--nf-radius-sm);
  background: var(--nf-color-surface-raised);
  color: var(--nf-color-text);
}

.workspace-tabs {
  display: inline-flex;
  gap: var(--nf-space-1);
  margin: var(--nf-space-6) 0 var(--nf-space-5);
  padding: var(--nf-space-1);
  border: 1px solid var(--nf-color-border);
  border-radius: var(--nf-radius-pill);
  background: var(--nf-color-surface-muted);
}

.workspace-tabs button {
  display: inline-flex;
  gap: var(--nf-space-2);
  align-items: center;
  min-height: 2.75rem;
  padding: 0.55rem 1rem;
  border: 0;
  border-radius: var(--nf-radius-pill);
  background: transparent;
  color: var(--nf-color-text-muted);
  font-weight: 750;
  cursor: pointer;
}

.workspace-tabs button[aria-selected='true'] {
  background: var(--nf-color-surface-raised);
  color: var(--nf-color-primary);
  box-shadow: 0 2px 8px rgb(0 0 0 / 8%);
}

.workspace-tabs button span {
  min-width: 1.5rem;
  padding: 0.1rem 0.4rem;
  border-radius: var(--nf-radius-pill);
  background: var(--nf-color-primary-soft);
  font-size: 0.72rem;
  text-align: center;
}

.notes-panel {
  display: grid;
  gap: var(--nf-space-5);
}

.notes-toolbar {
  display: grid;
  grid-template-columns: minmax(14rem, 1fr) auto;
  gap: var(--nf-space-3);
  align-items: center;
}

.new-note-button {
  display: flex;
  gap: var(--nf-space-2);
  align-items: center;
  justify-content: center;
  width: 100%;
  min-height: 3.25rem;
  padding: var(--nf-space-3) var(--nf-space-5);
  border: 1px solid color-mix(in srgb, var(--nf-color-primary) 45%, var(--nf-color-border));
  border-radius: var(--nf-radius-sm);
  background: linear-gradient(135deg, var(--nf-color-primary), color-mix(in srgb, var(--nf-color-primary) 76%, var(--nf-color-accent)));
  color: white;
  font-size: 1rem;
  font-weight: 800;
  box-shadow: 0 10px 24px color-mix(in srgb, var(--nf-color-primary) 22%, transparent);
  cursor: pointer;
}

.new-note-button:hover:not(:disabled) { filter: brightness(1.06); }
.new-note-button:disabled { opacity: 0.45; cursor: not-allowed; }

.notes-search {
  display: grid;
  grid-template-columns: 1.25rem minmax(0, 1fr);
  gap: var(--nf-space-2);
  align-items: center;
  min-height: 2.75rem;
  padding: 0 var(--nf-space-3);
  border: 1px solid var(--nf-color-border);
  border-radius: var(--nf-radius-sm);
  background: var(--nf-color-surface-raised);
  color: var(--nf-color-text-muted);
}

.notes-search input {
  width: 100%;
  min-height: 2.6rem;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--nf-color-text);
}

.archive-filter {
  display: inline-flex;
  gap: var(--nf-space-2);
  align-items: center;
  min-height: 2.75rem;
  color: var(--nf-color-text-muted);
  font-size: 0.85rem;
  font-weight: 700;
}

.archive-filter input {
  width: 1.2rem;
  height: 1.2rem;
}

.notes-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--nf-space-4);
  align-items: start;
}

.workspace-error,
.read-only-notice {
  margin: 0;
  padding: var(--nf-space-3) var(--nf-space-4);
  border-radius: var(--nf-radius-sm);
}

.workspace-error {
  background: color-mix(in srgb, var(--nf-color-danger) 12%, transparent);
  color: var(--nf-color-danger);
}

.read-only-notice {
  background: var(--nf-color-primary-soft);
  color: var(--nf-color-primary);
}

@media (max-width: 69.99rem) {
  .notes-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 47.99rem) {
  .notes-header {
    align-items: stretch;
    flex-direction: column;
  }

  .notes-toolbar {
    grid-template-columns: 1fr;
  }

  .notes-grid {
    grid-template-columns: 1fr;
  }

  .workspace-tabs {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    width: 100%;
  }

  .workspace-tabs button {
    justify-content: center;
  }
}
</style>
