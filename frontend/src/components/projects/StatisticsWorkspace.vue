<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { IonSpinner } from '@ionic/vue'

import { useLocaleStore } from '@/stores/locale'
import type { Project, Statistics, StatisticsMetrics, UnitCode } from '@/types/api'

const props = withDefaults(
  defineProps<{
    statistics?: Statistics | null
    project?: Project | null
    loading?: boolean
    error?: string | null
    fixedStageId?: string | null
  }>(),
  { statistics: null, project: null, loading: false, error: null, fixedStageId: null },
)

const emit = defineEmits<{ retry: [] }>()
const selectedEntityId = defineModel<string>('entityId', { default: '' })
const locale = useLocaleStore()
const t = locale.translate
const timelinePanel = ref<HTMLElement | null>(null)
const chartVisible = ref(false)
let timelineObserver: IntersectionObserver | undefined

type MetricKey = keyof StatisticsMetrics

const metricDefinitions: Array<{ key: MetricKey; label: string }> = [
  { key: 'entries_count', label: 'Записей' },
  { key: 'total', label: 'Всего написано' },
  { key: 'average_symbols_per_active_day', label: 'Среднее символов за активный день' },
  { key: 'average_symbols_per_entry', label: 'Среднее символов в записи' },
  { key: 'average_entries_per_active_day', label: 'Среднее записей за активный день' },
  { key: 'active_days', label: 'Активных дней' },
  { key: 'active_days_percent', label: 'Доля активных дней' },
  { key: 'current_streak', label: 'Текущий стрик' },
  { key: 'max_streak', label: 'Лучший стрик' },
  { key: 'best_day', label: 'Лучший день' },
  { key: 'best_weekday', label: 'Самый продуктивный день недели' },
  { key: 'freezes_used', label: 'Использовано заморозок' },
  { key: 'days_since_start', label: 'Дней с начала' },
]

const maxTimelineValue = computed(() =>
  Math.max(1, ...(props.statistics?.timeline.map((item) => Math.abs(item.value)) ?? [])),
)
function formatMetric(key: MetricKey): string {
  const metrics = props.statistics?.metrics
  if (!metrics) return '—'
  if (key === 'best_day') {
    const value = metrics.best_day
    if (!value) return '—'
    const unit = locale.formatUnit('symbols', value.symbols)
    return `${locale.formatDate(value.date)} · ${locale.formatNumber(value.symbols, 0)} ${unit}`
  }
  if (key === 'best_weekday') {
    const value = metrics.best_weekday
    if (!value) return '—'
    const referenceMonday = new Date(2024, 0, 1 + value.weekday)
    return new Intl.DateTimeFormat(locale.localeTag, { weekday: 'long' }).format(referenceMonday)
  }
  const value = metrics[key]
  if (typeof value !== 'number') return '—'
  if (key === 'total') return formatValue(value, props.statistics?.unit ?? 'symbols')
  if (key === 'average_entries_per_active_day' || key === 'active_days_percent') {
    const formatted = locale.formatNumber(value, 1)
    return key === 'active_days_percent' ? `${formatted}%` : formatted
  }
  return locale.formatNumber(value, 0)
}

function formatValue(value: number, unit: UnitCode): string {
  return locale.formatNumber(value, unit === 'symbols' ? 0 : 2)
}

function barWidth(value: number): string {
  return `${Math.max(2, Math.abs(value) / maxTimelineValue.value * 100)}%`
}

const cumulativeTimeline = computed(() => {
  const dailyChange = (props.statistics?.timeline ?? [])
    .reduce((sum, item) => sum + item.value, 0)
  let total = (props.statistics?.metrics.total ?? dailyChange) - dailyChange
  return (props.statistics?.timeline ?? []).map((item) => {
    total += item.value
    return { ...item, total }
  })
})
const cumulativeRange = computed(() => {
  const values = cumulativeTimeline.value.map((item) => item.total)
  const minimum = Math.min(0, ...values)
  const maximum = Math.max(1, ...values)
  return { minimum, maximum, size: Math.max(1, maximum - minimum) }
})
const chartPoints = computed(() => cumulativeTimeline.value.map((item, index, items) => {
  const x = items.length === 1 ? 50 : 4 + index / (items.length - 1) * 92
  const y = 92 - (item.total - cumulativeRange.value.minimum) / cumulativeRange.value.size * 84
  return `${x},${y}`
}).join(' '))

function observeTimeline(): void {
  timelineObserver?.disconnect()
  chartVisible.value = false
  void nextTick(() => {
    if (!timelinePanel.value) return
    if (!('IntersectionObserver' in window)) {
      chartVisible.value = true
      return
    }
    timelineObserver = new IntersectionObserver(([entry]) => {
      if (!entry?.isIntersecting) return
      chartVisible.value = true
      timelineObserver?.disconnect()
    }, { threshold: 0.2 })
    timelineObserver.observe(timelinePanel.value)
  })
}

watch(() => props.statistics?.timeline, observeTimeline, { deep: true, immediate: true })
onBeforeUnmount(() => timelineObserver?.disconnect())
</script>

<template>
  <section class="statistics-workspace" aria-labelledby="statistics-heading">
    <div class="statistics-heading">
      <div>
        <p>{{ t('Динамика работы') }}</p>
        <h2 id="statistics-heading">{{ t('Статистика') }}</h2>
      </div>
      <label v-if="project?.stages.length && !fixedStageId" class="statistics-entity" for="statistics-entity">
        <span>{{ t('Статистика по') }}</span>
        <select id="statistics-entity" v-model="selectedEntityId" :disabled="loading">
          <option value="">{{ t('Весь проект') }}</option>
          <option v-for="stage in project.stages" :key="stage.id" :value="stage.id">
            {{ stage.name }}
          </option>
        </select>
      </label>
      <button
        v-if="error"
        class="nf-button nf-button--secondary"
        type="button"
        :disabled="loading"
        @click="emit('retry')"
      >
        {{ t('Повторить') }}
      </button>
    </div>

    <div v-if="loading" class="statistics-state" role="status">
      <IonSpinner name="crescent" aria-hidden="true" />
      {{ t('Обновляем статистику…') }}
    </div>
    <p v-else-if="error" class="statistics-error" role="alert">{{ error }}</p>
    <template v-else-if="statistics">
      <dl class="metric-grid">
        <div v-for="metric in metricDefinitions" :key="metric.key" class="metric-card">
          <dt>{{ t(metric.label) }}</dt>
          <dd>{{ formatMetric(metric.key) }}</dd>
        </div>
      </dl>

      <div class="timeline-heading">
        <h3>{{ t('Прогресс по дням') }}</h3>
        <span>{{ t('Активных дней') }}: {{ statistics.timeline.length }}</span>
      </div>
      <div v-if="statistics.timeline.length" ref="timelinePanel" class="timeline-layout">
        <div class="timeline-bars" :class="{ 'timeline-bars--visible': chartVisible }" aria-hidden="true">
          <div v-for="item in statistics.timeline" :key="item.date" class="timeline-row">
            <span>{{ locale.formatDate(item.date) }}</span>
            <div class="timeline-track">
              <i
                :class="{ 'timeline-bar--negative': item.value < 0 }"
                :style="{ '--bar-width': barWidth(item.value) }"
              />
            </div>
            <strong>{{ item.value > 0 ? '+' : '' }}{{ formatValue(item.value, statistics.unit) }}</strong>
          </div>
        </div>

        <div class="progress-chart" :class="{ 'progress-chart--visible': chartVisible }">
          <div class="progress-chart__caption">
            <span>{{ t('Общее количество единиц') }}</span>
            <strong>{{ formatValue(cumulativeTimeline.at(-1)?.total ?? 0, statistics.unit) }}</strong>
          </div>
          <svg viewBox="0 0 100 100" role="img" :aria-label="t('График роста общего прогресса')" preserveAspectRatio="none">
            <line x1="4" x2="96" y1="92" y2="92" />
            <line x1="4" x2="4" y1="4" y2="92" />
            <polyline :points="chartPoints" />
          </svg>
          <div class="progress-chart__y-axis" aria-hidden="true">
            <span>{{ formatValue(cumulativeRange.maximum, statistics.unit) }}</span>
            <span>{{ formatValue(cumulativeRange.minimum, statistics.unit) }}</span>
          </div>
          <div class="progress-chart__axis"><span>{{ locale.formatDate(statistics.timeline[0]?.date ?? null) }}</span><span>{{ locale.formatDate(statistics.timeline.at(-1)?.date ?? null) }}</span></div>
        </div>
      </div>
      <p v-else class="statistics-empty">{{ t('Добавьте первую запись, чтобы увидеть динамику.') }}</p>
    </template>
  </section>
</template>

<style scoped>
.statistics-workspace { margin-top: var(--nf-space-7); }
.statistics-heading { display: flex; gap: var(--nf-space-4); align-items: flex-end; justify-content: space-between; margin-bottom: var(--nf-space-4); }
.statistics-heading p { margin: 0 0 var(--nf-space-1); color: var(--nf-color-accent); font-size: 0.72rem; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase; }
.statistics-heading h2 { margin: 0; color: var(--nf-color-text); font-family: var(--nf-font-serif); font-size: clamp(1.7rem, 4vw, 2.3rem); }
.statistics-entity { display: grid; gap: var(--nf-space-1); min-width: min(18rem, 45vw); margin-left: auto; color: var(--nf-color-text-muted); font-size: 0.75rem; font-weight: 700; }
.statistics-entity select { min-height: 2.75rem; padding: 0.55rem 0.75rem; border: 1px solid var(--nf-color-border); border-radius: var(--nf-radius-sm); background: var(--nf-color-surface); color: var(--nf-color-text); }
.statistics-state,
.statistics-error,
.statistics-empty { display: flex; gap: var(--nf-space-2); align-items: center; margin: 0; padding: var(--nf-space-5); border: 1px solid var(--nf-color-border); border-radius: var(--nf-radius-md); background: var(--nf-color-surface); color: var(--nf-color-text-muted); }
.statistics-state ion-spinner { width: 1.25rem; height: 1.25rem; }
.statistics-error { border-color: color-mix(in srgb, var(--nf-color-danger) 40%, var(--nf-color-border)); color: var(--nf-color-danger); }
.metric-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: var(--nf-space-3); margin: 0; }
.metric-card { min-width: 0; padding: var(--nf-space-4); border: 1px solid var(--nf-color-border); border-radius: var(--nf-radius-md); background: var(--nf-color-surface); }
.metric-card dt { min-height: 2.2em; color: var(--nf-color-text-muted); font-size: 0.75rem; line-height: 1.35; }
.metric-card dd { margin: var(--nf-space-2) 0 0; overflow-wrap: anywhere; color: var(--nf-color-text); font-family: var(--nf-font-serif); font-size: clamp(1.05rem, 2vw, 1.4rem); font-weight: 750; }
.timeline-heading { display: flex; align-items: baseline; justify-content: space-between; margin-top: var(--nf-space-6); }
.timeline-heading h3 { margin: 0; color: var(--nf-color-text); font-size: 1rem; }
.timeline-heading span { color: var(--nf-color-text-muted); font-size: 0.78rem; }
.timeline-layout { display: grid; gap: var(--nf-space-3); margin-top: var(--nf-space-3); }
.timeline-bars { display: grid; max-height: 18rem; gap: var(--nf-space-2); align-content: start; overflow-y: auto; padding: var(--nf-space-3); border: 1px solid var(--nf-color-border); border-radius: var(--nf-radius-md); background: var(--nf-color-surface); }
.timeline-row { display: grid; grid-template-columns: 6.8rem minmax(4rem, 1fr) 5rem; gap: var(--nf-space-2); align-items: center; color: var(--nf-color-text-muted); font-size: 0.72rem; }
.timeline-row strong { overflow: hidden; color: var(--nf-color-text); text-align: right; text-overflow: ellipsis; }
.timeline-track { height: 0.55rem; overflow: hidden; border-radius: var(--nf-radius-pill); background: var(--nf-color-surface-muted); }
.timeline-track i { display: block; width: 0 !important; height: 100%; border-radius: inherit; background: var(--nf-color-primary); transition: width 700ms cubic-bezier(.2,.8,.2,1); }
.timeline-bars--visible .timeline-track i { width: var(--bar-width, 0) !important; }
.timeline-track .timeline-bar--negative { background: var(--nf-color-danger); }
.progress-chart { position: relative; padding: var(--nf-space-3); border: 1px solid var(--nf-color-border); border-radius: var(--nf-radius-md); background: var(--nf-color-surface); }
.progress-chart__caption, .progress-chart__axis { display: flex; justify-content: space-between; gap: var(--nf-space-2); color: var(--nf-color-text-muted); font-size: .72rem; }
.progress-chart__caption strong { color: var(--nf-color-text); font-variant-numeric: tabular-nums; }
.progress-chart svg { display: block; width: 100%; height: 10rem; margin-top: var(--nf-space-2); overflow: visible; }
.progress-chart__y-axis { position: absolute; top: 3.3rem; bottom: 2.2rem; left: 1.15rem; display: flex; flex-direction: column; justify-content: space-between; color: var(--nf-color-text-muted); font-size: .62rem; pointer-events: none; }
.progress-chart line { stroke: var(--nf-color-border); stroke-width: .6; }
.progress-chart polyline { fill: none; stroke: var(--nf-color-primary); stroke-width: 2.4; stroke-linecap: round; stroke-linejoin: round; stroke-dasharray: 180; stroke-dashoffset: 180; transition: stroke-dashoffset 900ms cubic-bezier(.2,.8,.2,1); }
.progress-chart--visible polyline { stroke-dashoffset: 0; }

@media (max-width: 70rem) {
  .metric-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
@media (max-width: 42rem) {
  .statistics-heading { align-items: stretch; flex-direction: column; }
  .statistics-entity { min-width: 0; margin-left: 0; }
  .metric-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .timeline-row { grid-template-columns: 5.5rem minmax(3rem, 1fr) 4.5rem; }
}
@media (max-width: 25rem) {
  .metric-grid { grid-template-columns: 1fr; }
}
</style>
