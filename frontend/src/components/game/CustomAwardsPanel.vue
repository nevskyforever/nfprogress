<script setup lang="ts">
import { computed, ref } from 'vue'

import { useLocaleStore } from '@/stores/locale'
import type { CustomAwardsState } from '@/types/game'

defineProps<{
  awards: CustomAwardsState
  busy: boolean
}>()

const emit = defineEmits<{
  create: [name: string, price: number]
  update: [awardId: string, name: string, price: number]
  remove: [awardId: string]
  buy: [awardId: string, count: number]
  sell: [awardId: string, count: number]
  use: [awardId: string, count: number]
}>()

const locale = useLocaleStore()
const t = locale.translate
const awardName = ref('')
const awardPrice = ref(100)
const awardCount = ref(1)
const editingAwardId = ref<string | null>(null)
const editingName = ref('')
const editingPrice = ref(1)

const validAward = computed(() => awardName.value.trim().length > 0 && awardPrice.value > 0)

function positiveCount(): number {
  return Math.max(1, Math.min(1_000, Math.floor(awardCount.value || 1)))
}

function createAward(): void {
  if (!validAward.value) return
  emit('create', awardName.value.trim(), awardPrice.value)
  awardName.value = ''
}

function beginEditing(awardId: string, name: string, price: number): void {
  editingAwardId.value = awardId
  editingName.value = name
  editingPrice.value = price
}

function saveAward(): void {
  if (!editingAwardId.value || !editingName.value.trim() || editingPrice.value <= 0) return
  emit('update', editingAwardId.value, editingName.value.trim(), editingPrice.value)
  editingAwardId.value = null
}

function removeAward(awardId: string): void {
  if (window.confirm(t('Удалить награду из магазина? Купленные экземпляры сохранятся.'))) {
    emit('remove', awardId)
  }
}
</script>

<template>
  <form class="award-form" @submit.prevent="createAward">
    <label>
      <span>{{ t('Название награды') }}</span>
      <input v-model="awardName" maxlength="300" required :disabled="busy" />
    </label>
    <label>
      <span>{{ t('Цена') }}</span>
      <input v-model.number="awardPrice" type="number" min="0.1" step="0.1" required :disabled="busy" />
    </label>
    <button class="nf-button" type="submit" :disabled="busy || !validAward">
      {{ t('Создать награду') }}
    </button>
    <label class="count-field">
      <span>{{ t('Количество для действия') }}</span>
      <input v-model.number="awardCount" type="number" min="1" max="1000" step="1" />
    </label>
  </form>

  <p v-if="awards.items.length === 0" class="empty-copy">
    {{ t('Создайте личную награду — например, прогулку или любимый десерт.') }}
  </p>

  <div v-else class="award-grid">
    <article v-for="award in awards.items" :key="award.id" class="award-card">
      <template v-if="editingAwardId === award.id">
        <label>
          <span>{{ t('Название награды') }}</span>
          <input v-model="editingName" maxlength="300" />
        </label>
        <label>
          <span>{{ t('Цена') }}</span>
          <input v-model.number="editingPrice" type="number" min="0.1" step="0.1" />
        </label>
        <div class="button-row">
          <button class="nf-button" type="button" :disabled="busy" @click="saveAward">
            {{ t('Сохранить') }}
          </button>
          <button
            class="nf-button nf-button--secondary"
            type="button"
            @click="editingAwardId = null"
          >
            {{ t('Отмена') }}
          </button>
        </div>
      </template>
      <template v-else>
        <header>
          <div>
            <h3>{{ award.name }}</h3>
            <span>×{{ award.count }}</span>
          </div>
          <strong>{{ locale.formatNumber(award.price) }} {{ t('монет') }}</strong>
        </header>
        <p>{{ t(award.description) }}</p>
        <div class="button-row">
          <button
            v-if="award.available_in_shop"
            class="nf-button"
            type="button"
            :disabled="busy || !award.can_buy"
            @click="emit('buy', award.id, positiveCount())"
          >
            {{ t('Купить') }}
          </button>
          <button
            v-if="award.count > 0"
            class="nf-button nf-button--secondary"
            type="button"
            :disabled="busy || positiveCount() > award.count"
            @click="emit('use', award.id, positiveCount())"
          >
            {{ t('Использовать') }}
          </button>
          <button
            v-if="award.sellable && award.count > 0"
            class="nf-button nf-button--secondary"
            type="button"
            :disabled="busy || positiveCount() > award.count"
            @click="emit('sell', award.id, positiveCount())"
          >
            {{ t('Продать') }}
          </button>
          <button
            class="nf-button nf-button--quiet"
            type="button"
            :disabled="busy"
            @click="beginEditing(award.id, award.name, award.price)"
          >
            {{ t('Изменить') }}
          </button>
          <button
            v-if="award.available_in_shop"
            class="nf-button danger-button"
            type="button"
            :disabled="busy"
            @click="removeAward(award.id)"
          >
            {{ t('Удалить') }}
          </button>
        </div>
      </template>
    </article>
  </div>
</template>

<style scoped>
.award-form {
  display: grid;
  grid-template-columns: minmax(12rem, 2fr) minmax(7rem, 1fr) auto minmax(8rem, 1fr);
  gap: var(--nf-space-3);
  align-items: end;
  margin: var(--nf-space-5) 0;
  padding: var(--nf-space-4);
  border-radius: var(--nf-radius-md);
  background: var(--nf-color-surface-muted);
}

label {
  display: grid;
  gap: var(--nf-space-1);
  color: var(--nf-color-text-muted);
  font-size: 0.8rem;
  font-weight: 700;
}

input {
  width: 100%;
  min-height: 2.75rem;
  padding: 0.6rem 0.7rem;
  border: 1px solid var(--nf-color-border);
  border-radius: var(--nf-radius-sm);
  background: var(--nf-color-surface-raised);
  color: var(--nf-color-text);
}

.award-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--nf-space-3);
}

.award-card {
  display: grid;
  gap: var(--nf-space-3);
  padding: var(--nf-space-4);
  border: 1px solid var(--nf-color-border);
  border-radius: var(--nf-radius-md);
  background: var(--nf-color-surface-raised);
}

.award-card header,
.award-card header > div,
.button-row {
  display: flex;
  gap: var(--nf-space-3);
  align-items: center;
}

.award-card header {
  justify-content: space-between;
}

.award-card h3,
.award-card p,
.empty-copy {
  margin: 0;
}

.award-card h3 {
  font-family: var(--nf-font-serif);
}

.award-card p,
.empty-copy {
  color: var(--nf-color-text-muted);
  line-height: 1.45;
}

.award-card header span {
  color: var(--nf-color-primary);
  font-weight: 750;
}

.button-row {
  flex-wrap: wrap;
}

.danger-button {
  border-color: color-mix(in srgb, var(--nf-color-danger) 55%, transparent);
  background: transparent;
  color: var(--nf-color-danger);
}

.danger-button:hover:not(:disabled) {
  background: color-mix(in srgb, var(--nf-color-danger) 12%, transparent);
}

@media (max-width: 70rem) {
  .award-form {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 44rem) {
  .award-form,
  .award-grid {
    grid-template-columns: 1fr;
  }
}
</style>
