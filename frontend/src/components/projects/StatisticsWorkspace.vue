<script setup lang="ts">
import { computed } from 'vue'
import { IonSpinner } from '@ionic/vue'

import { useLocaleStore } from '@/stores/locale'
import type { Statistics, StatisticsMetrics, UnitCode } from '@/types/api'

const props = withDefaults(
  defineProps<{
    statistics?: Statistics | null
    loading?: boolean
    error?: string | null
  }>(),
  { statistics: null, loading: false, error: null },
)

const emit = defineEmits<{ retry: [] }>()
const locale = useLocaleStore()
const t = locale.translate

type MetricKey = keyof StatisticsMetrics

const metricDefinitions: Array<{ key: MetricKey; label: string }> = [
  { key: 'entries_count', label: 'Записей' },
  { key: 'total', label: 'Всего написано' },
  { key: 'average_symbols_per_active_day', label: 'Среднее символов за активный день' },
  { key: 'average_symbols_per_entry', label: 'Среднее символов в записи' },
  { key: 'average_entries_per_active_day', label: 'Среднее записей за активный день' },
  { key: 'active_days', label: 'Активных дней' },
  { key: 'active_days_percent', label: 'Доля активных дней' },
  { key: 'current_streak', label: 'Текущая серия' },
  { key: 'max_streak', label: 'Лучшая серия' },
  { key: 'best_day', label: 'Лучший день' },
  { key: 'best_weekday', label: 'Самый продуктивный день недели' },
  { key: 'freezes_used', label: 'Использовано заморозок' },
  { key: 'days_since_start', label: 'Дней с начала' },
]

const maxTimelineValue = computed(() =>
  Math.max(1, ...(props.statistics?.timeline.map((item) => Math.abs(item.value)) ?? [])),
)
function formatMetric(key: MetricKey, value: StatisticsMetrics[MetricKey]): string {
  if (typeof value === 'string') return value
  if (key === 'total') return formatValue(value, props.statistics?.unit ?? 'symbols')
  if (key === 'average_entries_per_active_day') return locale.formatNumber(value, 1)
  return locale.formatNumber(value, 0)
}

function formatValue(value: number, unit: UnitCode): string {
  return locale.formatNumber(value, unit === 'symbols' ? 0 : 2)
}

function barWidth(value: number): string {
  return `${Math.max(2, Math.abs(value) / maxTimelineValue.value * 100)}%`
}
</script>

<template>
  <section class="statistics-workspace" aria-labelledby="statistics-heading">
    <div class="statistics-heading">
      <div>
        <p>{{ t('Динамика работы') }}</p>
        <h2 id="statistics-heading">{{ t('Статистика') }}</h2>
      </div>
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
          <dd>{{ formatMetric(metric.key, statistics.metrics[metric.key]) }}</dd>
        </div>
      </dl>

      <div class="timeline-heading">
        <h3>{{ t('Прогресс по дням') }}</h3>
        <span>{{ t('Активных дней') }}: {{ statistics.timeline.length }}</span>
      </div>
      <div v-if="statistics.timeline.length" class="timeline-layout">
        <div class="timeline-bars" aria-hidden="true">
          <div v-for="item in statistics.timeline" :key="item.date" class="timeline-row">
            <span>{{ locale.formatDate(item.date) }}</span>
            <div class="timeline-track">
              <i
                :class="{ 'timeline-bar--negative': item.value < 0 }"
                :style="{ width: barWidth(item.value) }"
              />
            </div>
            <strong>{{ item.value > 0 ? '+' : '' }}{{ formatValue(item.value, statistics.unit) }}</strong>
          </div>
        </div>

        <div class="timeline-table-wrap">
          <table class="timeline-table">
            <caption>{{ t('Таблица прогресса по дням') }}</caption>
            <thead>
              <tr>
                <th scope="col">{{ t('Дата') }}</th>
                <th scope="col">{{ t('В единице проекта') }}</th>
                <th scope="col">{{ t('Символы') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in statistics.timeline" :key="item.date">
                <td>{{ locale.formatDate(item.date) }}</td>
                <td>{{ formatValue(item.value, statistics.unit) }}</td>
                <td>{{ locale.formatNumber(item.symbols, 0) }}</td>
              </tr>
            </tbody>
          </table>
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
.timeline-layout { display: grid; grid-template-columns: minmax(18rem, 1fr) minmax(22rem, 1.1fr); gap: var(--nf-space-4); margin-top: var(--nf-space-3); }
.timeline-bars { display: grid; gap: var(--nf-space-2); align-content: start; padding: var(--nf-space-4); border: 1px solid var(--nf-color-border); border-radius: var(--nf-radius-md); background: var(--nf-color-surface); }
.timeline-row { display: grid; grid-template-columns: 6.8rem minmax(4rem, 1fr) 5rem; gap: var(--nf-space-2); align-items: center; color: var(--nf-color-text-muted); font-size: 0.72rem; }
.timeline-row strong { overflow: hidden; color: var(--nf-color-text); text-align: right; text-overflow: ellipsis; }
.timeline-track { height: 0.55rem; overflow: hidden; border-radius: var(--nf-radius-pill); background: var(--nf-color-surface-muted); }
.timeline-track i { display: block; height: 100%; border-radius: inherit; background: var(--nf-color-primary); }
.timeline-track .timeline-bar--negative { background: var(--nf-color-danger); }
.timeline-table-wrap { overflow-x: auto; border: 1px solid var(--nf-color-border); border-radius: var(--nf-radius-md); background: var(--nf-color-surface); }
.timeline-table { width: 100%; min-width: 29rem; border-collapse: collapse; color: var(--nf-color-text); }
.timeline-table caption { padding: var(--nf-space-3) var(--nf-space-4); color: var(--nf-color-text-muted); font-size: 0.78rem; font-weight: 700; text-align: left; }
.timeline-table th,
.timeline-table td { padding: 0.7rem var(--nf-space-4); border-top: 1px solid var(--nf-color-border); text-align: left; }
.timeline-table th { color: var(--nf-color-text-muted); font-size: 0.7rem; text-transform: uppercase; }

@media (max-width: 70rem) {
  .metric-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .timeline-layout { grid-template-columns: 1fr; }
}
@media (max-width: 42rem) {
  .metric-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .timeline-bars { display: none; }
}
@media (max-width: 25rem) {
  .metric-grid { grid-template-columns: 1fr; }
}
</style>
