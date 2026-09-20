<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { IonContent, IonHeader, IonIcon, IonModal, IonSpinner } from '@ionic/vue'
import { closeOutline } from 'ionicons/icons'

import { apiErrorMessage } from '@/api/client'
import { gameApi } from '@/api/game'
import { currentPlatform } from '@/platform/runtime'
import { useLocaleStore } from '@/stores/locale'
import type { DeveloperModeState, DeveloperStreakState, GameState } from '@/types/game'

const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{ close: []; updated: [state: GameState] }>()

const locale = useLocaleStore()
const t = locale.translate
const loading = ref(false)
const saving = ref(false)
const granting = ref(false)
const transferring = ref(false)
const error = ref<string | null>(null)
const success = ref<string | null>(null)
const developerState = ref<DeveloperModeState | null>(null)
const streakState = ref<DeveloperStreakState | null>(null)
const streakBusy = ref(false)
const form = reactive({
  level: 1,
  health: 0,
  coins: 0,
  exp: 0,
  testDateEnabled: false,
  testDatetime: '',
})
const maxHealth = ref(100)
const grant = reactive({ category: '', itemId: '', count: 1 })
const streak = reactive({ type: 'global' as 'global' | 'project' | 'stage', targetId: 'global', length: 1 })

const categories = computed(() => developerState.value?.state.shop.categories ?? [])
const selectedItems = computed(
  () => categories.value.find((category) => category.key === grant.category)?.items ?? [],
)
const streakTargets = computed(() => streakState.value?.targets ?? [])
const selectedStreakTarget = computed(
  () => streakTargets.value.find((target) => target.id === streak.targetId) ?? null,
)
const visibleStreakTargets = computed(() => streakTargets.value.filter((target) => target.type === streak.type))
const testDataControlsAvailable = currentPlatform() === 'tauri'

function datetimeLocal(value: string | null): string {
  const date = value ? new Date(value) : new Date()
  if (Number.isNaN(date.getTime())) return value?.slice(0, 16) ?? ''
  const offset = date.getTimezoneOffset()
  return new Date(date.getTime() - offset * 60_000).toISOString().slice(0, 16)
}

function fill(state: DeveloperModeState): void {
  const profile = state.state.profile
  form.level = profile.level
  form.health = profile.health
  maxHealth.value = profile.max_health
  form.coins = profile.coins
  form.exp = profile.experience
  form.testDateEnabled = state.test_date_enabled
  form.testDatetime = datetimeLocal(state.test_datetime)
  const category = state.state.shop.categories[0]
  grant.category = category?.key ?? ''
  grant.itemId = category?.items[0]?.key ?? ''
  grant.count = 1
}

function normalizeNumber(value: unknown, fallback = 0): number {
  const number = typeof value === 'number' ? value : Number(value)
  return Number.isFinite(number) ? number : fallback
}

function normalizeForm(): void {
  form.level = Math.max(1, Math.min(99, Math.trunc(normalizeNumber(form.level, 1))))
  form.health = Math.round(Math.max(0, Math.min(maxHealth.value, normalizeNumber(form.health))) * 10) / 10
  form.coins = Math.round(Math.max(0, normalizeNumber(form.coins)) * 10) / 10
  form.exp = Math.round(Math.max(0, normalizeNumber(form.exp)) * 10) / 10
}

async function load(): Promise<void> {
  loading.value = true
  error.value = null
  success.value = null
  try {
    const [state, transferResult, loadedStreakState] = await Promise.all([
      gameApi.developerState(),
      testDataControlsAvailable ? gameApi.takeProfileTransferResult() : Promise.resolve(null),
      gameApi.developerStreakState(),
    ])
    developerState.value = state
    streakState.value = loadedStreakState
    fill(state)
    if (!visibleStreakTargets.value.some((target) => target.id === streak.targetId)) {
      streak.targetId = visibleStreakTargets.value[0]?.id ?? 'global'
    }
    if (transferResult?.status === 'complete') {
      success.value = t('Замена данных успешно завершена.')
    } else if (transferResult?.status === 'error') {
      error.value = `${t('Не удалось заменить данные')}: ${transferResult.error ?? t('неизвестная ошибка')}`
    }
  } catch (reason) {
    error.value = t(apiErrorMessage(reason))
  } finally {
    loading.value = false
  }
}

function selectStreakType(): void {
  streak.targetId = visibleStreakTargets.value[0]?.id ?? 'global'
}

function targetRequest() {
  const target = selectedStreakTarget.value
  if (!target) return null
  return {
    type: target.type,
    ...(target.project_id ? { project_id: target.project_id } : {}),
    ...(target.stage_id ? { stage_id: target.stage_id } : {}),
  }
}

async function changeStreak(operation: 'restore' | 'create'): Promise<void> {
  if (streakBusy.value) return
  const target = selectedStreakTarget.value
  const request = targetRequest()
  if (!target || !request || !streakState.value) return
  const length = Math.max(1, Math.min(10_000, Math.trunc(normalizeNumber(streak.length, 1))))
  streak.length = length
  const newLength = operation === 'restore' ? target.length : length
  const action = operation === 'restore' ? t('восстановить') : t('создать')
  if (!window.confirm(t(`Подтвердите: ${action} стрик «${target.name}». Текущая длина: ${target.length}; новая длина: ${newLength}; писательский день: ${streakState.value.logical_day}.`))) return
  streakBusy.value = true
  error.value = null
  success.value = null
  try {
    const result = operation === 'restore'
      ? await gameApi.developerRestoreStreak(request)
      : await gameApi.developerCreateStreakSeries({ ...request, length })
    success.value = t(result.message ?? 'Стрик изменён.')
    emit('updated', result.state)
    await load()
  } catch (reason) {
    error.value = t(apiErrorMessage(reason))
  } finally {
    streakBusy.value = false
  }
}

function selectCategory(): void {
  grant.itemId = selectedItems.value[0]?.key ?? ''
}

async function saveProfile(): Promise<void> {
  if (saving.value) return
  normalizeForm()
  saving.value = true
  error.value = null
  success.value = null
  try {
    const result = await gameApi.updateDeveloperProfile({
      level: Math.trunc(form.level),
      health: form.health,
      coins: form.coins,
      exp: form.exp,
      test_date_enabled: form.testDateEnabled,
      // This is a logical writing date; preserve the value selected in the
      // local datetime input instead of shifting it to UTC.
      test_datetime: form.testDateEnabled ? form.testDatetime : null,
    })
    success.value = t(result.message ?? 'Настройки режима разработчика сохранены.')
    emit('updated', result.state)
    await load()
  } catch (reason) {
    error.value = t(apiErrorMessage(reason))
  } finally {
    saving.value = false
  }
}

async function grantItem(): Promise<void> {
  if (granting.value || !grant.category || !grant.itemId) return
  granting.value = true
  error.value = null
  success.value = null
  try {
    const result = await gameApi.grantDeveloperInventoryItem(
      grant.category, grant.itemId, Math.max(1, Math.trunc(grant.count)),
    )
    success.value = t(result.message ?? 'Предмет добавлен в инвентарь.')
    emit('updated', result.state)
    await load()
  } catch (reason) {
    error.value = t(apiErrorMessage(reason))
  } finally {
    granting.value = false
  }
}

async function requestTransfer(direction: 'real_to_test' | 'test_to_real'): Promise<void> {
  if (transferring.value) return
  const confirmation = direction === 'real_to_test'
    ? t('Текущие тестовые данные будут заменены снимком реальных данных. Перед заменой будет создана резервная копия. Продолжить?')
    : t('Реальные данные будут заменены тестовыми. Перед заменой будет создана проверенная резервная копия реальных данных. Продолжить?')
  if (!window.confirm(confirmation)) return
  transferring.value = true
  error.value = null
  success.value = null
  try {
    const result = await gameApi.requestProfileTransfer(direction)
    success.value = t(result.message)
  } catch (reason) {
    error.value = t(apiErrorMessage(reason))
  } finally {
    transferring.value = false
  }
}

watch(() => props.open, (open) => {
  if (open) void load()
}, { immediate: true })
</script>

<template>
  <IonModal :is-open="open" @did-dismiss="emit('close')">
    <IonHeader class="dialog-header">
      <div>
        <p class="eyebrow">{{ t('Инструменты тестирования') }}</p>
        <h2>{{ t('Режим разработчика') }}</h2>
      </div>
      <button class="icon-button" type="button" :aria-label="t('Закрыть')" @click="emit('close')">
        <IonIcon :icon="closeOutline" aria-hidden="true" />
      </button>
    </IonHeader>
    <IonContent class="ion-padding">
      <div v-if="loading" class="developer-loading"><IonSpinner /> {{ t('Загружаем данные…') }}</div>
      <form v-else class="developer-form" @submit.prevent="saveProfile">
        <p>{{ t('Эти инструменты доступны только в локальном запуске с тестовыми данными.') }}</p>
        <div class="developer-grid">
          <label>{{ t('Уровень') }}<input v-model.number="form.level" min="1" max="99" step="1" type="number" @blur="normalizeForm" /></label>
          <label>{{ t('Здоровье') }}<input v-model.number="form.health" min="0" :max="maxHealth" step="any" type="number" @blur="normalizeForm" /></label>
          <label>{{ t('Монеты') }}<input v-model.number="form.coins" min="0" step="any" type="number" @blur="normalizeForm" /></label>
          <label>{{ t('Опыт') }}<input v-model.number="form.exp" min="0" step="any" type="number" @blur="normalizeForm" /></label>
        </div>
        <label class="developer-toggle"><input v-model="form.testDateEnabled" type="checkbox" /> {{ t('Использовать тестовую дату') }}</label>
        <label v-if="form.testDateEnabled">{{ t('Тестовые дата и время') }}<input v-model="form.testDatetime" type="datetime-local" required /></label>
        <button class="nf-button nf-button--primary" :disabled="saving" type="submit">{{ saving ? t('Сохраняем…') : t('Сохранить') }}</button>

        <section class="developer-inventory" :aria-label="t('Выдать предмет')">
          <h3>{{ t('Выдать предмет из реестра') }}</h3>
          <p>{{ t('Выдача не списывает монеты и не учитывает обычные лимиты магазина.') }}</p>
          <label>{{ t('Категория') }}<select v-model="grant.category" @change="selectCategory"><option v-for="category in categories" :key="category.key" :value="category.key">{{ category.name }}</option></select></label>
          <label>{{ t('Предмет') }}<select v-model="grant.itemId"><option v-for="item in selectedItems" :key="item.key" :value="item.key">{{ item.name }}</option></select></label>
          <label>{{ t('Количество') }}<input v-model.number="grant.count" min="1" max="9999" type="number" /></label>
          <button class="nf-button" :disabled="granting" type="button" @click="grantItem">{{ granting ? t('Добавляем…') : t('Добавить в инвентарь') }}</button>
        </section>
        <section class="developer-inventory" :aria-label="t('Управление стриками')">
          <h3>{{ t('Управление стриками') }}</h3>
          <p>{{ t('Операции используют текущий писательский день и изменяют только canonical игровое состояние.') }}</p>
          <label>{{ t('Тип стрика') }}
            <select v-model="streak.type" @change="selectStreakType">
              <option value="global">{{ t('Глобальный') }}</option>
              <option value="project">{{ t('Проект') }}</option>
              <option value="stage">{{ t('Источник') }}</option>
            </select>
          </label>
          <label v-if="streak.type !== 'global'">{{ streak.type === 'project' ? t('Проект') : t('Источник') }}
            <select v-model="streak.targetId">
              <option v-for="target in visibleStreakTargets" :key="target.id" :value="target.id">{{ target.name }}</option>
            </select>
          </label>
          <div v-if="selectedStreakTarget" class="developer-streak-info">
            <span>{{ t('Статус') }}: {{ selectedStreakTarget.status }}</span>
            <span>{{ t('Длина') }}: {{ selectedStreakTarget.length }}</span>
            <span>{{ t('Максимум') }}: {{ selectedStreakTarget.max_length }}</span>
            <span>{{ t('Последний effective day') }}: {{ selectedStreakTarget.last_effective_day ?? '—' }}</span>
            <span>{{ t('Писательский день') }}: {{ streakState?.logical_day }}</span>
          </div>
          <button class="nf-button" :disabled="streakBusy || !selectedStreakTarget" type="button" @click="changeStreak('restore')">
            {{ streakBusy ? t('Изменяем…') : t('Восстановить стрик до текущего дня') }}
          </button>
          <label>{{ t('Количество дней') }}<input v-model.number="streak.length" min="1" max="10000" step="1" type="number" /></label>
          <button class="nf-button" :disabled="streakBusy || !selectedStreakTarget" type="button" @click="changeStreak('create')">
            {{ streakBusy ? t('Изменяем…') : t('Создать серию') }}
          </button>
        </section>
        <section v-if="testDataControlsAvailable" class="developer-inventory" :aria-label="t('Данные тестового режима')">
          <h3>{{ t('Данные тестового режима') }}</h3>
          <p>{{ t('Операция выполняется только после перезапуска, до открытия SQLite. Для текущего профиля создаётся резервная копия, затем проверенный снимок активируется атомарно.') }}</p>
          <button class="nf-button" :disabled="transferring" type="button" @click="requestTransfer('real_to_test')">
            {{ t('Обновить тестовые данные из реальных') }}
          </button>
          <button class="nf-button nf-button--danger" :disabled="transferring" type="button" @click="requestTransfer('test_to_real')">
            {{ t('Заменить реальные данные тестовыми') }}
          </button>
        </section>
        <p v-if="success" class="developer-success" role="status">{{ success }}</p>
        <p v-if="error" class="developer-error" role="alert">{{ error }}</p>
      </form>
    </IonContent>
  </IonModal>
</template>

<style scoped>
.developer-loading { display: flex; align-items: center; gap: var(--nf-space-2); min-height: 12rem; justify-content: center; }
.developer-form { display: grid; gap: var(--nf-space-3); max-width: 40rem; margin: 0 auto; }
.developer-form label { display: grid; gap: var(--nf-space-1); font-weight: 600; }
.developer-form input, .developer-form select { width: 100%; }
.developer-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--nf-space-2); }
.developer-toggle { display: flex !important; align-items: center; gap: var(--nf-space-2); }
.developer-toggle input { width: auto; }
.developer-inventory { display: grid; gap: var(--nf-space-2); padding-top: var(--nf-space-3); border-top: 1px solid var(--nf-color-border); }
.developer-inventory h3, .developer-inventory p { margin: 0; }
.developer-inventory p { color: var(--nf-color-text-muted); }
.developer-streak-info { display: grid; gap: var(--nf-space-1); color: var(--nf-color-text-muted); }
.developer-success { color: var(--nf-color-success); margin: 0; }
.developer-error { color: var(--nf-color-danger); margin: 0; }
@media (max-width: 32rem) { .developer-grid { grid-template-columns: 1fr; } }
</style>
