export type JsonPrimitive = boolean | number | string | null
export type JsonValue = JsonPrimitive | JsonObject | JsonValue[]

export interface JsonObject {
  [key: string]: JsonValue
}

export type NoteSourceType = 'project' | 'mindmap'
export type NoteOwnerType = 'project' | 'stage'

export interface NoteChecklistItem {
  id: string
  text: string
  checked: boolean
}

export interface ProjectNote {
  id: string
  title: string
  display_title: string
  content: string
  content_format: 'html' | 'plain'
  checklist: NoteChecklistItem[]
  color: string
  pinned: boolean
  archived: boolean
  sort_order: number
  tags: string[]
  system_tags: string[]
  source_type: NoteSourceType
  source_map_id: string | null
  source_node_id: string | null
  created_at: string
  updated_at: string
  revision: number
  owner_type: NoteOwnerType
  owner_id: string
  owner_order: number
  stage_name: string | null
  read_only: boolean
}

export interface NotesViewContext {
  hasStages: boolean
  stages: Array<{
    id: string
    name: string
  }>
}

export interface NotesResponse {
  notes: ProjectNote[]
  read_only: boolean
  context: NotesViewContext
}

export interface ProjectNotePatch {
  title?: string | null
  content?: string | null
  tags?: string[] | null
  checklist?: NoteChecklistItem[] | null
  color?: string | null
  pinned?: boolean | null
  archived?: boolean | null
}

export interface NoteOrderResponse {
  changed: boolean
  notes: ProjectNote[]
}

export interface MindMapResponse {
  project_id: string
  stage_id: string | null
  name: string
  data: JsonObject | null
  combined: boolean
  read_only: boolean
  has_empty_completed_stage_map: boolean
  notes?: ProjectNote[]
}

export interface NotesScope {
  projectId: string
  stageId?: string | null
}
