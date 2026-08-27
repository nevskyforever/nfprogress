<script setup lang="ts">
import { computed, ref } from 'vue'

import { useLocaleStore } from '@/stores/locale'
import type { GameItem } from '@/types/game'

export interface CartLine { item: GameItem; count: number }
const props = defineProps<{ lines: CartLine[]; coins: number; canOpenCredit: boolean; creditAllowed: boolean; busy: boolean }>()
const emit = defineEmits<{ change: [itemId: string, count: number]; remove: [itemId: string]; clear: []; checkout: [useCredit: boolean, days: number] }>()
const locale = useLocaleStore(); const t = locale.translate
const expanded = ref(true); const creditDays = ref(30)
const total = computed(() => props.lines.reduce((sum, line) => sum + (line.item.price ?? 0) * line.count, 0))
const shortfall = computed(() => Math.max(0, total.value - props.coins))
function change(line: CartLine, delta: number): void { emit('change', line.item.id, Math.max(1, line.count + delta)) }
</script>

<template>
  <aside v-if="lines.length" class="shopping-cart" :aria-label="t('Корзина')">
    <button class="shopping-cart__summary" type="button" @click="expanded = !expanded">
      <span>🛒 {{ t('Корзина') }} · {{ lines.length }}</span><strong>{{ locale.formatNumber(total) }} {{ t('монет') }}</strong><span>{{ expanded ? '⌄' : '⌃' }}</span>
    </button>
    <div v-if="expanded" class="shopping-cart__content">
      <ul><li v-for="line in lines" :key="line.item.id"><span>{{ t(line.item.name) }}</span><div><button type="button" @click="change(line, -1)">−</button><b>×{{ line.count }}</b><button type="button" @click="change(line, 1)">+</button><button type="button" :aria-label="t('Удалить')" @click="emit('remove', line.item.id)">×</button></div></li></ul>
      <p v-if="shortfall" class="shopping-cart__shortfall">{{ t('Не хватает') }}: {{ locale.formatNumber(shortfall) }} {{ t('монет') }}</p>
      <p v-if="shortfall && !creditAllowed" class="shopping-cart__shortfall">{{ t('В корзине есть товары, недоступные для кредита.') }}</p>
      <label v-if="shortfall && canOpenCredit && creditAllowed">{{ t('Срок кредита, дней') }}<input v-model.number="creditDays" type="number" min="1" max="3650" /></label>
      <div class="shopping-cart__actions"><button type="button" class="nf-button nf-button--secondary" :disabled="busy" @click="emit('clear')">{{ t('Очистить') }}</button><button v-if="!shortfall" type="button" class="nf-button" :disabled="busy" @click="emit('checkout', false, creditDays)">{{ t('Оформить покупку') }}</button><button v-else type="button" class="nf-button" :disabled="busy || !canOpenCredit || !creditAllowed" @click="emit('checkout', true, creditDays)">{{ t('Оформить кредит и купить') }}</button></div>
    </div>
  </aside>
</template>

<style scoped>
.shopping-cart { position: fixed; z-index: 20; right: 1.25rem; bottom: 1.25rem; width: min(27rem, calc(100% - 2.5rem)); overflow: hidden; border: 1px solid var(--nf-color-border); border-radius: var(--nf-radius-xl, 1.5rem); background: var(--nf-color-surface-raised); box-shadow: var(--nf-shadow-card); }.shopping-cart__summary { width: 100%; display: flex; justify-content: space-between; gap: .75rem; padding: 1rem 1.25rem; border: 0; background: var(--nf-color-surface-raised); color: inherit; cursor: pointer; }.shopping-cart__content { padding: 0 1.25rem 1.25rem; }.shopping-cart ul { max-height: 12rem; margin: 0; padding: 0; overflow: auto; list-style: none; }.shopping-cart li { display: flex; justify-content: space-between; gap: .5rem; padding: .65rem 0; border-top: 1px solid var(--nf-color-border); }.shopping-cart li div { display: flex; gap: .35rem; align-items: center; }.shopping-cart li button { min-width: 1.7rem; border: 1px solid var(--nf-color-border); border-radius: .4rem; background: transparent; color: inherit; cursor: pointer; }.shopping-cart__shortfall { color: var(--ion-color-warning, #cc8613); }.shopping-cart label { display: grid; gap: .3rem; color: var(--nf-color-text-muted); }.shopping-cart input { max-width: 8rem; }.shopping-cart__actions { display: flex; justify-content: flex-end; gap: .5rem; margin-top: 1rem; }
</style>
