<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { IonIcon } from '@ionic/vue'
import { addOutline, documentTextOutline } from 'ionicons/icons'

import { canonicalizeSyncTimestamp } from '@/cloud/syncTimestamp'
import type { BrowserCloudAccountSession } from '@/platform/web/cloudAccountSession'
import { BrowserPersistenceError } from '@/platform/web/persistence'
import type { LocalNoteSource, NativeLegacyNote, NativeLocalProject } from '@/platform/web/localAuthorityRecords'
import type { LocalStage } from '@/platform/web/localStages'
import NoteCard from '@/components/notes/NoteCard.vue'
import NoteEditorDialog from '@/components/notes/NoteEditorDialog.vue'
import { useLocaleStore } from '@/stores/locale'
import type { ProjectNote, ProjectNotePatch } from '@/types/notes'
import type { SupportedLanguage } from '@/types/api'

const unavailableCopy: Record<SupportedLanguage, string> = {
  ru: 'Тексты, прогресс и игровой режим в защищённом пространстве пока недоступны.',
  en: 'Texts, progress, and game mode are not yet available in the encrypted workspace.',
  es: 'Los textos, el progreso y el modo de juego aún no están disponibles en el espacio cifrado.',
  de: 'Texte, Fortschritt und Spielmodus sind im verschlüsselten Arbeitsbereich noch nicht verfügbar.',
  fr: 'Les textes, la progression et le mode jeu ne sont pas encore disponibles dans cet espace chiffré.',
  pt_BR: 'Textos, progresso e modo de jogo ainda não estão disponíveis no espaço criptografado.',
}

const props = defineProps<{ session: BrowserCloudAccountSession }>()
const emit = defineEmits<{ close: [] }>()
const locale = useLocaleStore()
const t = locale.translate
const projectName = ref('')
const newProjectName = ref('')
const projectId = ref('')
const projects = ref<NativeLocalProject[]>([])
const stages = ref<LocalStage[]>([])
const newStageName = ref('')
const editingStageId = ref<string | null>(null)
const editingStageName = ref('')
const notes = ref<ProjectNote[]>([])
const loading = ref(true)
const mutating = ref(false)
const projectMissing = ref(false)
const error = ref<string | null>(null)
const editingNote = ref<ProjectNote | null>(null)
const autosaveStatus = ref<'idle' | 'pending' | 'saving' | 'saved' | 'error'>('idle')
const visibleError = computed(() => error.value)
let writeQueue: Promise<void> = Promise.resolve()
let active = true

function timestamp(): string {
  return canonicalizeSyncTimestamp(new Date().toISOString())
}

function workspaceProject(id: string, name: string): NativeLocalProject {
  return {
    id,
    name: name.trim(),
    goal: null,
    infinite: true,
    unit: 'symbols',
    status: 'активен',
    created_at: timestamp(),
    updated_at: timestamp(),
    payload: {},
  }
}

function displayNote(source: LocalNoteSource, index: number): ProjectNote | null {
  if (source.state !== 'live') return null
  const note = source.note
  return {
    ...note,
    display_title: note.title,
    system_tags: [],
    owner_type: 'project',
    owner_id: note.project_id,
    owner_order: index,
    stage_name: null,
    read_only: false,
  }
}

function safeError(reason: unknown): string {
  if (reason instanceof BrowserPersistenceError) {
    if (reason.code === 'corrupt_record') return t('Зашифрованная заметка повреждена. Данные сохранены; автоматическое восстановление не выполнялось.')
    if (reason.code === 'missing_local_source') return t('Локальный проект ещё не создан.')
    if (reason.code === 'closed') return t('Хранилище заблокировано. Разблокируйте аккаунт и повторите попытку.')
    if (reason.code === 'account_mismatch') return t('Аккаунт или проект не совпадает. Данные не изменены.')
    if (reason.code === 'conflicting_record') return t('Локальный проект с этим идентификатором уже существует. Он не был перезаписан.')
    if (reason.code === 'writer_busy') return t('Другая вкладка использует зашифрованное хранилище.')
    return t('Не удалось открыть зашифрованное локальное хранилище. Данные не изменены.')
  }
  return t('Не удалось сохранить изменения.')
}

async function loadWorkspace(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    const repository = props.session.localNoteRepository()
    const available = await repository.source.listProjects(repository.scope)
    if (!active) return
    projects.value = available
    if (!available.length) {
      projectMissing.value = true
      projectId.value = ''
      notes.value = []
      stages.value = []
      return
    }
    if (!available.some(project => project.id === projectId.value)) projectId.value = available[0]!.id
    const snapshot = await repository.source.readSnapshot(repository.scope, projectId.value)
    const decoded = await repository.source.withDecryptedSnapshot(repository.scope, snapshot.token, async source => structuredClone(source))
    const storedStages = await repository.stages.list(repository.scope, projectId.value)
    if (!active) return
    projectName.value = decoded.project.name
    notes.value = decoded.notes.map(displayNote).filter((note): note is ProjectNote => note !== null)
    stages.value = storedStages
    projectMissing.value = false
  } catch (reason) {
    if (!active) return
    if (reason instanceof BrowserPersistenceError && reason.code === 'missing_local_source') {
      projectMissing.value = true
      notes.value = []
      stages.value = []
    } else {
      error.value = safeError(reason)
    }
  } finally {
    if (active) loading.value = false
  }
}

async function createProject(): Promise<void> {
  const name = projectMissing.value ? projectName.value.trim() : newProjectName.value.trim()
  if (mutating.value || !name) return
  mutating.value = true
  error.value = null
  try {
    const repository = props.session.localNoteRepository()
    const id = crypto.randomUUID()
    await repository.source.createProject(repository.scope, workspaceProject(id, name))
    projectId.value = id
    newProjectName.value = ''
    await loadWorkspace()
  } catch (reason) {
    error.value = safeError(reason)
  } finally {
    mutating.value = false
  }
}

async function selectProject(id: string): Promise<void> {
  if (mutating.value || id === projectId.value) return
  projectId.value = id
  editingNote.value = null
  await loadWorkspace()
}

async function renameProject(): Promise<void> {
  if (mutating.value || !projectId.value || !projectName.value.trim()) return
  mutating.value = true
  error.value = null
  try {
    const repository = props.session.localNoteRepository()
    const snapshot = await repository.source.readSnapshot(repository.scope, projectId.value)
    const old = await repository.source.withDecryptedSnapshot(repository.scope, snapshot.token, async source => structuredClone(source.project))
    await repository.source.replaceProject(repository.scope, snapshot.token, { ...old, name: projectName.value.trim(), updated_at: timestamp() })
    await loadWorkspace()
  } catch (reason) { error.value = safeError(reason) }
  finally { mutating.value = false }
}

async function createStage(): Promise<void> {
  if (mutating.value || !newStageName.value.trim() || !projectId.value) return
  mutating.value = true
  error.value = null
  try {
    const repository = props.session.localNoteRepository()
    const unit = projects.value.find(project => project.id === projectId.value)?.unit ?? 'symbols'
    await repository.stages.create(repository.scope, projectId.value, newStageName.value, unit)
    newStageName.value = ''
    await loadWorkspace()
  } catch (reason) { error.value = safeError(reason) }
  finally { mutating.value = false }
}

async function renameStage(): Promise<void> {
  if (mutating.value || !editingStageId.value || !editingStageName.value.trim()) return
  mutating.value = true
  error.value = null
  try {
    const repository = props.session.localNoteRepository()
    const revision = stages.value.find(stage => stage.id === editingStageId.value)?.revision
    if (revision === undefined) throw new BrowserPersistenceError('stale_source')
    await repository.stages.rename(repository.scope, projectId.value, editingStageId.value, editingStageName.value, revision)
    editingStageId.value = null
    await loadWorkspace()
  } catch (reason) { error.value = safeError(reason) }
  finally { mutating.value = false }
}

async function removeStage(stage: LocalStage): Promise<void> {
  if (mutating.value || !window.confirm(`${t('Удалить')} «${stage.name}»?`)) return
  mutating.value = true
  error.value = null
  try {
    const repository = props.session.localNoteRepository()
    await repository.stages.remove(repository.scope, projectId.value, stage.id, stage.revision)
    await loadWorkspace()
  } catch (reason) { error.value = safeError(reason) }
  finally { mutating.value = false }
}

async function moveStage(index: number, direction: -1 | 1): Promise<void> {
  const target = index + direction
  if (mutating.value || target < 0 || target >= stages.value.length) return
  const ids = stages.value.map(stage => stage.id)
  ;[ids[index], ids[target]] = [ids[target]!, ids[index]!]
  mutating.value = true
  error.value = null
  try {
    const repository = props.session.localNoteRepository()
    await repository.stages.reorder(repository.scope, projectId.value, ids, Object.fromEntries(stages.value.map(stage => [stage.id, stage.revision])))
    await loadWorkspace()
  } catch (reason) { error.value = safeError(reason) }
  finally { mutating.value = false }
}

async function createNote(): Promise<void> {
  if (mutating.value || projectMissing.value) return
  mutating.value = true
  error.value = null
  try {
    const repository = props.session.localNoteRepository()
    const snapshot = await repository.source.readSnapshot(repository.scope, projectId.value)
    const now = timestamp()
    const note: NativeLegacyNote = {
      id: crypto.randomUUID(), project_id: projectId.value, stage_id: null,
      source_type: 'project', source_map_id: null, source_node_id: null,
      content_format: 'html', title: '', content: '', checklist: [], color: 'default',
      pinned: false, archived: false, sort_order: notes.value.length, tags: [],
      created_at: now, updated_at: now, metadata: {}, revision: 0,
    }
    await repository.source.createNote(repository.scope, snapshot.token, note)
    await loadWorkspace()
    editingNote.value = notes.value.find(item => item.id === note.id) ?? null
  } catch (reason) {
    error.value = safeError(reason)
  } finally {
    mutating.value = false
  }
}

function enqueueWrite(noteId: string, patch: ProjectNotePatch): Promise<void> {
  const work = writeQueue.then(async () => {
    const repository = props.session.localNoteRepository()
    const snapshot = await repository.source.readSnapshot(repository.scope, projectId.value)
    await repository.source.updateNote(repository.scope, snapshot.token, noteId, patch, timestamp())
    await loadWorkspace()
    const updated = notes.value.find(note => note.id === noteId)
    if (updated && editingNote.value?.id === noteId) editingNote.value = updated
  })
  writeQueue = work.catch(() => undefined)
  return work
}

async function saveNote(noteId: string, patch: ProjectNotePatch, closeAfter = false): Promise<void> {
  if (mutating.value) return
  mutating.value = true
  error.value = null
  autosaveStatus.value = 'saving'
  try {
    await enqueueWrite(noteId, patch)
    autosaveStatus.value = 'saved'
    if (closeAfter) editingNote.value = null
  } catch (reason) {
    error.value = safeError(reason)
    autosaveStatus.value = 'error'
  } finally {
    mutating.value = false
  }
}

function updateNote(note: ProjectNote, patch: ProjectNotePatch): Promise<void> {
  return saveNote(note.id, patch)
}

function updateColor(note: ProjectNote, color: string): Promise<void> {
  return updateNote(note, { color })
}

function onSubmit(noteId: string, patch: ProjectNotePatch): Promise<void> {
  return saveNote(noteId, patch, true)
}

function onAutosave(noteId: string, patch: ProjectNotePatch): Promise<void> {
  return saveNote(noteId, patch)
}

async function deleteNote(note: ProjectNote): Promise<void> {
  if (mutating.value || !window.confirm(t('Удалить заметку «{name}»? Это действие нельзя отменить.', { name: note.display_title || note.title || t('Без названия') }))) return
  mutating.value = true
  error.value = null
  try {
    const repository = props.session.localNoteRepository()
    const snapshot = await repository.source.readSnapshot(repository.scope, projectId.value)
    await repository.source.tombstoneNote(repository.scope, snapshot.token, note.id, timestamp())
    await loadWorkspace()
  } catch (reason) {
    error.value = safeError(reason)
  } finally {
    mutating.value = false
  }
}

function closeEditor(): void {
  if (!mutating.value) editingNote.value = null
}

onMounted(() => { void loadWorkspace() })
onBeforeUnmount(() => {
  active = false
  notes.value = []
  stages.value = []
  projects.value = []
  editingNote.value = null
})
</script>

<template>
  <section class="encrypted-workspace" aria-labelledby="encrypted-workspace-title" data-testid="encrypted-local-workspace">
    <header class="encrypted-workspace__header">
      <div>
        <p>{{ t('Отдельный режим разработчика') }} · {{ t('Только локально') }}</p>
        <h3 id="encrypted-workspace-title">{{ t('Зашифрованное рабочее пространство') }}</h3>
        <span>{{ t('Не синхронизируется. Данные не переносятся из старого Web-хранилища.') }}</span>
      </div>
      <button class="nf-button nf-button--secondary" type="button" :disabled="mutating" @click="emit('close')">
        {{ t('Закрыть рабочее пространство') }}
      </button>
    </header>

    <p v-if="visibleError" role="alert" class="encrypted-workspace__error">{{ visibleError }}</p>
    <button v-if="visibleError && !loading" class="nf-button nf-button--secondary" type="button" :disabled="mutating" @click="loadWorkspace">{{ t('Повторить') }}</button>
    <p v-if="loading" role="status">{{ t('Открываем зашифрованные заметки…') }}</p>

    <form v-else-if="projectMissing" class="encrypted-workspace__create" @submit.prevent="createProject">
      <p>{{ t('Создайте отдельный локальный проект. Существующие проекты и заметки не импортируются.') }}</p>
      <label>
        <span>{{ t('Название локального проекта') }}</span>
        <input v-model="projectName" maxlength="200" required />
      </label>
      <button class="nf-button" type="submit" :disabled="mutating || !projectName.trim()">
        {{ mutating ? t('Сохраняем…') : t('Создать зашифрованный проект') }}
      </button>
    </form>

    <div v-else-if="!error" class="encrypted-workspace__body">
      <h4>{{ projectName }}</h4>
      <nav class="encrypted-workspace__projects" :aria-label="t('Проекты')">
        <button v-for="item in projects" :key="item.id" class="nf-button" :class="item.id === projectId ? '' : 'nf-button--secondary'" type="button" :disabled="mutating" @click="selectProject(item.id)">{{ item.name }}</button>
      </nav>
      <form class="encrypted-workspace__create" data-testid="encrypted-new-project" @submit.prevent="createProject">
        <label><span>{{ t('Название локального проекта') }}</span><input v-model="newProjectName" maxlength="200" required /></label>
        <button class="nf-button" type="submit" :disabled="mutating || !newProjectName.trim()">{{ t('Создать проект') }}</button>
      </form>
      <form class="encrypted-workspace__create" data-testid="encrypted-rename-project" @submit.prevent="renameProject">
        <label><span>{{ t('Название локального проекта') }}</span><input v-model="projectName" maxlength="200" required /></label>
        <button class="nf-button nf-button--secondary" type="submit" :disabled="mutating || !projectName.trim()">{{ t('Сохранить') }}</button>
      </form>
      <section class="encrypted-workspace__stages" aria-labelledby="encrypted-stages-title">
        <h4 id="encrypted-stages-title">{{ t('Этапы') }}</h4>
        <form class="encrypted-workspace__create" data-testid="encrypted-new-stage" @submit.prevent="createStage">
          <label><span>{{ t('Название') }}</span><input v-model="newStageName" maxlength="200" required /></label>
          <button class="nf-button" type="submit" :disabled="mutating || !newStageName.trim()">{{ t('Добавить этап') }}</button>
        </form>
        <ol class="encrypted-workspace__stage-list" data-testid="encrypted-stage-list">
          <li v-for="(stage, index) in stages" :key="stage.id">
            <template v-if="editingStageId === stage.id">
              <form class="encrypted-workspace__create" @submit.prevent="renameStage">
                <label><span>{{ t('Название') }}</span><input v-model="editingStageName" maxlength="200" required /></label>
                <button class="nf-button" type="submit" :disabled="mutating || !editingStageName.trim()">{{ t('Сохранить') }}</button>
                <button class="nf-button nf-button--secondary" type="button" @click="editingStageId = null">{{ t('Отмена') }}</button>
              </form>
            </template>
            <template v-else>
              <strong>{{ stage.name }}</strong>
              <button class="nf-button nf-button--secondary" type="button" :disabled="mutating" @click="editingStageId = stage.id; editingStageName = stage.name">{{ t('Переименовать') }}</button>
              <button class="nf-button nf-button--secondary" type="button" :disabled="mutating || index === 0" :aria-label="`${t('Выше')}: ${stage.name}`" @click="moveStage(index, -1)">↑</button>
              <button class="nf-button nf-button--secondary" type="button" :disabled="mutating || index === stages.length - 1" :aria-label="`${t('Ниже')}: ${stage.name}`" @click="moveStage(index, 1)">↓</button>
              <button class="nf-button nf-button--secondary" type="button" :disabled="mutating" @click="removeStage(stage)">{{ t('Удалить') }}</button>
            </template>
          </li>
        </ol>
        <p>{{ unavailableCopy[locale.language] }}</p>
      </section>
      <h4>{{ t('Заметки') }} · {{ projectName }}</h4>
      <button class="nf-button encrypted-workspace__new-note" type="button" :disabled="mutating" @click="createNote">
        <IonIcon :icon="addOutline" aria-hidden="true" /> {{ t('Новая заметка') }}
      </button>
      <div v-if="notes.length" class="encrypted-workspace__notes">
        <NoteCard
          v-for="note in notes"
          :key="note.id"
          :note="note"
          :disabled="mutating"
          @edit="editingNote = $event; autosaveStatus = 'idle'"
          @toggle-pin="updateNote($event, { pinned: !$event.pinned })"
          @toggle-archive="updateNote($event, { archived: !$event.archived })"
          @set-color="updateColor"
          @delete="deleteNote"
        />
      </div>
      <p v-else class="encrypted-workspace__empty">
        <IonIcon :icon="documentTextOutline" aria-hidden="true" /> {{ t('Создайте первую локальную заметку.') }}
      </p>
    </div>

    <NoteEditorDialog
      :open="editingNote !== null"
      :note="editingNote"
      :submitting="mutating"
      :api-error="error"
      :autosave="true"
      :autosave-status="autosaveStatus"
      @submit="onSubmit"
      @autosave="onAutosave"
      @autosave-status="autosaveStatus = $event"
      @close="closeEditor"
      @dismissed="closeEditor"
    />
  </section>
</template>

<style scoped>
.encrypted-workspace { display: grid; gap: 1rem; padding-top: 1rem; border-top: 1px solid var(--nf-color-border); }
.encrypted-workspace__header { display: flex; flex-wrap: wrap; gap: 1rem; align-items: center; justify-content: space-between; }
.encrypted-workspace__header p { margin: 0; color: var(--nf-color-primary); font-size: .75rem; font-weight: 800; text-transform: uppercase; }
.encrypted-workspace__header h3, .encrypted-workspace__body h4 { margin: .25rem 0; }
.encrypted-workspace__header span, .encrypted-workspace__create p { color: var(--nf-color-text-muted); }
.encrypted-workspace__create { display: flex; flex-wrap: wrap; gap: .75rem; align-items: end; }
.encrypted-workspace__create p { flex-basis: 100%; margin: 0; }
.encrypted-workspace__create label { display: grid; flex: 1; gap: .3rem; min-width: 15rem; }
.encrypted-workspace__create input { min-height: 2.75rem; padding: .5rem .7rem; border: 1px solid var(--nf-color-border); border-radius: var(--nf-radius-sm); background: var(--nf-color-surface); color: var(--nf-color-text); }
.encrypted-workspace__body { display: grid; gap: .75rem; }
.encrypted-workspace__projects { display: flex; flex-wrap: wrap; gap: .5rem; }
.encrypted-workspace__stages { display: grid; gap: .75rem; }
.encrypted-workspace__stages h4, .encrypted-workspace__stages p { margin: 0; }
.encrypted-workspace__stage-list { display: grid; gap: .5rem; padding-left: 1.5rem; }
.encrypted-workspace__stage-list li { display: flex; flex-wrap: wrap; align-items: center; gap: .5rem; }
.encrypted-workspace__new-note { justify-self: start; }
.encrypted-workspace__notes { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 20rem), 1fr)); gap: 1rem; }
.encrypted-workspace__empty { display: flex; gap: .5rem; align-items: center; margin: 0; color: var(--nf-color-text-muted); }
.encrypted-workspace__error { padding: .75rem; border-radius: var(--nf-radius-sm); background: color-mix(in srgb, var(--nf-color-danger) 12%, transparent); color: var(--nf-color-danger); }
</style>
