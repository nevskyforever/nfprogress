<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { useLocaleStore } from '@/stores/locale'
import type {
  WritingSessionModeKey,
  WritingSessionStart,
  WritingSessionState,
} from '@/types/game'

const props = defineProps<{
  session: WritingSessionState
  busy: boolean
}>()

const emit = defineEmits<{
  start: [payload: WritingSessionStart]
  finish: []
  cancel: []
}>()

const locale = useLocaleStore()
const t = locale.translate
const duration = ref<number>(25)
const target = ref(1_000)
const intention = ref('Продолжить черновик')
const mode = ref<WritingSessionModeKey>('flow')
const ticker = ref(Date.now())
const clockOffset = ref(0)
let timer: ReturnType<typeof setInterval> | undefined
let completionRequested = false

const activeMode = computed(() =>
  props.session.modes.find((item) => item.key === props.session.active?.mode),
)

const selectedMode = computed(() =>
  props.session.modes.find((item) => item.key === mode.value),
)

const remainingSeconds = computed(() => {
  const active = props.session.active
  if (!active) return 0
  if (!active.ends_at) return Math.max(0, active.remaining_seconds)
  const endsAt = Date.parse(active.ends_at)
  if (Number.isNaN(endsAt)) return Math.max(0, active.remaining_seconds)
  return Math.max(0, Math.ceil((endsAt - (ticker.value + clockOffset.value)) / 1_000))
})

const remainingLabel = computed(() => {
  const minutes = Math.floor(remainingSeconds.value / 60)
  const seconds = remainingSeconds.value % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
})

const validConfiguration = computed(() => {
  if (!props.session.allowed_durations_minutes.includes(duration.value) || target.value <= 0) return false
  if (mode.value === 'sprint' && duration.value !== 15) return false
  if (mode.value === 'deep' && duration.value !== 45 && duration.value !== 60) return false
  if (mode.value === 'editing' && intention.value !== 'Отредактировать текст') return false
  return true
})

const recentHistory = computed(() => [...props.session.history].reverse().slice(0, 8))

watch(
  () => props.session.server_time,
  (serverTime) => {
    const parsed = Date.parse(serverTime)
    ticker.value = Date.now()
    clockOffset.value = Number.isNaN(parsed) ? 0 : parsed - ticker.value
  },
  { immediate: true },
)

watch(
  () => props.session.active?.started_at,
  () => { completionRequested = false },
  { immediate: true },
)

watch(remainingSeconds, (remaining) => {
  if (!props.session.active || remaining > 0 || completionRequested) return
  completionRequested = true
  emit('finish')
})

watch(mode, (value) => {
  if (value === 'sprint') duration.value = 15
  if (value === 'deep' && ![45, 60].includes(duration.value)) duration.value = 45
  if (value === 'editing') intention.value = 'Отредактировать текст'
})

function start(): void {
  if (!validConfiguration.value) return
  emit('start', {
    duration_minutes: duration.value as WritingSessionStart['duration_minutes'],
    target_symbols: Math.floor(target.value),
    intention: intention.value,
    mode: mode.value,
  })
}

function gradeName(key: string | undefined): string {
  if (!key || key === 'failed') return t('Цель не достигнута')
  return t(props.session.grades.find((grade) => grade.key === key)?.name ?? key)
}

onMounted(() => {
  timer = setInterval(() => {
    ticker.value = Date.now()
  }, 1_000)
})

onBeforeUnmount(() => clearInterval(timer))
</script>

<template>
  <section class="game-panel" :aria-labelledby="'writing-session-title'">
    <header class="panel-heading">
      <div>
        <p>{{ t('Творческий ритм') }}</p>
        <h2 id="writing-session-title">{{ t('Писательская сессия') }}</h2>
      </div>
      <span class="streak-badge">
        {{ t('Стрик') }}: {{ session.streak }}
      </span>
    </header>

    <article v-if="session.active" class="active-session" aria-live="polite">
      <div>
        <p class="mode-name">{{ t(activeMode?.name ?? session.active.mode) }}</p>
        <strong class="session-clock">{{ remainingLabel }}</strong>
        <p>
          {{ t(session.active.intention) }} ·
          {{ locale.formatNumber(session.active.progress, 0) }} {{ locale.formatUnit('symbols', session.active.progress) }} /
          {{ locale.formatNumber(session.active.target_symbols, 0) }} {{ locale.formatUnit('symbols', session.active.target_symbols) }}
        </p>
      </div>
      <progress
        :value="session.active.progress"
        :max="session.active.target_symbols"
        :aria-label="t('Прогресс писательской сессии')"
      />
      <div class="button-row">
        <button class="nf-button" type="button" :disabled="busy" @click="emit('finish')">
          {{ t('Завершить сессию') }}
        </button>
        <button
          class="nf-button nf-button--secondary"
          type="button"
          :disabled="busy"
          @click="emit('cancel')"
        >
          {{ t('Отменить без результата') }}
        </button>
      </div>
    </article>

    <form v-else class="session-form" @submit.prevent="start">
      <label>
        <span>{{ t('Режим') }}</span>
        <select v-model="mode" :disabled="busy">
          <option v-for="item in session.modes" :key="item.key" :value="item.key">
            {{ t(item.name) }}
          </option>
        </select>
      </label>
      <label>
        <span>{{ t('Длительность') }}</span>
        <select v-model.number="duration" :disabled="busy">
          <option v-for="minutes in session.allowed_durations_minutes" :key="minutes" :value="minutes">
            {{ minutes }} {{ t('мин') }}
          </option>
        </select>
      </label>
      <label>
        <span>{{ t('Намерение') }}</span>
        <select v-model="intention" :disabled="busy || mode === 'editing'">
          <option value="Написать новую сцену">{{ t('Написать новую сцену') }}</option>
          <option value="Продолжить черновик">{{ t('Продолжить черновик') }}</option>
          <option value="Отредактировать текст">{{ t('Отредактировать текст') }}</option>
        </select>
      </label>
      <label>
        <span>{{ t('Цель в символах') }}</span>
        <input v-model.number="target" type="number" min="1" step="1" :disabled="busy" />
      </label>
      <p v-if="selectedMode" class="mode-description">{{ t(selectedMode.description) }}</p>
      <button class="nf-button" type="submit" :disabled="busy || !validConfiguration">
        {{ t('Начать сессию') }}
      </button>
    </form>

    <section class="session-history" :aria-labelledby="'session-history-title'">
      <h3 id="session-history-title">{{ t('Последние результаты') }}</h3>
      <p v-if="recentHistory.length === 0" class="empty-copy">
        {{ t('Завершённые сессии появятся здесь.') }}
      </p>
      <ol v-else>
        <li v-for="(entry, index) in recentHistory" :key="`${entry.finished_at}:${index}`">
          <div>
            <strong>{{ t(entry.intention ?? 'Писательская сессия') }}</strong>
            <span>
              {{ locale.formatNumber(entry.progress ?? 0, 0) }} /
              {{ locale.formatNumber(entry.target_symbols ?? 0, 0) }}
            </span>
          </div>
          <span :class="entry.successful ? 'result-success' : 'result-failed'">
            {{ gradeName(entry.grade) }}
          </span>
        </li>
      </ol>
    </section>
  </section>
</template>

<style scoped>
.game-panel {
  padding: var(--nf-space-5);
  border: 1px solid var(--nf-color-border);
  border-radius: var(--nf-radius-lg);
  background: var(--nf-color-surface);
  box-shadow: var(--nf-shadow-card);
}

.panel-heading,
.button-row,
.session-history li,
.session-history li > div {
  display: flex;
  gap: var(--nf-space-3);
  align-items: center;
}

.panel-heading {
  justify-content: space-between;
}

.panel-heading p,
.panel-heading h2,
.active-session p,
.empty-copy {
  margin: 0;
}

.panel-heading p {
  color: var(--nf-color-accent);
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.panel-heading h2,
.session-history h3 {
  font-family: var(--nf-font-serif);
}

.panel-heading h2 {
  margin-top: var(--nf-space-1);
}

.streak-badge {
  padding: 0.45rem 0.75rem;
  border-radius: var(--nf-radius-pill);
  background: var(--nf-color-primary-soft);
  color: var(--nf-color-primary);
  font-weight: 750;
}

.active-session {
  display: grid;
  gap: var(--nf-space-4);
  margin-top: var(--nf-space-5);
  padding: var(--nf-space-5);
  border-radius: var(--nf-radius-md);
  background: var(--nf-color-primary-soft);
}

.mode-name {
  color: var(--nf-color-text-muted);
  font-weight: 700;
}

.session-clock {
  display: block;
  margin: var(--nf-space-1) 0;
  font-variant-numeric: tabular-nums;
  font-size: clamp(2.25rem, 9vw, 4.5rem);
  letter-spacing: -0.04em;
}

progress {
  width: 100%;
  height: 0.7rem;
  accent-color: var(--nf-color-primary);
}

.session-form {
  display: grid;
  grid-template-columns: repeat(4, minmax(9rem, 1fr));
  gap: var(--nf-space-4);
  margin-top: var(--nf-space-5);
}

.session-form label {
  display: grid;
  gap: var(--nf-space-2);
  color: var(--nf-color-text-muted);
  font-size: 0.875rem;
  font-weight: 700;
}

.session-form input,
.session-form select {
  width: 100%;
  min-height: 2.8rem;
  padding: 0.65rem 0.75rem;
  border: 1px solid var(--nf-color-border);
  border-radius: var(--nf-radius-sm);
  background: var(--nf-color-surface-raised);
  color: var(--nf-color-text);
}

.mode-description {
  grid-column: 1 / -1;
  margin: 0;
  color: var(--nf-color-text-muted);
  line-height: 1.5;
}

.session-form > button {
  width: fit-content;
}

.session-history {
  margin-top: var(--nf-space-6);
  border-top: 1px solid var(--nf-color-border);
}

.session-history h3 {
  margin-bottom: var(--nf-space-3);
}

.session-history ol {
  display: grid;
  gap: var(--nf-space-2);
  padding: 0;
  margin: 0;
  list-style: none;
}

.session-history li {
  justify-content: space-between;
  padding: var(--nf-space-3) 0;
  border-bottom: 1px solid var(--nf-color-border);
}

.session-history li > div {
  flex-wrap: wrap;
}

.session-history li span,
.empty-copy {
  color: var(--nf-color-text-muted);
}

.result-success {
  color: var(--nf-color-success) !important;
  font-weight: 750;
}

.result-failed {
  color: var(--nf-color-danger) !important;
  font-weight: 750;
}

@media (max-width: 60rem) {
  .session-form {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 38rem) {
  .game-panel {
    padding: var(--nf-space-4);
  }

  .session-form {
    grid-template-columns: 1fr;
  }

  .button-row,
  .session-history li,
  .panel-heading {
    align-items: stretch;
    flex-direction: column;
  }

  .button-row > * {
    width: 100%;
  }
}
</style>
