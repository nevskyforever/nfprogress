<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  IonContent,
  IonIcon,
  IonPage,
  IonSpinner,
  onIonViewWillEnter,
  onIonViewWillLeave,
} from '@ionic/vue'
import {
  addOutline,
  alertCircleOutline,
  closeCircleOutline,
  folderOpenOutline,
  refreshOutline,
  searchOutline,
} from 'ionicons/icons'

import ProjectCard from '@/components/projects/ProjectCard.vue'
import ProjectCreateDialog from '@/components/projects/ProjectCreateDialog.vue'
import FolderDialog from '@/components/projects/FolderDialog.vue'
import StreakBadge from '@/components/projects/StreakBadge.vue'
import StatePanel from '@/components/ui/StatePanel.vue'
import ContextActionMenu, { type ContextAction } from '@/components/ui/ContextActionMenu.vue'
import { projectsApi } from '@/api/projects'
import { apiErrorMessage } from '@/api/client'
import { integrationsApi } from '@/api/integrations'
import { settingsApi } from '@/api/settings'
import { useLocaleStore } from '@/stores/locale'
import { useNotificationsStore } from '@/stores/notifications'
import { useProjectsStore } from '@/stores/projects'
import { onDataChange } from '@/services/dataChanges'
import { gameResponseMessages } from '@/utils/gameNotifications'
import { progressChangeNotification } from '@/utils/progressNotifications'
import { todayIsoDate, writingDayIsoDate } from '@/utils/projectPlanning'
import type {
  GlobalStreakSummary,
  Project,
  ProjectCreate,
  ProjectFolder,
  ProjectSort,
  ProjectStatus,
  TodaySummary,
} from '@/types/api'
import type { SyncBatchItem } from '@/types/integrations'

type StatusFilter = 'all' | ProjectStatus

const route = useRoute()
const router = useRouter()
const store = useProjectsStore()
const locale = useLocaleStore()
const notifications = useNotificationsStore()
const t = locale.translate

function queryValue(value: unknown): string {
  return typeof value === 'string' ? value : ''
}

function routeStatus(): StatusFilter | null {
  const value = queryValue(route.query.status)
  return value === 'all' || value === 'активен' || value === 'в архиве' || value === 'завершен'
    ? value
    : null
}

function routeSort(): ProjectSort | null {
  const value = queryValue(route.query.sort)
  return value === 'manual' || value === 'name' || value === 'deadline' || value === 'progress' || value === 'updated'
    ? value
    : null
}

function initialStatus(): StatusFilter {
  return routeStatus() ?? 'all'
}

function initialSort(): ProjectSort {
  return routeSort() ?? 'manual'
}

const search = ref(queryValue(route.query.search))
const debouncedSearch = ref(search.value)
const status = ref<StatusFilter>(initialStatus())
const sort = ref<ProjectSort>(initialSort())
const folders = ref<ProjectFolder[]>([])
const draggedProjectId = ref<string | null>(null)
const contextProject = ref<Project | null>(null)
const contextPosition = ref({ x: 0, y: 0 })
const createDialogOpen = ref(false)
const folderDialogOpen = ref(false)
const folderBeingEdited = ref<ProjectFolder | null>(null)
const todaySummary = ref<TodaySummary | null>(null)
const showTodaySummary = ref(false)
const streaksEnabled = ref(false)
const globalStreak = ref<GlobalStreakSummary | null>(null)
const localSyncAvailable = ref(false)
const syncAllRunning = ref(false)
const preferencesReady = ref(false)
const createPlanningDate = ref(todayIsoDate())
const cardVersions = ref<Record<string, number>>({})
const previousCardSignatures = new Map<string, string>()
const pendingCardAnimations = new Set<string>()
const projectDragMimeType = 'application/x-nfprogress-project-id'
const projectOrderEditing = ref(false)
const projectOrderSaving = ref(false)
const draftProjectOrder = ref<string[]>([])
const draftProjectFolders = ref<Record<string, string | null>>({})
const pointerProjectDrag = ref<{
  projectId: string
  pointerId: number
  startX: number
  startY: number
  active: boolean
} | null>(null)
let projectViewActive = false
let debounceTimer: ReturnType<typeof setTimeout> | undefined
let preferencesController: AbortController | undefined
let preferenceSaveChain: Promise<void> = Promise.resolve()
let stopDataChanges: (() => void) | undefined

const hasFilters = computed(
  () => search.value.trim().length > 0 || status.value !== 'all',
)
const canReorderProjects = computed(() => sort.value === 'manual' && projectOrderEditing.value)
const canMoveProjectsToFolders = computed(() => folders.value.length > 0 && !projectOrderSaving.value)
const canDragProjects = computed(() => canReorderProjects.value || canMoveProjectsToFolders.value)
const projectGroups = computed(() => {
  const orderIndex = new Map(draftProjectOrder.value.map((id, index) => [id, index]))
  const orderedProjects = [...store.projects].sort((left, right) =>
    (orderIndex.get(left.id) ?? Number.MAX_SAFE_INTEGER)
    - (orderIndex.get(right.id) ?? Number.MAX_SAFE_INTEGER),
  )
  const folderId = (project: Project): string | null => (
    projectOrderEditing.value && Object.hasOwn(draftProjectFolders.value, project.id)
      ? draftProjectFolders.value[project.id] ?? null
      : project.folder_id
  )
  const groups = [
    { id: null as string | null, name: t('Без папки'), projects: orderedProjects.filter((project) => !folderId(project)) },
    ...folders.value.map((folder) => ({
      id: folder.id as string | null,
      name: folder.name,
      projects: orderedProjects.filter((project) => folderId(project) === folder.id),
    })),
  ]
  return groups.filter((group) => group.projects.length || group.id !== null)
})

function beginProjectOrderEditing(): void {
  draftProjectOrder.value = projectGroups.value.flatMap((group) => group.projects.map((project) => project.id))
  draftProjectFolders.value = Object.fromEntries(
    store.projects.map((project) => [project.id, project.folder_id]),
  )
  projectOrderEditing.value = true
}

async function saveProjectOrder(): Promise<void> {
  if (!projectOrderEditing.value || projectOrderSaving.value) return
  projectOrderSaving.value = true
  try {
    const folderUpdates = store.projects
      .filter((project) => draftProjectFolders.value[project.id] !== project.folder_id)
      .map((project) => projectsApi.update(project.id, {
        folder_id: draftProjectFolders.value[project.id] ?? null,
      }))
    await Promise.all(folderUpdates)
    const saved = await store.reorderProjects([...draftProjectOrder.value])
    if (!saved) return
    projectOrderEditing.value = false
    draftProjectOrder.value = []
    draftProjectFolders.value = {}
    loadProjects()
  } catch (error) {
    notifications.error(t(apiErrorMessage(error)))
  } finally {
    projectOrderSaving.value = false
  }
}

const resultSummary = computed(() => {
  if (store.loading || store.error) return ''
  return t('Найдено проектов: {count}', { count: store.projectCount })
})

function currentListQuery() {
  return {
    search: debouncedSearch.value,
    sort: sort.value,
    status: status.value === 'all' ? undefined : status.value,
  }
}

function loadProjects(): void {
  void store.load(currentListQuery())
}

function projectAnimationSignature(project: Project): string {
  return JSON.stringify({
    total: project.total,
    goal: project.goal,
    progress: project.progress,
    deadline: project.deadline,
    status: project.status,
    todayGoal: project.today_goal,
    personalGoal: project.personal_goal,
    streak: [project.streak_status, project.streak_length, project.max_streak],
    stages: project.stages.map((stage) => [
      stage.id, stage.total, stage.goal, stage.progress, stage.deadline,
      stage.status, stage.today_goal, stage.streak_status, stage.streak_length,
    ]),
  })
}

function restartCardAnimation(projectId: string): void {
  cardVersions.value = {
    ...cardVersions.value,
    [projectId]: (cardVersions.value[projectId] ?? 0) + 1,
  }
}

function preferenceStatus(value: unknown): StatusFilter | null {
  if (value === 'all' || value === 'активен' || value === 'в архиве' || value === 'завершен') {
    return value
  }
  const legacy: Record<string, ProjectStatus> = {
    Активен: 'активен',
    'В архиве': 'в архиве',
    Завершен: 'завершен',
  }
  return typeof value === 'string' ? legacy[value] ?? null : null
}

function preferenceSort(value: unknown): ProjectSort | null {
  if (value === 'manual' || value === 'name' || value === 'deadline' || value === 'progress' || value === 'updated') {
    return value
  }
  const legacy: Record<string, ProjectSort> = {
    Название: 'name',
    Дедлайн: 'deadline',
    Прогресс: 'progress',
  }
  return typeof value === 'string' ? legacy[value] ?? null : null
}

function enabledSetting(value: unknown): boolean {
  // Existing settings files are normally boolean, but early legacy saves can
  // contain serialized truthy equivalents.
  return value === true || value === 1 || value === 'true' || value === 'True'
}

function synchronizeRoute(): void {
  const query: Record<string, string> = {}
  if (debouncedSearch.value.trim()) query.search = debouncedSearch.value.trim()
  if (status.value !== 'all') query.status = status.value
  if (sort.value !== 'manual') query.sort = sort.value
  void router.replace({ query })
}

function persistListPreferences(): void {
  const values = {
    frontend_project_filter: status.value,
    frontend_project_sort: sort.value,
  }
  preferenceSaveChain = preferenceSaveChain
    .then(() => settingsApi.update(values))
    .then(() => undefined)
    .catch(() => {
      // List filtering remains usable when a noncritical view preference cannot save.
    })
}

async function initializeWorkspace(): Promise<void> {
  preferencesController?.abort()
  const controller = new AbortController()
  preferencesController = controller
  try {
    const settings = await settingsApi.get(controller.signal)
    try {
      folders.value = await projectsApi.folders(controller.signal)
    } catch {
      folders.value = []
    }
    if (routeStatus() === null) {
      status.value = preferenceStatus(
        settings.values.frontend_project_filter ?? settings.values.project_filter,
      ) ?? status.value
    }
    if (routeSort() === null) {
      sort.value = preferenceSort(
        settings.values.frontend_project_sort ?? settings.values.project_sort,
      ) ?? sort.value
    }
    showTodaySummary.value = enabledSetting(settings.values.show_written_today_in_all_projects)
    streaksEnabled.value = enabledSetting(settings.values.global_streak)
    localSyncAvailable.value = settings.capabilities.local_file_sync === true
    createPlanningDate.value = writingDayIsoDate(settings.values.start_day_time)
    const summaryRequests: Promise<void>[] = []
    if (showTodaySummary.value) {
      summaryRequests.push(
        projectsApi.today(controller.signal)
          .then((summary) => { todaySummary.value = summary })
          .catch(() => { todaySummary.value = null }),
      )
    }
    if (streaksEnabled.value) {
      summaryRequests.push(
        projectsApi.globalStreak(controller.signal)
          .then((summary) => { globalStreak.value = summary })
          .catch(() => { globalStreak.value = null }),
      )
    }
    await Promise.all(summaryRequests)
  } catch (caught) {
    if (caught instanceof DOMException && caught.name === 'AbortError') return
    todaySummary.value = null
    globalStreak.value = null
  } finally {
    if (controller.signal.aborted || preferencesController !== controller) return
    preferencesReady.value = true
    synchronizeRoute()
    loadProjects()
  }
}

async function synchronizeAll(): Promise<void> {
  if (!localSyncAvailable.value || syncAllRunning.value) return
  syncAllRunning.value = true
  try {
    const result = await integrationsApi.runAllSync()
    await Promise.all([
      store.load(currentListQuery()),
      showTodaySummary.value
        ? projectsApi.today().then((summary) => { todaySummary.value = summary }).catch(() => undefined)
        : Promise.resolve(),
      streaksEnabled.value
        ? projectsApi.globalStreak().then((summary) => { globalStreak.value = summary }).catch(() => undefined)
      : Promise.resolve(),
    ])
    const notify = result.failed > 0 ? notifications.warning : notifications.success
    notify(t('Синхронизация завершена'))
    for (const item of result.items) applySyncFeedback(item)
  } catch (error) {
    notifications.error(t(apiErrorMessage(error)))
  } finally {
    syncAllRunning.value = false
  }
}

function applySyncFeedback(item: SyncBatchItem): void {
  const progress = item.progress
  if (progress) {
    const entity = item.stage_id
      ? progress.project.stages.find((stage) => stage.id === item.stage_id)
        ?? store.projects.find((project) => project.id === item.project_id)?.stages
          .find((stage) => stage.id === item.stage_id)
        ?? progress.project
      : progress.project
    const feedback = progressChangeNotification(
      progress,
      entity,
      t,
      locale.formatNumber,
      locale.formatUnit,
    )
    if (feedback) notifications.show(feedback.message, feedback.kind)

    const game = progress.game
    if (game) {
      notifications.setGameHistory(game.state.notifications)
      for (const message of gameResponseMessages(game)) notifications.success(t(message))
    }
  }
  if (!item.ok && item.error?.message) {
    notifications.warning(t(item.error.message))
  } else if (item.ok && !item.changed) {
    notifications.show(t('Документ не изменился. Текущий объём уже актуален.'), 'info')
  }
}

function clearFilters(): void {
  search.value = ''
  debouncedSearch.value = ''
  status.value = 'all'
}

function openCreateDialog(): void {
  store.clearCreateError()
  createDialogOpen.value = true
}

function closeCreateDialog(): void {
  createDialogOpen.value = false
  store.clearCreateError()
}

async function createProject(payload: ProjectCreate): Promise<void> {
  const project = await store.create(payload)
  if (!project) return
  createDialogOpen.value = false
  await router.push({ name: 'project-detail', params: { projectId: project.id } })
}

function openProjectContext(event: MouseEvent, project: Project): void {
  contextProject.value = project
  contextPosition.value = { x: event.clientX, y: event.clientY }
}

const contextActions = computed<ContextAction[]>(() => {
  const project = contextProject.value
  if (!project) return []
  const shared = project.name === 'Общий проект'
  const actions: ContextAction[] = []
  if (project.status !== 'завершен' && !shared) actions.push({ id: 'edit', label: t('Изменить') })
  if (project.status !== 'завершен' && !shared) {
    actions.push({ id: 'archive', label: project.status === 'в архиве' ? t('Вернуть в активные') : t('В архив') })
  }
  if (
    project.status !== 'завершен' && !shared && !project.infinite
    && project.goal !== null && project.total >= project.goal
  ) actions.push({ id: 'complete', label: t('Завершить') })
  if (localSyncAvailable.value && project.sync_available && project.status !== 'завершен') {
    actions.push({ id: 'sync', label: t('Синхронизировать') })
  }
  for (const folder of folders.value) {
    if (folder.id !== project.folder_id) {
      actions.push({ id: `folder:${folder.id}`, label: t('В папку «{name}»', { name: folder.name }), separator: actions.every((item) => !item.id.startsWith('folder:')) })
    }
  }
  if (project.folder_id) actions.push({ id: 'folder:', label: t('Убрать из папки') })
  if (!shared) actions.push({ id: 'delete', label: t('Удалить'), danger: true, separator: true })
  return actions
})

async function handleContextAction(action: ContextAction): Promise<void> {
  const project = contextProject.value
  contextProject.value = null
  if (!project) return
  try {
    if (action.id === 'edit') {
      await router.push({ name: 'project-detail', params: { projectId: project.id }, query: { edit: '1' } })
      return
    }
    if (action.id === 'archive') await projectsApi.setArchived(project.id, project.status !== 'в архиве')
    if (action.id === 'complete') {
      if (!window.confirm(t('Завершить проект «{name}»? После этого он будет доступен только для просмотра.', { name: project.name }))) return
      await projectsApi.complete(project.id)
    }
    if (action.id === 'delete') {
      if (!window.confirm(t('Удалить проект «{name}» и все связанные данные? Это действие нельзя отменить.', { name: project.name }))) return
      await projectsApi.remove(project.id)
    }
    if (action.id === 'sync') {
      const result = await integrationsApi.runProjectSyncs(project.id)
      const notify = result.failed > 0 ? notifications.warning : notifications.success
      notify(t('Синхронизация завершена'))
      for (const item of result.items) applySyncFeedback(item)
    }
    if (action.id.startsWith('folder:')) {
      await projectsApi.update(project.id, { folder_id: action.id.slice('folder:'.length) || null })
    }
    loadProjects()
  } catch (error) {
    notifications.error(t(apiErrorMessage(error)))
  }
}

function openCreateFolderDialog(): void {
  folderBeingEdited.value = null
  folderDialogOpen.value = true
}

function openRenameFolderDialog(folder: ProjectFolder): void {
  folderBeingEdited.value = folder
  folderDialogOpen.value = true
}

function closeFolderDialog(): void {
  folderDialogOpen.value = false
  folderBeingEdited.value = null
}

async function saveFolder(name: string): Promise<void> {
  try {
    const folder = folderBeingEdited.value
    if (folder) {
      const updated = await projectsApi.updateFolder(folder.id, name)
      folders.value = folders.value.map((item) => item.id === folder.id ? updated : item)
    } else {
      folders.value = [...folders.value, await projectsApi.createFolder(name)]
    }
    closeFolderDialog()
  } catch (error) { notifications.error(t(apiErrorMessage(error))) }
}

async function deleteFolder(folder: ProjectFolder): Promise<void> {
  if (!window.confirm(t('Удалить папку «{name}»? Проекты останутся без папки.', { name: folder.name }))) return
  try {
    await projectsApi.removeFolder(folder.id)
    folders.value = folders.value.filter((item) => item.id !== folder.id)
    loadProjects()
  } catch (error) { notifications.error(t(apiErrorMessage(error))) }
}

function startProjectDrag(event: DragEvent, project: Project): void {
  if (!canDragProjects.value) { event.preventDefault(); return }
  draggedProjectId.value = project.id
  if (event.dataTransfer) {
    // A data item is required for native drag-and-drop in Firefox and Safari.
    // It also preserves the source when the drag crosses a Vue component boundary.
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData(projectDragMimeType, project.id)
    event.dataTransfer.setData('text/plain', project.id)
  }
}

function reorderProject(
  sourceId: string,
  targetProject: Project,
  targetFolderId: string | null,
): void {
  draggedProjectId.value = null
  if (!sourceId || sourceId === targetProject.id) return
  const ordered = projectGroups.value.flatMap((group) => group.projects.map((project) => project.id))
  const from = ordered.indexOf(sourceId)
  const to = ordered.indexOf(targetProject.id)
  if (from < 0 || to < 0) return
  ordered.splice(from, 1)
  const targetIndex = ordered.indexOf(targetProject.id)
  ordered.splice(from < to ? targetIndex + 1 : targetIndex, 0, sourceId)
  draftProjectOrder.value = ordered
  draftProjectFolders.value = { ...draftProjectFolders.value, [sourceId]: targetFolderId }
}

async function dropProject(
  event: DragEvent,
  targetProject: Project,
  targetFolderId: string | null,
): Promise<void> {
  const sourceId = event.dataTransfer?.getData(projectDragMimeType)
    || event.dataTransfer?.getData('text/plain')
    || draggedProjectId.value
  if (!sourceId) return
  if (projectOrderEditing.value) {
    reorderProject(sourceId, targetProject, targetFolderId)
    return
  }
  await moveProjectToFolder(sourceId, targetFolderId)
}

async function moveProjectToFolder(sourceId: string, targetFolderId: string | null): Promise<void> {
  const sourceProject = store.projects.find((project) => project.id === sourceId)
  if (!sourceProject) return
  if (!projectOrderEditing.value) {
    if (sourceProject.folder_id === targetFolderId) return
    try {
      await projectsApi.update(sourceId, { folder_id: targetFolderId })
      await store.load(currentListQuery())
    } catch (error) {
      notifications.error(t(apiErrorMessage(error)))
    }
    return
  }
  const ordered = projectGroups.value
    .flatMap((group) => group.projects.map((project) => project.id))
    .filter((projectId) => projectId !== sourceId)
  ordered.push(sourceId)
  draftProjectOrder.value = ordered
  draftProjectFolders.value = { ...draftProjectFolders.value, [sourceId]: targetFolderId }
  draggedProjectId.value = null
}

async function dropProjectIntoFolder(event: DragEvent, targetFolderId: string | null): Promise<void> {
  const sourceId = event.dataTransfer?.getData(projectDragMimeType)
    || event.dataTransfer?.getData('text/plain')
    || draggedProjectId.value
  if (sourceId) await moveProjectToFolder(sourceId, targetFolderId)
}

function clearProjectPointerDrag(): void {
  pointerProjectDrag.value = null
  window.removeEventListener('pointermove', moveProjectPointer)
  window.removeEventListener('pointerup', finishProjectPointer)
  window.removeEventListener('pointercancel', finishProjectPointer)
}

function moveProjectPointer(event: PointerEvent): void {
  const drag = pointerProjectDrag.value
  if (!drag || event.pointerId !== drag.pointerId) return
  if (!drag.active && Math.hypot(event.clientX - drag.startX, event.clientY - drag.startY) < 8) return
  drag.active = true
  event.preventDefault()
}

function finishProjectPointer(event: PointerEvent): void {
  const drag = pointerProjectDrag.value
  if (!drag || event.pointerId !== drag.pointerId) return
  clearProjectPointerDrag()
  if (!drag.active) return
  const targetId = document.elementFromPoint(event.clientX, event.clientY)
    ?.closest<HTMLElement>('[data-project-id]')?.dataset.projectId
  const targetProject = store.projects.find((project) => project.id === targetId)
  window.addEventListener('click', (clickEvent) => {
    clickEvent.preventDefault()
    clickEvent.stopImmediatePropagation()
  }, { capture: true, once: true })
  if (targetProject) {
    const targetFolderId = Object.hasOwn(draftProjectFolders.value, targetProject.id)
      ? draftProjectFolders.value[targetProject.id] ?? null
      : targetProject.folder_id
    if (projectOrderEditing.value) reorderProject(drag.projectId, targetProject, targetFolderId)
    else void moveProjectToFolder(drag.projectId, targetFolderId)
    return
  }
  const folderElement = document.elementFromPoint(event.clientX, event.clientY)
    ?.closest<HTMLElement>('[data-folder-id]')
  if (!folderElement) return
  void moveProjectToFolder(drag.projectId, folderElement.dataset.folderId || null)
}

function startProjectPointer(event: PointerEvent, project: Project): void {
  if (!canDragProjects.value || event.button !== 0) return
  pointerProjectDrag.value = {
    projectId: project.id,
    pointerId: event.pointerId,
    startX: event.clientX,
    startY: event.clientY,
    active: false,
  }
  window.addEventListener('pointermove', moveProjectPointer, { passive: false })
  window.addEventListener('pointerup', finishProjectPointer)
  window.addEventListener('pointercancel', finishProjectPointer)
}

watch(search, (value) => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    debouncedSearch.value = value
  }, 250)
})

watch(
  [debouncedSearch, status, sort],
  () => {
    if (!preferencesReady.value) return
    synchronizeRoute()
    persistListPreferences()
    loadProjects()
  },
)

watch(
  () => store.projects.map((project) => [project.id, projectAnimationSignature(project)] as const),
  (entries) => {
    const currentIds = new Set(entries.map(([id]) => id))
    for (const [id, signature] of entries) {
      const previous = previousCardSignatures.get(id)
      previousCardSignatures.set(id, signature)
      if (previous === undefined || previous === signature) continue
      if (projectViewActive) restartCardAnimation(id)
      else pendingCardAnimations.add(id)
    }
    for (const id of previousCardSignatures.keys()) {
      if (!currentIds.has(id)) previousCardSignatures.delete(id)
    }
  },
  { deep: true },
)

onMounted(() => {
  void initializeWorkspace()
  window.addEventListener('nfprogress:new-project', openCreateDialog)
  stopDataChanges = onDataChange((scope) => {
    if (scope === 'projects') {
      loadProjects()
      return
    }
    void initializeWorkspace()
  })
})
onIonViewWillEnter(() => {
  projectViewActive = true
  for (const id of pendingCardAnimations) restartCardAnimation(id)
  pendingCardAnimations.clear()
})
onIonViewWillLeave(() => { projectViewActive = false })
onBeforeUnmount(() => {
  clearTimeout(debounceTimer)
  preferencesController?.abort()
  store.cancelList()
  clearProjectPointerDrag()
  stopDataChanges?.()
  window.removeEventListener('nfprogress:new-project', openCreateDialog)
})
</script>

<template>
  <IonPage>
    <IonContent :fullscreen="true" class="projects-content">
      <div class="projects-workspace">
        <header class="page-header">
          <div>
            <p class="page-eyebrow">{{ t('Рабочее пространство') }}</p>
            <h1>{{ t('Проекты') }}</h1>
            <p class="page-introduction">
              {{ t('Следите за рукописями, целями и ритмом работы в одном месте.') }}
            </p>
          </div>
          <div class="page-header__actions">
            <button
              v-if="localSyncAvailable"
              class="nf-button nf-button--secondary sync-all-button"
              type="button"
              :disabled="syncAllRunning"
              :aria-busy="syncAllRunning"
              @click="synchronizeAll"
            >
              <IonSpinner v-if="syncAllRunning" name="crescent" aria-hidden="true" />
              <IonIcon v-else :icon="refreshOutline" aria-hidden="true" />
              {{ t('Синхронизировать все') }}
            </button>
            <button class="nf-button create-project-button" type="button" @click="openCreateDialog">
              <IonIcon :icon="addOutline" aria-hidden="true" />
              {{ t('Новый проект') }}
            </button>
            <button class="nf-button nf-button--secondary" type="button" @click="openCreateFolderDialog">
              {{ t('Новая папка') }}
            </button>
          </div>
        </header>

        <div
          v-if="(showTodaySummary && todaySummary) || (streaksEnabled && globalStreak?.enabled)"
          class="workspace-summaries"
        >
          <section v-if="showTodaySummary && todaySummary" class="workspace-summary workspace-summary--today" role="status">
            <div>
              <p>{{ t('Текущий писательский день') }}</p>
              <h2>{{ t('Написано сегодня') }}</h2>
            </div>
            <strong>{{ locale.formatNumber(todaySummary.symbols, 0) }} {{ locale.formatUnit('symbols', todaySummary.symbols) }}</strong>
          </section>

          <section v-if="streaksEnabled && globalStreak?.enabled" class="workspace-summary workspace-summary--streak">
            <div>
              <p>{{ t('Ритм всех проектов') }}</p>
              <h2>{{ t('Глобальный стрик') }}</h2>
            </div>
            <StreakBadge
              :length="globalStreak.length"
              :max-length="globalStreak.max_length"
              :status="globalStreak.status"
              scope="global"
              show-max
            />
          </section>
        </div>

        <section class="project-toolbar" :aria-label="t('Поиск и фильтры проектов')">
          <label class="search-field" for="project-search">
            <span class="visually-hidden">{{ t('Поиск проектов') }}</span>
            <IonIcon :icon="searchOutline" aria-hidden="true" />
            <input
              id="project-search"
              v-model="search"
              type="search"
              :disabled="projectOrderEditing"
              :placeholder="t('Поиск по проектам и этапам')"
              autocomplete="off"
            />
            <button
              v-if="search"
              class="clear-search"
              type="button"
              :aria-label="t('Очистить поиск')"
              @click="search = ''"
            >
              <IonIcon :icon="closeCircleOutline" aria-hidden="true" />
            </button>
          </label>

          <label class="toolbar-select" for="project-status-filter">
            <span>{{ t('Статус') }}</span>
            <select id="project-status-filter" v-model="status" :disabled="projectOrderEditing">
              <option value="all">{{ t('Все проекты') }}</option>
              <option value="активен">{{ t('Активные') }}</option>
              <option value="в архиве">{{ t('В архиве') }}</option>
              <option value="завершен">{{ t('Завершённые') }}</option>
            </select>
          </label>

          <label class="toolbar-select" for="project-sort">
            <span>{{ t('Сортировка') }}</span>
            <select id="project-sort" v-model="sort" :disabled="projectOrderEditing">
              <option value="manual">{{ t('Свободный порядок') }}</option>
              <option value="progress">{{ t('По прогрессу') }}</option>
              <option value="updated">{{ t('Недавно изменённые') }}</option>
              <option value="deadline">{{ t('По сроку') }}</option>
              <option value="name">{{ t('По названию') }}</option>
            </select>
          </label>
          <button
            v-if="sort === 'manual'"
            class="nf-button nf-button--secondary project-order-toggle"
            type="button"
            :disabled="projectOrderSaving"
            :aria-label="projectOrderEditing ? t('Сохранить') : t('Изменить')"
            @click="projectOrderEditing ? saveProjectOrder() : beginProjectOrderEditing()"
          >
            <span v-if="!projectOrderEditing" aria-hidden="true">✎</span>
            {{ projectOrderEditing ? t('Сохранить') : t('Изменить') }}
          </button>
        </section>

        <p class="results-summary" aria-live="polite">{{ resultSummary }}</p>

        <StatePanel
          v-if="store.loading && store.projects.length === 0"
          :title="t('Загружаем проекты')"
          :message="t('Собираем актуальные данные вашего рабочего пространства.')"
          loading
        />

        <StatePanel
          v-else-if="store.error"
          :title="t('Не удалось загрузить проекты')"
          :message="store.error"
          :icon="alertCircleOutline"
        >
          <button class="nf-button" type="button" @click="loadProjects">
            {{ t('Повторить') }}
          </button>
        </StatePanel>

        <StatePanel
          v-else-if="store.projects.length === 0 && hasFilters"
          :title="t('Ничего не найдено')"
          :message="t('Попробуйте изменить запрос или сбросить фильтры.')"
          :icon="searchOutline"
        >
          <button class="nf-button nf-button--secondary" type="button" @click="clearFilters">
            {{ t('Сбросить фильтры') }}
          </button>
        </StatePanel>

        <StatePanel
          v-else-if="store.projects.length === 0"
          :title="t('Здесь появятся ваши истории')"
          :message="t('Создайте первый проект, задайте цель и начните фиксировать прогресс.')"
          :icon="folderOpenOutline"
        >
          <button class="nf-button" type="button" @click="openCreateDialog">
            <IonIcon :icon="addOutline" aria-hidden="true" />
            {{ t('Создать первый проект') }}
          </button>
        </StatePanel>

        <div v-else class="project-folders" :class="{ 'project-grid--updating': store.loading }">
          <section
            v-for="group in projectGroups"
            :key="group.id ?? 'unfiled'"
            class="project-folder"
            :data-folder-id="group.id ?? ''"
            @dragover="canDragProjects && $event.preventDefault()"
            @drop.prevent="dropProjectIntoFolder($event, group.id)"
          >
            <header v-if="folders.length" class="project-folder__header">
              <h2>{{ group.name }}</h2>
              <div v-if="group.id">
                <button type="button" @click="openRenameFolderDialog(folders.find((folder) => folder.id === group.id)!)">{{ t('Переименовать') }}</button>
                <button type="button" class="project-folder__delete" @click="deleteFolder(folders.find((folder) => folder.id === group.id)!)">{{ t('Удалить папку') }}</button>
              </div>
            </header>
            <TransitionGroup tag="div" class="project-grid" :aria-label="group.name">
              <ProjectCard
                v-for="project in group.projects"
                :key="`${project.id}:${cardVersions[project.id] ?? 0}`"
                :project="project"
                :streaks-enabled="streaksEnabled"
                :draggable="canDragProjects"
                :show-drag-handle="canDragProjects"
                @context="openProjectContext"
                @dragstart="startProjectDrag"
                @dragend="draggedProjectId = null"
                @pointerdown="startProjectPointer"
                @dragover.prevent
                @drop.stop.prevent="dropProject($event, project, group.id)"
              />
            </TransitionGroup>
            <p v-if="!group.projects.length" class="project-folder__empty">{{ t('Перетащите сюда проекты или выберите папку в контекстном меню.') }}</p>
          </section>
        </div>
      </div>
    </IonContent>

    <ProjectCreateDialog
      :open="createDialogOpen"
      :planning-date="createPlanningDate"
      :submitting="store.creating"
      :api-error="store.createError"
      @close="closeCreateDialog"
      @submit="createProject"
    />
    <FolderDialog
      :open="folderDialogOpen"
      :initial-name="folderBeingEdited?.name"
      @close="closeFolderDialog"
      @submit="saveFolder"
    />
    <ContextActionMenu
      :open="contextProject !== null"
      :x="contextPosition.x"
      :y="contextPosition.y"
      :label="contextProject ? t('Действия проекта') : ''"
      :actions="contextActions"
      @close="contextProject = null"
      @select="handleContextAction"
    />
  </IonPage>
</template>

<style scoped>
.projects-content {
  --background: var(--nf-color-canvas);
}

.projects-workspace {
  width: min(100%, 91rem);
  min-height: 100%;
  margin: 0 auto;
  padding: calc(var(--nf-space-7) + env(safe-area-inset-top)) clamp(1rem, 3vw, 3.5rem)
    var(--nf-space-7);
}

.page-header {
  display: flex;
  gap: var(--nf-space-6);
  align-items: flex-end;
  justify-content: space-between;
}

.page-header__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--nf-space-2);
  align-items: center;
  justify-content: flex-end;
}

.sync-all-button {
  min-width: max-content;
}

.sync-all-button ion-icon,
.sync-all-button ion-spinner {
  font-size: 1.1rem;
}

.page-eyebrow {
  margin: 0 0 var(--nf-space-2);
  color: var(--nf-color-accent);
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.page-header h1 {
  margin: 0;
  color: var(--nf-color-text);
  font-family: var(--nf-font-serif);
  font-size: clamp(1.8rem, 3.5vw, 2.75rem);
  font-weight: 650;
  letter-spacing: -0.04em;
  line-height: 0.98;
}

.page-introduction {
  max-width: 38rem;
  margin: var(--nf-space-3) 0 0;
  color: var(--nf-color-text-muted);
  font-size: clamp(0.95rem, 1.5vw, 1.08rem);
  line-height: 1.55;
}

.create-project-button {
  min-width: max-content;
}

.create-project-button ion-icon {
  font-size: 1.15rem;
}

.workspace-summaries {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--nf-space-3);
  margin-top: var(--nf-space-5);
}

.workspace-summary {
  display: flex;
  min-width: 0;
  gap: var(--nf-space-3);
  align-items: center;
  justify-content: space-between;
  padding: var(--nf-space-3) var(--nf-space-4);
  border: 1px solid var(--nf-color-border);
  border-left: 0.25rem solid var(--nf-color-accent);
  border-radius: var(--nf-radius-md);
  background: var(--nf-color-surface);
  box-shadow: var(--nf-shadow-card);
}

.workspace-summary--today {
  border-left-color: var(--nf-color-success);
}

.workspace-summary p,
.workspace-summary h2,
.workspace-summary strong {
  margin: 0;
}

.workspace-summary p {
  color: var(--nf-color-text-muted);
  font-size: 0.72rem;
  font-weight: 700;
}

.workspace-summary h2 {
  margin-top: var(--nf-space-1);
  font-family: var(--nf-font-serif);
  font-size: 1.08rem;
}

.workspace-summary--today strong {
  min-width: max-content;
  color: var(--nf-color-success);
  font-size: clamp(1.05rem, 1.8vw, 1.32rem);
  text-align: right;
}

.workspace-summary--streak :deep(.streak-badge) {
  flex: 0 1 auto;
}

.project-toolbar {
  display: grid;
  grid-template-columns: minmax(14rem, 1fr) auto auto auto;
  gap: var(--nf-space-3);
  align-items: end;
  margin-top: var(--nf-space-7);
  padding: var(--nf-space-3);
  border: 1px solid var(--nf-color-border);
  border-radius: var(--nf-radius-md);
  background: var(--nf-color-surface);
}

.project-order-toggle {
  min-height: 3rem;
  white-space: nowrap;
}

.search-field {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: var(--nf-space-2);
  align-items: center;
  min-height: 3rem;
  padding: 0 var(--nf-space-3);
  border: 1px solid transparent;
  border-radius: var(--nf-radius-sm);
  background: var(--nf-color-surface-muted);
  color: var(--nf-color-text-muted);
}

.search-field:focus-within {
  border-color: var(--nf-color-focus);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--nf-color-focus) 25%, transparent);
}

.search-field input {
  width: 100%;
  min-height: 2.75rem;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--nf-color-text);
}

.search-field input::placeholder {
  color: var(--nf-color-text-muted);
}

.clear-search {
  display: grid;
  width: 2.5rem;
  height: 2.5rem;
  padding: 0;
  place-items: center;
  border: 0;
  border-radius: var(--nf-radius-pill);
  background: transparent;
  color: var(--nf-color-text-muted);
  cursor: pointer;
}

.clear-search ion-icon {
  font-size: 1.25rem;
}

.toolbar-select {
  display: grid;
  gap: var(--nf-space-1);
  min-width: 10rem;
}

.toolbar-select span {
  padding-left: var(--nf-space-2);
  color: var(--nf-color-text-muted);
  font-size: 0.7rem;
  font-weight: 750;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.toolbar-select select {
  min-height: 3rem;
  padding: 0 var(--nf-space-3);
  border: 1px solid var(--nf-color-border);
  border-radius: var(--nf-radius-sm);
  background: var(--nf-color-surface-raised);
  color: var(--nf-color-text);
}

.results-summary {
  min-height: 1.25rem;
  margin: var(--nf-space-4) var(--nf-space-1) var(--nf-space-3);
  color: var(--nf-color-text-muted);
  font-size: 0.8rem;
}

.project-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 19rem), 1fr));
  gap: var(--nf-space-4);
  transition: opacity 120ms ease;
}

.project-folders { display: grid; gap: var(--nf-space-6); }
.project-folder { min-width: 0; }
.project-folder__header { display: flex; gap: var(--nf-space-3); align-items: center; justify-content: space-between; margin: 0 0 var(--nf-space-3); }
.project-folder__header h2 { margin: 0; font-family: var(--nf-font-serif); font-size: 1.35rem; }
.project-folder__header div { display: flex; gap: var(--nf-space-2); }
.project-folder__header button { padding: .35rem .55rem; border: 0; background: transparent; color: var(--nf-color-primary); font: inherit; font-size: .8rem; font-weight: 700; cursor: pointer; }
.project-folder__header .project-folder__delete { color: var(--nf-color-danger); }
.project-folder__empty { margin: 0; padding: var(--nf-space-5); border: 1px dashed var(--nf-color-border); border-radius: var(--nf-radius-md); color: var(--nf-color-text-muted); text-align: center; }
.project-card--sortable { cursor: grab; user-select: none; }
.project-card--sortable:active { cursor: grabbing; }

.project-grid--updating {
  opacity: 0.58;
  pointer-events: none;
}

.project-mixed-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 19rem), 1fr));
  gap: var(--nf-space-4);
  transition: opacity 120ms ease;
}

.project-mixed-grid__covers {
  display: contents;
}

.project-mixed-grid__plain {
  display: grid;
  gap: var(--nf-space-4);
  align-content: start;
}
.project-grid-move,
.project-grid-enter-active,
.project-grid-leave-active { transition: transform 360ms ease, opacity 260ms ease; }
.project-grid-enter-from,
.project-grid-leave-to { opacity: 0; transform: translateY(0.8rem) scale(0.98); }
.project-grid-leave-active { position: absolute; }

@media (min-width: 100rem) {
  .project-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }

  .project-mixed-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

@media (max-width: 75rem) {
  .project-grid,
  .project-mixed-grid {
    grid-template-columns: minmax(0, min(100%, 19rem));
    justify-content: center;
  }
}

@media (max-width: 48rem) {
  .projects-workspace {
    padding-top: calc(var(--nf-space-6) + env(safe-area-inset-top));
    padding-bottom: var(--nf-space-6);
  }

  .page-header {
    align-items: flex-start;
  }

  .page-header__actions {
    flex-direction: column-reverse;
    align-items: stretch;
  }

  .create-project-button {
    width: 3rem;
    min-width: 3rem;
    padding: 0;
    font-size: 0;
  }

  .create-project-button ion-icon {
    font-size: 1.35rem;
  }

  .sync-all-button {
    width: 3rem;
    min-width: 3rem;
    padding: 0;
    font-size: 0;
  }

  .sync-all-button ion-icon,
  .sync-all-button ion-spinner {
    font-size: 1.25rem;
  }

  .workspace-summaries {
    grid-template-columns: 1fr;
  }

  .workspace-summary {
    align-items: flex-start;
  }

  .workspace-summary--today strong {
    text-align: left;
  }

  .project-toolbar {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .search-field {
    grid-column: 1 / -1;
  }

  .toolbar-select {
    min-width: 0;
  }
}

@media (max-width: 28rem) {
  .project-toolbar {
    grid-template-columns: 1fr;
  }

  .search-field {
    grid-column: auto;
  }
}
</style>
