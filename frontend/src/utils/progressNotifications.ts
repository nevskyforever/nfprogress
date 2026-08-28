import type { ProgressResult, Project } from '@/types/api'

type Translate = (
  source: string,
  parameters?: Record<string, string | number>,
) => string

type FormatNumber = (value: number, maximumFractionDigits?: number) => string
type FormatUnit = (unit: Project['unit'], value: number) => string

export interface ProgressNotification {
  message: string
  kind: 'success' | 'warning'
}

export function progressChangeNotification(
  progress: ProgressResult,
  entity: Pick<Project, 'unit'>,
  translate: Translate,
  formatNumber: FormatNumber,
  formatUnit: FormatUnit,
): ProgressNotification | null {
  const delta = progress.entry.added
  if (!Number.isFinite(delta) || delta === 0) return null

  const amount = formatNumber(Math.abs(delta), entity.unit === 'symbols' ? 0 : 2)
  const unit = formatUnit(entity.unit, Math.abs(delta))
  const source = delta > 0
    ? 'В проект добавлено {0} {1}'
    : 'Из проекта удалено {0} {1}'

  return {
    message: translate(source, { 0: amount, 1: unit }),
    kind: delta > 0 ? 'success' : 'warning',
  }
}
