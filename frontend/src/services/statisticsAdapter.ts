import { calculatePureStatistics } from '@/core/statistics/calculations'
import type { StatisticsInput } from '@/core/statistics/types'
import type { Project, Statistics } from '@/types/api'

function inputFor(project: Project, stageId?: string): StatisticsInput {
  const entity = stageId
    ? project.stages.find((stage) => stage.id === stageId) ?? project
    : project
  const entries = stageId
    ? entity.progress_entries
    : project.stages.length > 0
      ? project.stages.flatMap((stage) => stage.progress_entries)
      : project.progress_entries
  return {
    entityId: stageId || project.id,
    unit: entity.unit,
    createdAt: entity.created_at,
    planningDate: project.planning_date,
    total: entity.total,
    progressEntries: entries.map((entry) => ({
      addedSymbols: entry.added_symbols,
      createdAt: entry.created_at,
    })),
  }
}

/** Merge verified pure calculations with Python-owned mutable state. */
export function adaptStatistics(
  project: Project,
  serverStatistics: Statistics,
  stageId?: string,
): Statistics {
  const pure = calculatePureStatistics(inputFor(project, stageId))
  return {
    ...serverStatistics,
    ...pure,
    metrics: {
      ...serverStatistics.metrics,
      ...pure.metrics,
    },
  }
}

export function calculateLocalStatistics(project: Project, stageId?: string): Statistics {
  const entity = stageId
    ? project.stages.find((stage) => stage.id === stageId) ?? project
    : project
  const pure = calculatePureStatistics(inputFor(project, stageId))
  return {
    ...pure,
    metrics: {
      ...pure.metrics,
      freezes_used: 0,
      current_streak: entity.streak_length,
      max_streak: entity.max_streak,
    },
  }
}
