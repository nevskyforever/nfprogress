<script setup lang="ts">
import { computed, ref } from 'vue'

import { useLocaleStore } from '@/stores/locale'
import type { BankProductRequest, BankState, GameCommandResponse } from '@/types/game'

const props = defineProps<{
  bank: BankState
  preview: GameCommandResponse['result']
  busy: boolean
}>()

const emit = defineEmits<{
  preview: [payload: BankProductRequest]
  openCredit: [amount: number, days: number]
  openDeposit: [amount: number, days: number, allowInterestWithdrawal: boolean]
  process: []
  payCredit: []
  partialRepay: [amount: number]
  repayCredit: []
  topUpDeposit: [amount: number]
  withdrawDeposit: [allowEarly: boolean]
  withdrawInterest: []
}>()

const locale = useLocaleStore()
const t = locale.translate
const productType = ref<'credit' | 'deposit'>('deposit')
const amount = ref(100)
const days = ref(7)
const allowInterestWithdrawal = ref(false)
const transactionAmount = ref(50)

const validProduct = computed(() => amount.value > 0 && days.value > 0 && days.value <= 3_650)

function bankRequest(): BankProductRequest {
  return {
    product_type: productType.value,
    amount: amount.value,
    days: Math.floor(days.value),
    allow_interest_withdrawal: productType.value === 'deposit' && allowInterestWithdrawal.value,
  }
}

function openProduct(): void {
  if (!validProduct.value) return
  if (productType.value === 'credit') {
    emit('openCredit', amount.value, Math.floor(days.value))
  } else {
    emit('openDeposit', amount.value, Math.floor(days.value), allowInterestWithdrawal.value)
  }
}

function previewNumber(key: string): number | null {
  const value = props.preview?.[key]
  return typeof value === 'number' ? value : null
}

function confirmFullRepayment(): void {
  if (window.confirm(t('Полностью погасить активный кредит?'))) emit('repayCredit')
}

function confirmEarlyWithdrawal(): void {
  if (window.confirm(t('Забрать вклад досрочно? Начисленные проценты могут быть потеряны.'))) {
    emit('withdrawDeposit', true)
  }
}
</script>

<template>
  <div class="bank-summary">
    <article>
      <span>{{ t('Кредитный рейтинг') }}</span>
      <strong>{{ bank.credit_score ?? '—' }}</strong>
    </article>
    <article>
      <span>{{ t('Кредитный лимит') }}</span>
      <strong>{{ bank.credit_limit === undefined ? '—' : locale.formatNumber(bank.credit_limit) }}</strong>
    </article>
    <article>
      <span>{{ t('Ставка кредита') }}</span>
      <strong>{{ bank.credit_rate === undefined ? '—' : `${locale.formatNumber(bank.credit_rate)}%` }}</strong>
    </article>
    <article>
      <span>{{ t('Ставка вклада') }}</span>
      <strong>{{ bank.deposit_rate === undefined ? '—' : `${locale.formatNumber(bank.deposit_rate)}%` }}</strong>
    </article>
  </div>

  <form v-if="!bank.credit || !bank.deposit" class="bank-form" @submit.prevent="openProduct">
    <label>
      <span>{{ t('Продукт') }}</span>
      <select v-model="productType">
        <option value="deposit" :disabled="!bank.can_open_deposit">{{ t('Вклад') }}</option>
        <option value="credit" :disabled="!bank.can_open_credit">{{ t('Кредит') }}</option>
      </select>
    </label>
    <label>
      <span>{{ t('Сумма') }}</span>
      <input v-model.number="amount" type="number" min="0.1" step="0.1" />
    </label>
    <label>
      <span>{{ t('Срок, дней') }}</span>
      <input v-model.number="days" type="number" min="1" max="3650" step="1" />
    </label>
    <label v-if="productType === 'deposit'" class="checkbox-label">
      <input v-model="allowInterestWithdrawal" type="checkbox" />
      <span>{{ t('Разрешить вывод процентов') }}</span>
    </label>
    <div class="button-row bank-form-actions">
      <button
        class="nf-button nf-button--secondary"
        type="button"
        :disabled="busy || !validProduct"
        @click="emit('preview', bankRequest())"
      >
        {{ t('Рассчитать') }}
      </button>
      <button
        class="nf-button"
        type="submit"
        :disabled="
          busy ||
          !validProduct ||
          (productType === 'credit' ? !bank.can_open_credit : !bank.can_open_deposit)
        "
      >
        {{ productType === 'credit' ? t('Открыть кредит') : t('Открыть вклад') }}
      </button>
    </div>
  </form>

  <article v-if="preview" class="preview-card" aria-live="polite">
    <h3>{{ t('Предварительный расчёт') }}</h3>
    <dl>
      <div><dt>{{ t('Сумма') }}</dt><dd>{{ locale.formatNumber(previewNumber('amount') ?? 0) }}</dd></div>
      <div><dt>{{ t('Ставка') }}</dt><dd>{{ locale.formatNumber(previewNumber('rate') ?? 0) }}%</dd></div>
      <div><dt>{{ t('Проценты') }}</dt><dd>{{ locale.formatNumber(previewNumber('interest') ?? 0) }}</dd></div>
      <div><dt>{{ t('Итого') }}</dt><dd>{{ locale.formatNumber(previewNumber('total') ?? 0) }}</dd></div>
    </dl>
  </article>

  <div class="bank-products">
    <article v-if="bank.credit" class="product-card">
      <header>
        <h3>{{ t('Активный кредит') }}</h3>
        <span>{{ t(bank.credit.status) }}</span>
      </header>
      <dl>
        <div><dt>{{ t('Остаток') }}</dt><dd>{{ locale.formatNumber(bank.credit.remaining) }}</dd></div>
        <div><dt>{{ t('Ежедневный платёж') }}</dt><dd>{{ locale.formatNumber(bank.credit.daily_payment) }}</dd></div>
        <div><dt>{{ t('Дата возврата') }}</dt><dd>{{ locale.formatDate(bank.credit.return_date) }}</dd></div>
        <div><dt>{{ t('Просрочка, дней') }}</dt><dd>{{ bank.credit.overdue_days }}</dd></div>
      </dl>
      <label>
        <span>{{ t('Сумма частичного погашения') }}</span>
        <input v-model.number="transactionAmount" type="number" min="0.1" step="0.1" />
      </label>
      <div class="button-row">
        <button class="nf-button" type="button" :disabled="busy" @click="emit('payCredit')">
          {{ t('Внести платёж') }}
        </button>
        <button
          class="nf-button nf-button--secondary"
          type="button"
          :disabled="busy || transactionAmount <= 0"
          @click="emit('partialRepay', transactionAmount)"
        >
          {{ t('Погасить частично') }}
        </button>
        <button
          class="nf-button nf-button--secondary"
          type="button"
          :disabled="busy"
          @click="confirmFullRepayment"
        >
          {{ t('Погасить полностью') }}
        </button>
      </div>
    </article>

    <article v-if="bank.deposit" class="product-card">
      <header>
        <h3>{{ t('Активный вклад') }}</h3>
        <span>{{ t(bank.deposit.status) }}</span>
      </header>
      <dl>
        <div><dt>{{ t('Основная сумма') }}</dt><dd>{{ locale.formatNumber(bank.deposit.principal) }}</dd></div>
        <div><dt>{{ t('Начисленные проценты') }}</dt><dd>{{ locale.formatNumber(bank.deposit.interest) }}</dd></div>
        <div><dt>{{ t('Доступные проценты') }}</dt><dd>{{ locale.formatNumber(bank.deposit.available_interest) }}</dd></div>
        <div><dt>{{ t('Дата возврата') }}</dt><dd>{{ locale.formatDate(bank.deposit.return_date) }}</dd></div>
      </dl>
      <label>
        <span>{{ t('Сумма пополнения') }}</span>
        <input v-model.number="transactionAmount" type="number" min="0.1" step="0.1" />
      </label>
      <div class="button-row">
        <button
          class="nf-button"
          type="button"
          :disabled="busy || transactionAmount <= 0"
          @click="emit('topUpDeposit', transactionAmount)"
        >
          {{ t('Пополнить') }}
        </button>
        <button
          v-if="bank.deposit.allow_interest_withdrawal"
          class="nf-button nf-button--secondary"
          type="button"
          :disabled="busy || bank.deposit.available_interest <= 0"
          @click="emit('withdrawInterest')"
        >
          {{ t('Вывести проценты') }}
        </button>
        <button
          class="nf-button nf-button--secondary"
          type="button"
          :disabled="busy"
          @click="emit('withdrawDeposit', false)"
        >
          {{ t('Забрать в срок') }}
        </button>
        <button
          class="nf-button danger-button"
          type="button"
          :disabled="busy"
          @click="confirmEarlyWithdrawal"
        >
          {{ t('Забрать досрочно') }}
        </button>
      </div>
    </article>
  </div>

  <button
    class="nf-button nf-button--quiet process-button"
    type="button"
    :disabled="busy"
    @click="emit('process')"
  >
    {{ t('Проверить банковские события') }}
  </button>
</template>

<style scoped>
.bank-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(8rem, 1fr));
  gap: var(--nf-space-3);
  margin-top: var(--nf-space-5);
}

.bank-summary article {
  display: grid;
  gap: var(--nf-space-2);
  padding: var(--nf-space-4);
  border-radius: var(--nf-radius-md);
  background: var(--nf-color-surface-muted);
}

.bank-summary span,
dt {
  color: var(--nf-color-text-muted);
  font-size: 0.8rem;
}

.bank-summary strong {
  font-family: var(--nf-font-serif);
  font-size: 1.4rem;
}

.bank-form {
  display: grid;
  grid-template-columns: repeat(3, minmax(8rem, 1fr)) minmax(11rem, 1.2fr);
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

input,
select {
  width: 100%;
  min-height: 2.75rem;
  padding: 0.6rem 0.7rem;
  border: 1px solid var(--nf-color-border);
  border-radius: var(--nf-radius-sm);
  background: var(--nf-color-surface-raised);
  color: var(--nf-color-text);
}

.checkbox-label {
  display: flex;
  gap: var(--nf-space-2);
  align-items: center;
  min-height: 2.75rem;
}

.checkbox-label input {
  width: 1.2rem;
  min-height: 1.2rem;
}

.button-row {
  display: flex;
  gap: var(--nf-space-3);
  align-items: center;
  flex-wrap: wrap;
}

.bank-form-actions {
  grid-column: 1 / -1;
}

.preview-card,
.product-card {
  display: grid;
  gap: var(--nf-space-3);
  padding: var(--nf-space-4);
  border: 1px solid var(--nf-color-border);
  border-radius: var(--nf-radius-md);
  background: var(--nf-color-surface-raised);
}

.preview-card {
  margin-bottom: var(--nf-space-4);
  background: var(--nf-color-primary-soft);
}

.preview-card h3,
.product-card h3 {
  margin: 0;
  font-family: var(--nf-font-serif);
}

.preview-card dl,
.product-card dl {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--nf-space-3);
  margin: 0;
}

.preview-card dl div,
.product-card dl div {
  display: grid;
  gap: var(--nf-space-1);
}

dd {
  margin: 0;
  font-weight: 750;
}

.bank-products {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--nf-space-3);
}

.product-card header {
  display: flex;
  gap: var(--nf-space-3);
  align-items: center;
  justify-content: space-between;
}

.product-card header span {
  color: var(--nf-color-primary);
  font-size: 0.8rem;
  font-weight: 750;
}

.danger-button {
  border-color: color-mix(in srgb, var(--nf-color-danger) 55%, transparent);
  background: transparent;
  color: var(--nf-color-danger);
}

.danger-button:hover:not(:disabled) {
  background: color-mix(in srgb, var(--nf-color-danger) 12%, transparent);
}

.process-button {
  margin-top: var(--nf-space-4);
}

@media (max-width: 70rem) {
  .bank-form,
  .bank-summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 44rem) {
  .bank-form,
  .bank-products,
  .bank-summary,
  .preview-card dl,
  .product-card dl {
    grid-template-columns: 1fr;
  }

  .bank-form-actions {
    grid-column: auto;
  }
}
</style>
