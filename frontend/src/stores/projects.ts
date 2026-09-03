import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { apiErrorMessage } from '@/api/client'
import { projectsApi } from '@/api/projects'
import { adaptStatistics } from '@/services/statisticsAdapter'
import { announceDataChange } from '@/services/dataChanges'
import type {
  EntityUpdate,
  ProgressCreate,
  ProgressResult,
  Project,
  ProjectCreate,
  ProjectListQuery,
  ProjectUpdate,
  StageCreate,
  Statistics,
} from '@/types/api'

export const useProjectsStore = defineStore('projects', () => {
  const projects = ref<Project[]>([])
  const currentProject = ref<Project | null>(null)
  const loading = ref(false)
  const detailLoading = ref(false)
  const creating = ref(false)
  const detailOperation = ref<string | null>(null)
  const detailActionError = ref<string | null>(null)
  const statistics = ref<Statistics | null>(null)
  const statisticsLoading = ref(false)
  const statisticsError = ref<string | null>(null)
  const error = ref<string | null>(null)
  const detailError = ref<string | null>(null)
  const createError = ref<string | null>(null)
  const detailSelections = ref<Record<string, { entityId: string; statisticsEntityId: string }>>({})

  let listController: AbortController | null = null
  let detailController: AbortController | null = null
  let statisticsSequence = 0

  const projectCount = computed(() => projects.value.length)
  const detailBusy = computed(() => detailOperation.value !== null)

  function storeProject(project: Project): Project {
    currentProject.value = project
    const index = projects.value.findIndex((item) => item.id === project.id)
    if (index >= 0) projects.value.splice(index, 1, project)
    return project
  }

  function saveDetailSelection(projectId: string, entityId: string, statisticsEntityId: string): void {
    detailSelections.value = {
      ...detailSelections.value,
      [projectId]: { entityId, statisticsEntityId },
    }
  }

  function detailSelection(projectId: string): { entityId: string; statisticsEntityId: string } | undefined {
    return detailSelections.value[projectId]
  }

  async function runDetailMutation(
    operation: string,
    action: () => Promise<Project>,
  ): Promise<Project | null> {
    if (detailBusy.value) return null
    detailOperation.value = operation
    detailActionError.value = null
    try {
      const project = storeProject(await action())
      announceDataChange('projects')
      return project
    } catch (mutationError) {
      detailActionError.value = apiErrorMessage(mutationError)
      return null
    } finally {
      detailOperation.value = null
    }
  }

  async function runStageMutation(
    projectId: string,
    operation: string,
    action: () => Promise<unknown>,
  ): Promise<Project | null> {
    return runDetailMutation(operation, async () => {
      await action()
      return projectsApi.get(projectId)
    })
  }

  async function load(query: ProjectListQuery = {}): Promise<void> {
    listController?.abort()
    const controller = new AbortController()
    listController = controller
    loading.value = true
    error.value = null
    try {
      projects.value = await projectsApi.list(query, controller.signal)
    } catch (loadError) {
      if (loadError instanceof DOMException && loadError.name === 'AbortError') return
      error.value = apiErrorMessage(loadError)
    } finally {
      if (listController === controller) {
        loading.value = false
        listController = null
      }
    }
  }

  async function loadOne(projectId: string): Promise<void> {
    detailController?.abort()
    const controller = new AbortController()
    detailController = controller
    detailLoading.value = true
    detailError.value = null
    detailActionError.value = null
    statisticsSequence += 1
    statisticsLoading.value = false
    statistics.value = null
    statisticsError.value = null
    currentProject.value = null
    try {
      storeProject(await projectsApi.get(projectId, controller.signal))
    } catch (loadError) {
      if (loadError instanceof DOMException && loadError.name === 'AbortError') return
      detailError.value = apiErrorMessage(loadError)
    } finally {
      if (detailController === controller) {
        detailLoading.value = false
        detailController = null
      }
    }
  }

  async function refreshCurrent(projectId: string): Promise<Project | null> {
    try {
      const project = storeProject(await projectsApi.get(projectId))
      announceDataChange('projects')
      return project
    } catch (refreshError) {
      detailActionError.value = apiErrorMessage(refreshError)
      return null
    }
  }

  async function create(payload: ProjectCreate): Promise<Project | null> {
    creating.value = true
    createError.value = null
    try {
      const project = await projectsApi.create(payload)
      projects.value = [project, ...projects.value.filter((item) => item.id !== project.id)]
      currentProject.value = project
      announceDataChange('projects')
      return project
    } catch (creationError) {
      createError.value = apiErrorMessage(creationError)
      return null
    } finally {
      creating.value = false
    }
  }

  function clearCreateError(): void {
    createError.value = null
  }

  function clearDetailActionError(): void {
    detailActionError.value = null
  }

  function updateCurrent(projectId: string, payload: ProjectUpdate): Promise<Project | null> {
    return runDetailMutation('update-project', () => projectsApi.update(projectId, payload))
  }

  function setArchived(projectId: string, archived: boolean): Promise<Project | null> {
    return runDetailMutation(archived ? 'archive-project' : 'activate-project', () =>
      projectsApi.setArchived(projectId, archived),
    )
  }

  async function reorderProjects(projectIds: string[]): Promise<boolean> {
    try {
      projects.value = await projectsApi.reorder(projectIds)
      announceDataChange('projects')
      return true
    } catch (mutationError) {
      error.value = apiErrorMessage(mutationError)
      return false
    }
  }

  function completeCurrent(projectId: string): Promise<Project | null> {
    return runDetailMutation('complete-project', () => projectsApi.complete(projectId))
  }

  async function removeCurrent(projectId: string): Promise<boolean> {
    if (detailBusy.value) return false
    detailOperation.value = 'delete-project'
    detailActionError.value = null
    try {
      await projectsApi.remove(projectId)
      projects.value = projects.value.filter((item) => item.id !== projectId)
      if (currentProject.value?.id === projectId) currentProject.value = null
      announceDataChange('projects')
      return true
    } catch (mutationError) {
      detailActionError.value = apiErrorMessage(mutationError)
      return false
    } finally {
      detailOperation.value = null
    }
  }

  function createStage(projectId: string, payload: StageCreate): Promise<Project | null> {
    return runStageMutation(projectId, 'create-stage', () =>
      projectsApi.createStage(projectId, payload),
    )
  }

  function updateStage(
    projectId: string,
    stageId: string,
    payload: EntityUpdate,
  ): Promise<Project | null> {
    return runStageMutation(projectId, `update-stage:${stageId}`, () =>
      projectsApi.updateStage(projectId, stageId, payload),
    )
  }

  function removeStage(projectId: string, stageId: string): Promise<Project | null> {
    return runStageMutation(projectId, `delete-stage:${stageId}`, () =>
      projectsApi.removeStage(projectId, stageId),
    )
  }

  function completeStage(projectId: string, stageId: string): Promise<Project | null> {
    return runStageMutation(projectId, `complete-stage:${stageId}`, () =>
      projectsApi.completeStage(projectId, stageId),
    )
  }

  function reorderStages(projectId: string, stageIds: string[]): Promise<Project | null> {
    return runDetailMutation('reorder-stages', () =>
      projectsApi.reorderStages(projectId, stageIds),
    )
  }

  async function recordProgress(
    projectId: string,
    payload: ProgressCreate,
  ): Promise<ProgressResult | null> {
    if (detailBusy.value) return null
    detailOperation.value = 'record-progress'
    detailActionError.value = null
    try {
      const result = await projectsApi.recordProgress(projectId, payload)
      storeProject(result.project)
      announceDataChange('projects')
      return result
    } catch (mutationError) {
      detailActionError.value = apiErrorMessage(mutationError)
      return null
    } finally {
      detailOperation.value = null
    }
  }

  function deleteProgress(
    projectId: string,
    entryId: string,
    stageId?: string,
  ): Promise<Project | null> {
    return runDetailMutation(`delete-progress:${entryId}`, () =>
      projectsApi.deleteProgress(projectId, entryId, stageId),
    )
  }

  async function loadStatistics(projectId: string, stageId?: string): Promise<void> {
    const sequence = ++statisticsSequence
    statisticsLoading.value = true
    statisticsError.value = null
    try {
      const result = await projectsApi.statistics(projectId, stageId)
      const project = currentProject.value
      const adapted = project?.id === projectId
        ? adaptStatistics(project, result, stageId)
        : result
      if (sequence === statisticsSequence) statistics.value = adapted
    } catch (loadError) {
      if (sequence === statisticsSequence) {
        statistics.value = null
        statisticsError.value = apiErrorMessage(loadError)
      }
    } finally {
      if (sequence === statisticsSequence) statisticsLoading.value = false
    }
  }

  function cancelList(): void {
    listController?.abort()
    listController = null
  }

  function cancelDetail(): void {
    detailController?.abort()
    detailController = null
    statisticsSequence += 1
    statisticsLoading.value = false
  }

  return {
    projects,
    currentProject,
    detailSelection,
    saveDetailSelection,
    loading,
    detailLoading,
    creating,
    detailOperation,
    detailBusy,
    detailActionError,
    statistics,
    statisticsLoading,
    statisticsError,
    error,
    detailError,
    createError,
    projectCount,
    load,
    loadOne,
    refreshCurrent,
    create,
    clearCreateError,
    clearDetailActionError,
    updateCurrent,
    setArchived,
    reorderProjects,
    completeCurrent,
    removeCurrent,
    createStage,
    updateStage,
    removeStage,
    completeStage,
    reorderStages,
    recordProgress,
    deleteProgress,
    loadStatistics,
    cancelList,
    cancelDetail,
  }
})
