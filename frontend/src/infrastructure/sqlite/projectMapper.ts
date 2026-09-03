import type { ProgressEntry, Project, ProjectStatus, UnitCode } from '@/types/api'

export interface SqliteEntityRow {
  id: string
  project_id: string | null
  name: string | null
  goal: number | null
  infinite: number
  unit: string
  status: string
  created_at: string | null
  updated_at: string | null
  payload_json: string
}

export interface SqliteProgressRow {
  id: string
  project_id: string
  stage_id: string | null
  created_at: string | null
  added_symbols: number | null
  added_progress: number | null
  payload_json: string
}

export interface SqliteProjectReadModel {
  mirror_status: string
  projects: SqliteEntityRow[]
  stages: SqliteEntityRow[]
  progress_entries: SqliteProgressRow[]
  project_order: string[]
}

function objectPayload(value: string): Record<string, unknown> {
  try {
    const parsed: unknown = JSON.parse(value)
    return parsed !== null && typeof parsed === 'object' && !Array.isArray(parsed)
      ? parsed as Record<string, unknown> : {}
  } catch {
    return {}
  }
}

function numberOr(value: unknown, fallback: number): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback
}

function stringOr(value: unknown, fallback: string | null): string | null {
  return typeof value === 'string' ? value : fallback
}

function progressEntry(row: SqliteProgressRow): ProgressEntry {
  const payload = objectPayload(row.payload_json)
  return {
    id: row.id,
    new_total: numberOr(payload.new_total, 0),
    new_total_symbols: numberOr(payload.new_total_symbols, 0),
    added: numberOr(payload.added, row.added_progress ?? 0),
    added_symbols: numberOr(payload.added_symbols, row.added_symbols ?? 0),
    added_progress: numberOr(payload.added_progress, row.added_progress ?? 0),
    created_at: stringOr(payload.created_at, row.created_at) ?? '',
  }
}

function entity(
  row: SqliteEntityRow,
  entries: ProgressEntry[],
  stages: Project[],
): Project {
  const payload = objectPayload(row.payload_json)
  const result = {
    ...payload,
    id: row.id,
    name: row.name ?? stringOr(payload.name, '') ?? '',
    goal: row.infinite ? null : row.goal ?? (typeof payload.goal === 'number' ? payload.goal : null),
    infinite: Boolean(row.infinite),
    status: row.status as ProjectStatus,
    unit: row.unit as UnitCode,
    created_at: row.created_at ?? stringOr(payload.created_at, null),
    updated_at: row.updated_at ?? stringOr(payload.updated_at, null),
    progress_entries: entries,
    stages,
    parent_project_id: row.project_id,
  }
  return result as Project
}

export function mapProjects(model: SqliteProjectReadModel): Project[] {
  if (model.mirror_status !== 'healthy') throw new Error('SQLite mirror is not healthy')
  const projectIds = new Set(model.projects.map((row) => row.id))
  if (model.project_order.length !== model.projects.length
    || new Set(model.project_order).size !== model.project_order.length
    || model.project_order.some((id) => !projectIds.has(id))) {
    throw new Error('SQLite project ordering is incomplete')
  }
  const entriesByEntity = new Map<string, ProgressEntry[]>()
  for (const row of model.progress_entries) {
    const entries = entriesByEntity.get(row.stage_id ?? row.project_id) ?? []
    entries.push(progressEntry(row))
    entriesByEntity.set(row.stage_id ?? row.project_id, entries)
  }
  const stagesByProject = new Map<string, Project[]>()
  for (const row of model.stages) {
    const stages = stagesByProject.get(row.project_id ?? '') ?? []
    stages.push(entity(row, entriesByEntity.get(row.id) ?? [], []))
    stagesByProject.set(row.project_id ?? '', stages)
  }
  const rowsById = new Map(model.projects.map((row) => [row.id, row]))
  return model.project_order.map((id) => rowsById.get(id)).map((row) => {
    if (!row) throw new Error('SQLite project ordering is incomplete')
    return entity(
    row,
    entriesByEntity.get(row.id) ?? [],
    stagesByProject.get(row.id) ?? [],
    )
  })
}
