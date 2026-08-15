import { computed, reactive, toValue, type MaybeRefOrGetter } from 'vue'

import { useLocaleStore } from '@/stores/locale'
import type { Project, ProjectStatus, UnitCode } from '@/types/api'

const STATUS_LABELS: Record<ProjectStatus, string> = {
  активен: 'Активен',
  'в архиве': 'В архиве',
  завершен: 'Завершён',
}

const UNIT_LABELS: Record<UnitCode, string> = {
  symbols: 'символов',
  A4: 'листов A4',
  author_list: 'авторских листов',
  ficbook_pages: 'страниц Ficbook',
}

export function useProjectPresentation(project: MaybeRefOrGetter<Project>) {
  const locale = useLocaleStore()
  const value = computed(() => toValue(project))
  const progress = computed(() => Math.min(100, Math.max(0, value.value.progress || 0)))
  const statusLabel = computed(() => locale.translate(STATUS_LABELS[value.value.status]))
  const unitLabel = computed(() => locale.translate(UNIT_LABELS[value.value.unit]))
  const fractionDigits = computed(() => (value.value.unit === 'symbols' ? 0 : 2))
  const totalLabel = computed(() =>
    locale.formatNumber(value.value.total, fractionDigits.value),
  )
  const goalLabel = computed(() => {
    if (value.value.infinite || value.value.goal === null) return locale.translate('Без лимита')
    return locale.formatNumber(value.value.goal, fractionDigits.value)
  })
  const progressLabel = computed(() => `${locale.formatNumber(progress.value, 1)}%`)

  return reactive({
    progress,
    statusLabel,
    unitLabel,
    totalLabel,
    goalLabel,
    progressLabel,
  })
}
