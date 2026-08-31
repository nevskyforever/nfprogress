import type { ProgressResult, Project } from '@/types/api'
import type { SyncBatchResult } from '@/types/integrations'

type Translate = (source: string, parameters?: Record<string, string | number>) => string

export interface SyncBatchNotification {
  message: string
  kind: 'success' | 'warning'
}

function progressUnit(progress: ProgressResult, stageId: string | null): Project['unit'] {
  if (!stageId) return progress.project.unit
  return progress.project.stages.find((stage) => stage.id === stageId)?.unit
    ?? progress.project.unit
}

function formatDelta(
  values: Map<Project['unit'], number>,
  formatNumber: (value: number) => string,
  formatUnit: (unit: Project['unit'], value: number) => string,
): string {
  return [...values.entries()]
    .map(([unit, value]) => `${formatNumber(value)} ${formatUnit(unit, value)}`)
    .join(', ')
}

/** Build one locale-aware notification for a batch, regardless of its size. */
export function syncBatchNotification(
  batch: SyncBatchResult,
  translate: Translate,
  formatNumber: (value: number) => string,
  formatUnit: (unit: Project['unit'], value: number) => string,
): SyncBatchNotification {
  const projectIds = new Set<string>()
  let stages = 0
  const added = new Map<Project['unit'], number>()
  const removed = new Map<Project['unit'], number>()

  for (const item of batch.items) {
    if (!item.ok) continue
    if (item.stage_id) stages += 1
    else projectIds.add(item.project_id)
    const progress = item.progress
    if (!progress || progress.entry.added === 0) continue
    const target = progress.entry.added > 0 ? added : removed
    const unit = progressUnit(progress, item.stage_id)
    target.set(unit, (target.get(unit) ?? 0) + Math.abs(progress.entry.added))
  }

  const details = [
    translate('Синхронизировано: {projects} проектов, {stages} этапов.', {
      projects: projectIds.size,
      stages,
    }),
  ]
  if (added.size) {
    details.push(translate('Добавлено: {amount}.', {
      amount: formatDelta(added, formatNumber, formatUnit),
    }))
  }
  if (removed.size) {
    details.push(translate('Удалено: {amount}.', {
      amount: formatDelta(removed, formatNumber, formatUnit),
    }))
  }
  if (batch.failed) {
    details.push(translate('Не удалось синхронизировать источников: {count}.', {
      count: batch.failed,
    }))
  }
  return { message: details.join(' '), kind: batch.failed ? 'warning' : 'success' }
}
