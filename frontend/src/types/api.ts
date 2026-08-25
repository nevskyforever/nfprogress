import type { GameCommandResponse } from './game'

export const PROJECT_STATUSES = ['активен', 'в архиве', 'завершен'] as const
export const PROJECT_SORTS = ['name', 'deadline', 'progress', 'updated'] as const
export const UNIT_CODES = ['symbols', 'A4', 'author_list', 'ficbook_pages'] as const

export type ProjectStatus = (typeof PROJECT_STATUSES)[number]
export type ProjectSort = (typeof PROJECT_SORTS)[number]
export type UnitCode = (typeof UNIT_CODES)[number]

export interface ProgressEntry {
  id: string
  new_total: number
  new_total_symbols: number
  added: number
  added_symbols: number
  added_progress: number
  created_at: string
}

export interface Project {
  id: string
  name: string
  goal: number | null
  infinite: boolean
  total: number
  progress: number
  deadline: string | null
  status: ProjectStatus
  unit: UnitCode
  created_at: string | null
  updated_at: string | null
  completed_at: string | null
  personal_goal: number
  today_goal: number | null
  planning_date: string
  plan_daily_goal: number | null
  added_today: number
  remaining: number | null
  streak_enabled: boolean
  streak_status: string | null
  streak_length: number
  max_streak: number
  auto_freeze: boolean
  progress_entries: ProgressEntry[]
  project_notes: Array<Record<string, unknown>>
  mindmap: Record<string, unknown> | null
  stages: Project[]
  stages_enabled: boolean
  combine_stage_mindmaps: boolean
  parent_project_id: string | null
}

export interface StageCreate {
  name: string
  goal?: number | null
  infinite?: boolean
  total?: number
  deadline?: string | null
  personal_goal?: number
  streak_enabled?: boolean
  auto_freeze?: boolean
}

export interface ProjectCreate extends StageCreate {
  unit?: UnitCode
  stages_enabled?: boolean
  stages?: StageCreate[]
  combine_stage_mindmaps?: boolean
}

export interface EntityUpdate {
  name?: string
  goal?: number
  infinite?: boolean
  total?: number
  unit?: UnitCode
  deadline?: string | null
  personal_goal?: number
  streak_enabled?: boolean
  auto_freeze?: boolean
  recalculate_plan?: boolean
}

export interface ProjectUpdate extends EntityUpdate {
  stages_enabled?: boolean
  combine_stage_mindmaps?: boolean
}

export interface ProjectListQuery {
  status?: ProjectStatus
  search?: string
  sort?: ProjectSort
}

export interface ProgressCreate {
  new_total: number
  stage_id?: string | null
}

export interface ProgressResult {
  project: Project
  entry: ProgressEntry
  added_symbols: number
  game: GameCommandResponse | null
  warning: string | null
}

export interface TodayProjectSummary {
  id: string
  name: string
  symbols: number
  unit: UnitCode
  value: number
}

export interface TodaySummary {
  date: string
  symbols: number
  projects: TodayProjectSummary[]
}

export interface GlobalStreakSummary {
  enabled: boolean
  status: string
  length: number
  max_length: number
}

export interface Statistics {
  entity_id: string
  unit: UnitCode
  metrics: StatisticsMetrics
  timeline: Array<{
    date: string
    symbols: number
    value: number
  }>
}

export interface StatisticsMetrics {
  entries_count: number
  total: number
  average_symbols_per_active_day: number
  average_symbols_per_entry: number
  average_entries_per_active_day: number
  freezes_used: number
  best_day: {
    date: string
    symbols: number
    value: number
  } | null
  best_weekday: {
    weekday: number
    symbols: number
  } | null
  current_streak: number
  max_streak: number
  days_since_start: number
  active_days: number
  active_days_percent: number
}

export interface LanguageOption {
  code: SupportedLanguage
  display_name: string
}

export type SupportedLanguage = 'ru' | 'en' | 'es' | 'de' | 'fr' | 'pt_BR'

export interface HealthResponse {
  status: 'ok'
  version: string
}
