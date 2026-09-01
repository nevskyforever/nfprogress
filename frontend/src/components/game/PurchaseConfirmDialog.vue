<script setup lang="ts">
import { IonContent, IonModal } from '@ionic/vue'

import { useLocaleStore } from '@/stores/locale'
import type { GameItem } from '@/types/game'

defineProps<{ item: GameItem | null; count: number; busy: boolean }>()
const emit = defineEmits<{ confirm: []; cancel: []; addToCart: [] }>()
const locale = useLocaleStore()
const t = locale.translate
</script>

<template>
  <IonModal :is-open="item !== null" css-class="purchase-confirm-modal" :backdrop-dismiss="!busy" :keyboard-close="!busy" @did-dismiss="emit('cancel')">
    <IonContent class="purchase-confirm" :scroll-y="false">
      <section v-if="item" class="purchase-confirm__card" role="dialog" aria-modal="true" :aria-label="t('Подтверждение покупки')">
        <p>{{ t('Подтверждение покупки') }}</p>
        <h2>{{ t(item.name) }}</h2>
        <dl>
          <div><dt>{{ t('Количество') }}</dt><dd>×{{ count }}</dd></div>
          <div><dt>{{ t('Стоимость') }}</dt><dd>{{ locale.formatNumber((item.price ?? 0) * count) }} {{ t('монет') }}</dd></div>
        </dl>
        <div class="purchase-confirm__actions">
          <button class="nf-button nf-button--secondary" type="button" :disabled="busy" @click="emit('cancel')">{{ t('Отмена') }}</button>
          <button class="nf-button nf-button--secondary" type="button" :disabled="busy" @click="emit('addToCart')">{{ t('В корзину') }}</button>
          <button class="nf-button" type="button" :disabled="busy" @click="emit('confirm')">{{ t('Купить') }}</button>
        </div>
      </section>
    </IonContent>
  </IonModal>
</template>

<style>
.purchase-confirm-modal {
  --width: 100%;
  --height: 100%;
  --background: transparent;
  --box-shadow: none;
  --border-width: 0;
  --border-radius: 0;
}

.purchase-confirm-modal::part(content) {
  background: transparent;
}
</style>

<style scoped>
.purchase-confirm { --background: transparent; }
.purchase-confirm__card { width: min(30rem, calc(100% - 2rem)); margin: max(1rem, 20vh) auto; padding: 1.5rem; border: 1px solid var(--nf-color-border); border-radius: var(--nf-radius-xl, 1.5rem); background: var(--nf-color-surface-raised); box-shadow: var(--nf-shadow-card); }
.purchase-confirm__card > p, .purchase-confirm__card h2 { margin: 0; }.purchase-confirm__card > p { color: var(--nf-color-text-muted); }.purchase-confirm__card h2 { margin-top: .35rem; }
.purchase-confirm__card dl { display: grid; gap: .5rem; margin: 1.5rem 0; }.purchase-confirm__card dl div { display: flex; justify-content: space-between; }.purchase-confirm__card dt { color: var(--nf-color-text-muted); }.purchase-confirm__card dd { margin: 0; font-weight: 750; }
.purchase-confirm__actions { display: flex; flex-wrap: wrap; gap: .5rem; justify-content: flex-end; }
</style>
