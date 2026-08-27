<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { IonContent, IonHeader, IonIcon, IonModal, IonSpinner } from '@ionic/vue'
import { closeOutline } from 'ionicons/icons'

import { apiErrorMessage } from '@/api/client'
import { gameApi } from '@/api/game'
import { useLocaleStore } from '@/stores/locale'
import type { DeveloperModeState, GameState } from '@/types/game'

const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{ close: []; updated: [state: GameState] }>()

const locale = useLocaleStore()
const t = locale.translate
const loading = ref(false)
const saving = ref(false)
const granting = ref(false)
const error = ref<string | null>(null)
const success = ref<string | null>(null)
const developerState = ref<DeveloperModeState | null>(null)
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

const categories = computed(() => developerState.value?.state.shop.categories ?? [])
const selectedItems = computed(
  () => categories.value.find((category) => category.key === grant.category)?.items ?? [],
)

function datetimeLocal(value: string | null): string {
  return value ? value.slice(0, 16) : new Date().toISOString().slice(0, 16)
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
    const state = await gameApi.developerState()
    developerState.value = state
    fill(state)
  } catch (reason) {
    error.value = t(apiErrorMessage(reason))
  } finally {
    loading.value = false
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
      test_datetime: form.testDateEnabled ? new Date(form.testDatetime).toISOString() : null,
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

watch(() => props.open, (open) => {
  if (open) void load()
})
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
.developer-success { color: var(--nf-color-success); margin: 0; }
.developer-error { color: var(--nf-color-danger); margin: 0; }
@media (max-width: 32rem) { .developer-grid { grid-template-columns: 1fr; } }
</style>
