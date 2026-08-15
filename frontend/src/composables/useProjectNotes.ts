import { computed, ref, type Ref } from 'vue'

import { notesApi } from '@/api/notes'
import { apiErrorMessage } from '@/api/client'
import type {
  JsonObject,
  MindMapResponse,
  NotesScope,
  NotesViewContext,
  ProjectNote,
  ProjectNotePatch,
} from '@/types/notes'

const EMPTY_CONTEXT: NotesViewContext = { hasStages: false, stages: [] }

function sortedNotes(notes: ProjectNote[]): ProjectNote[] {
  return [...notes].sort((left, right) => {
    if (left.archived !== right.archived) return Number(left.archived) - Number(right.archived)
    if (left.pinned !== right.pinned) return Number(right.pinned) - Number(left.pinned)
    if (left.sort_order !== right.sort_order) return left.sort_order - right.sort_order
    return left.created_at.localeCompare(right.created_at)
  })
}

export function useProjectNotes(projectId: Ref<string>, stageId: Ref<string | null>) {
  const notes = ref<ProjectNote[]>([])
  const context = ref<NotesViewContext>(EMPTY_CONTEXT)
  const mindMap = ref<MindMapResponse | null>(null)
  const readOnly = ref(false)
  const loading = ref(false)
  const mutating = ref(false)
  const error = ref<string | null>(null)
  let loadSequence = 0

  const scope = computed<NotesScope>(() => ({
    projectId: projectId.value,
    stageId: stageId.value,
  }))

  function replaceNote(note: ProjectNote): void {
    const next = notes.value.filter(({ id }) => id !== note.id)
    next.push(note)
    notes.value = sortedNotes(next)
  }

  async function load(): Promise<void> {
    const sequence = ++loadSequence
    if (!projectId.value) return
    loading.value = true
    error.value = null
    try {
      const [notePayload, mapPayload, projectContextPayload] = await Promise.all([
        notesApi.list(scope.value),
        notesApi.mindMap(scope.value),
        stageId.value ? notesApi.list({ projectId: projectId.value }) : Promise.resolve(null),
      ])
      if (sequence !== loadSequence) return
      notes.value = notePayload.notes
      context.value = projectContextPayload?.context ?? notePayload.context
      readOnly.value = notePayload.read_only
      mindMap.value = mapPayload
    } catch (reason) {
      if (sequence === loadSequence) error.value = apiErrorMessage(reason)
    } finally {
      if (sequence === loadSequence) loading.value = false
    }
  }

  async function createNote(): Promise<ProjectNote | null> {
    mutating.value = true
    error.value = null
    try {
      const note = await notesApi.create(scope.value)
      replaceNote(note)
      return note
    } catch (reason) {
      error.value = apiErrorMessage(reason)
      return null
    } finally {
      mutating.value = false
    }
  }

  async function updateNote(noteId: string, patch: ProjectNotePatch): Promise<ProjectNote | null> {
    mutating.value = true
    error.value = null
    try {
      const note = await notesApi.update(scope.value, noteId, patch)
      replaceNote(note)
      return note
    } catch (reason) {
      error.value = apiErrorMessage(reason)
      return null
    } finally {
      mutating.value = false
    }
  }

  async function deleteNote(noteId: string): Promise<boolean> {
    mutating.value = true
    error.value = null
    try {
      await notesApi.remove(scope.value, noteId)
      notes.value = notes.value.filter(({ id }) => id !== noteId)
      return true
    } catch (reason) {
      error.value = apiErrorMessage(reason)
      return false
    } finally {
      mutating.value = false
    }
  }

  async function reorderNotes(noteIds: string[]): Promise<boolean> {
    mutating.value = true
    error.value = null
    try {
      const result = await notesApi.reorder(scope.value, noteIds)
      notes.value = result.notes
      return true
    } catch (reason) {
      error.value = apiErrorMessage(reason)
      return false
    } finally {
      mutating.value = false
    }
  }

  async function saveMindMap(
    data: JsonObject,
    requestedScope: NotesScope = scope.value,
  ): Promise<MindMapResponse> {
    const result = await notesApi.saveMindMap(requestedScope, data)
    const stillCurrent =
      projectId.value === requestedScope.projectId &&
      stageId.value === (requestedScope.stageId ?? null)
    if (stillCurrent) {
      mindMap.value = result
      if (result.notes) notes.value = result.notes
    }
    return result
  }

  async function refreshMindMap(): Promise<MindMapResponse | null> {
    error.value = null
    try {
      const result = await notesApi.mindMap(scope.value)
      mindMap.value = result
      return result
    } catch (reason) {
      error.value = apiErrorMessage(reason)
      return null
    }
  }

  function invalidate(): void {
    loadSequence += 1
  }

  return {
    notes,
    context,
    mindMap,
    readOnly,
    loading,
    mutating,
    error,
    scope,
    load,
    createNote,
    updateNote,
    deleteNote,
    reorderNotes,
    saveMindMap,
    refreshMindMap,
    invalidate,
  }
}
