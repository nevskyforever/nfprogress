<script setup lang="ts">
import BankPanel from '@/components/game/BankPanel.vue'
import CustomAwardsPanel from '@/components/game/CustomAwardsPanel.vue'
import { useLocaleStore } from '@/stores/locale'
import type {
  BankProductRequest,
  BankState,
  CustomAwardsState,
  GameCommandResponse,
} from '@/types/game'

defineProps<{
  awards: CustomAwardsState
  bank: BankState
  preview: GameCommandResponse['result']
  busy: boolean
  view: 'awards' | 'bank'
}>()

const emit = defineEmits<{
  createAward: [name: string, price: number]
  updateAward: [awardId: string, name: string, price: number]
  deleteAward: [awardId: string]
  buyAward: [awardId: string, count: number]
  sellAward: [awardId: string, count: number]
  useAward: [awardId: string, count: number]
  previewBank: [payload: BankProductRequest]
  openCredit: [amount: number, days: number]
  openDeposit: [amount: number, days: number, allowInterestWithdrawal: boolean]
  processBank: []
  payCredit: []
  partialRepay: [amount: number]
  repayCredit: []
  topUpDeposit: [amount: number]
  withdrawDeposit: [allowEarly: boolean]
  withdrawInterest: []
}>()

const locale = useLocaleStore()
const t = locale.translate
</script>

<template>
  <section class="game-panel" :aria-labelledby="'rewards-bank-title'">
    <header class="panel-heading">
      <div>
        <p>{{ t('Личные цели и экономика') }}</p>
        <h2 id="rewards-bank-title">{{ view === 'awards' ? t('Награды') : t('Банк') }}</h2>
      </div>
    </header>

    <CustomAwardsPanel
      v-if="view === 'awards'"
      :awards="awards"
      :busy="busy"
      @create="(name, price) => emit('createAward', name, price)"
      @update="(id, name, price) => emit('updateAward', id, name, price)"
      @remove="(id) => emit('deleteAward', id)"
      @buy="(id, count) => emit('buyAward', id, count)"
      @sell="(id, count) => emit('sellAward', id, count)"
      @use="(id, count) => emit('useAward', id, count)"
    />

    <BankPanel
      v-else
      :bank="bank"
      :preview="preview"
      :busy="busy"
      @preview="(payload) => emit('previewBank', payload)"
      @open-credit="(amount, days) => emit('openCredit', amount, days)"
      @open-deposit="(amount, days, interest) => emit('openDeposit', amount, days, interest)"
      @process="emit('processBank')"
      @pay-credit="emit('payCredit')"
      @partial-repay="(amount) => emit('partialRepay', amount)"
      @repay-credit="emit('repayCredit')"
      @top-up-deposit="(amount) => emit('topUpDeposit', amount)"
      @withdraw-deposit="(early) => emit('withdrawDeposit', early)"
      @withdraw-interest="emit('withdrawInterest')"
    />
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

.panel-heading {
  display: flex;
  gap: var(--nf-space-3);
  align-items: center;
  justify-content: space-between;
}

.panel-heading p,
.panel-heading h2 {
  margin: 0;
}

.panel-heading p {
  color: var(--nf-color-accent);
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.panel-heading h2 {
  font-family: var(--nf-font-serif);
}

.view-switch {
  display: inline-flex;
  padding: var(--nf-space-1);
  border: 1px solid var(--nf-color-border);
  border-radius: var(--nf-radius-pill);
  background: var(--nf-color-surface-muted);
}

.view-switch button {
  min-height: 2.4rem;
  padding: 0.45rem 0.75rem;
  border: 0;
  border-radius: var(--nf-radius-pill);
  background: transparent;
  color: var(--nf-color-text-muted);
  cursor: pointer;
}

.view-switch button.active {
  background: var(--nf-color-surface-raised);
  color: var(--nf-color-primary);
  font-weight: 750;
}

@media (max-width: 44rem) {
  .game-panel {
    padding: var(--nf-space-4);
  }

  .panel-heading {
    align-items: stretch;
    flex-direction: column;
  }

  .view-switch {
    width: 100%;
  }

  .view-switch button {
    flex: 1;
  }
}
</style>
