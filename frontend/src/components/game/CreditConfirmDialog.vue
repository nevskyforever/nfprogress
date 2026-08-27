<script setup lang="ts">
import { IonContent, IonModal } from '@ionic/vue'
import { useLocaleStore } from '@/stores/locale'
import type { GameCommandResponse } from '@/types/game'

defineProps<{
  preview: GameCommandResponse['result']
  amount: number
  days: number
  busy: boolean
}>()
const emit = defineEmits<{ confirm: []; cancel: [] }>()
const locale = useLocaleStore()
const t = locale.translate
function numberValue(value: unknown): number {
  return typeof value === 'number' ? value : 0
}
</script>

<template>
  <IonModal :is-open="preview !== null" css-class="credit-confirm-modal" :backdrop-dismiss="!busy" :keyboard-close="!busy">
    <IonContent class="credit-confirm"><section class="credit-confirm__card" role="dialog" aria-modal="true">
      <p>{{ t('Параметры кредита') }}</p><h2>{{ t('Кредит для корзины') }}</h2>
      <dl>
        <div><dt>{{ t('Сумма') }}</dt><dd>{{ locale.formatNumber(amount) }} {{ t('монет') }}</dd></div>
        <div><dt>{{ t('Срок') }}</dt><dd>{{ days }} {{ t('дн.') }}</dd></div>
        <div><dt>{{ t('Ежедневный платёж') }}</dt><dd>{{ locale.formatNumber(numberValue(preview?.daily_payment)) }} {{ t('монет') }}</dd></div>
        <div><dt>{{ t('Проценты') }}</dt><dd>{{ locale.formatNumber(numberValue(preview?.interest)) }} {{ t('монет') }}</dd></div>
        <div><dt>{{ t('Итого к возврату') }}</dt><dd>{{ locale.formatNumber(numberValue(preview?.total)) }} {{ t('монет') }}</dd></div>
      </dl>
      <div class="credit-confirm__actions"><button class="nf-button nf-button--secondary" type="button" :disabled="busy" @click="emit('cancel')">{{ t('Отмена') }}</button><button class="nf-button" type="button" :disabled="busy" @click="emit('confirm')">{{ t('Оформить кредит и купить') }}</button></div>
    </section></IonContent>
  </IonModal>
</template>

<style scoped>
.credit-confirm { --background: transparent; }.credit-confirm__card { width: min(30rem, calc(100% - 2rem)); margin: 15vh auto; padding: 1.5rem; border: 1px solid var(--nf-color-border); border-radius: var(--nf-radius-xl, 1.5rem); background: var(--nf-color-surface-raised); box-shadow: var(--nf-shadow-card); }.credit-confirm__card > p, .credit-confirm__card h2 { margin: 0; }.credit-confirm__card > p { color: var(--nf-color-text-muted); }.credit-confirm__card h2 { margin-top: .35rem; }.credit-confirm__card dl { display: grid; gap: .5rem; margin: 1.5rem 0; }.credit-confirm__card dl div { display: flex; justify-content: space-between; gap: 1rem; }.credit-confirm__card dt { color: var(--nf-color-text-muted); }.credit-confirm__card dd { margin: 0; font-weight: 750; }.credit-confirm__actions { display: flex; justify-content: flex-end; gap: .5rem; }
</style>
