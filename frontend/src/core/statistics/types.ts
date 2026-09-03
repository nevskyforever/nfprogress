import type { ProgressUnit } from '@/core/projects/types'

export interface StatisticsProgressEntry {
  addedSymbols: number
  createdAt: string
}

export interface StatisticsInput {
  entityId: string
  unit: ProgressUnit
  createdAt: string | null
  planningDate: string
  total: number
  progressEntries: StatisticsProgressEntry[]
}

export interface StatisticsTimelineItem {
  date: string
  symbols: number
  value: number
}

export interface PureStatisticsMetrics {
  entries_count: number
  total: number
  average_symbols_per_active_day: number
  average_symbols_per_entry: number
  average_entries_per_active_day: number
  best_day: {
    date: string
    symbols: number
    value: number
  } | null
  best_weekday: {
    weekday: number
    symbols: number
  } | null
  days_since_start: number
  active_days: number
  active_days_percent: number
}

export interface PureStatistics {
  entity_id: string
  unit: ProgressUnit
  metrics: PureStatisticsMetrics
  timeline: StatisticsTimelineItem[]
}

export interface StatisticsMetrics extends PureStatisticsMetrics {
  freezes_used: number
  current_streak: number
  max_streak: number
}

export interface Statistics {
  entity_id: string
  unit: ProgressUnit
  metrics: StatisticsMetrics
  timeline: StatisticsTimelineItem[]
}
