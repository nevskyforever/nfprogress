<script setup lang="ts">
import { IonIcon, IonSpinner } from '@ionic/vue'

withDefaults(
  defineProps<{
    title: string
    message?: string
    icon?: string
    loading?: boolean
  }>(),
  {
    message: '',
    icon: undefined,
    loading: false,
  },
)
</script>

<template>
  <section class="state-panel" :aria-busy="loading || undefined">
    <IonSpinner v-if="loading" name="crescent" aria-hidden="true" />
    <IonIcon v-else-if="icon" class="state-panel__icon" :icon="icon" aria-hidden="true" />
    <h2>{{ title }}</h2>
    <p v-if="message">{{ message }}</p>
    <div v-if="$slots.default" class="state-panel__actions">
      <slot />
    </div>
  </section>
</template>

<style scoped>
.state-panel {
  display: grid;
  width: min(100%, 38rem);
  min-height: 17rem;
  margin: var(--nf-space-6) auto;
  padding: var(--nf-space-7) var(--nf-space-5);
  place-items: center;
  align-content: center;
  border: 1px dashed var(--nf-color-border);
  border-radius: var(--nf-radius-lg);
  color: var(--nf-color-text-muted);
  text-align: center;
}

.state-panel ion-spinner,
.state-panel__icon {
  width: 2.25rem;
  height: 2.25rem;
  margin-bottom: var(--nf-space-3);
  color: var(--nf-color-primary);
}

.state-panel h2 {
  margin: 0;
  color: var(--nf-color-text);
  font-family: var(--nf-font-serif);
  font-size: clamp(1.35rem, 3vw, 1.75rem);
}

.state-panel p {
  max-width: 31rem;
  margin: var(--nf-space-2) 0 0;
  line-height: 1.55;
}

.state-panel__actions {
  display: flex;
  gap: var(--nf-space-3);
  justify-content: center;
  margin-top: var(--nf-space-5);
}
</style>
