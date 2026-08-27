<script setup lang="ts">
import { IonIcon } from '@ionic/vue'
import { cashOutline, flameOutline, heartOutline, ribbonOutline, sparklesOutline } from 'ionicons/icons'

import { useLocaleStore } from '@/stores/locale'
import type { GameProfile } from '@/types/game'

defineProps<{ profile: GameProfile }>()

const locale = useLocaleStore()
const t = locale.translate
</script>

<template>
  <aside class="character-quick-stats" :aria-label="t('Параметры персонажа')">
    <span class="quick-stat quick-stat--level" :title="t('Уровень')" :aria-label="`${t('Уровень')}: ${profile.level}`">
      <IonIcon :icon="ribbonOutline" aria-hidden="true" />{{ profile.level }}
    </span>
    <span class="quick-stat quick-stat--coins" :title="t('Монеты')" :aria-label="`${t('Монеты')}: ${locale.formatNumber(profile.coins)}`">
      <IonIcon :icon="cashOutline" aria-hidden="true" />{{ locale.formatNumber(profile.coins) }}
    </span>
    <span class="quick-stat quick-stat--health" :title="t('Здоровье')" :aria-label="`${t('Здоровье')}: ${profile.health}/${profile.max_health}`">
      <IonIcon :icon="heartOutline" aria-hidden="true" />{{ locale.formatNumber(profile.health) }}/{{ locale.formatNumber(profile.max_health) }}
    </span>
    <span class="quick-stat quick-stat--inspiration" :title="t('Вдохновение')" :aria-label="`${t('Вдохновение')}: ${profile.inspiration}/${profile.max_inspiration}`">
      <IonIcon :icon="sparklesOutline" aria-hidden="true" />{{ profile.inspiration }}/{{ profile.max_inspiration }}
    </span>
    <span class="quick-stat quick-stat--streak" :title="t('Стрик сессий')" :aria-label="`${t('Стрик сессий')}: ${profile.writing_session_streak}`">
      <IonIcon :icon="flameOutline" aria-hidden="true" />{{ profile.writing_session_streak }}
    </span>
  </aside>
</template>

<style scoped>
.character-quick-stats { position: sticky; z-index: 4; top: calc(env(safe-area-inset-top) + 4rem); display: flex; width: fit-content; max-width: 100%; margin: 0 auto var(--nf-space-3); overflow-x: auto; border: 1px solid color-mix(in srgb, var(--nf-color-border) 86%, transparent); border-radius: var(--nf-radius-pill); background: color-mix(in srgb, var(--nf-color-surface-raised) 92%, transparent); box-shadow: 0 .6rem 1.5rem color-mix(in srgb, var(--nf-color-canvas) 28%, transparent); backdrop-filter: blur(12px); }
.quick-stat { display: inline-flex; flex: 0 0 auto; gap: .35rem; align-items: center; min-height: 2.35rem; padding: .45rem .7rem; border-right: 1px solid var(--nf-color-border); color: var(--nf-color-text); font-size: .82rem; font-variant-numeric: tabular-nums; font-weight: 750; white-space: nowrap; }.quick-stat ion-icon { width: 1rem; height: 1rem; stroke-width: 2.25; }.quick-stat--level ion-icon { color: var(--nf-color-primary); }.quick-stat--coins ion-icon { color: #d69c18; }.quick-stat--health ion-icon { color: var(--nf-color-danger); }.quick-stat--inspiration ion-icon { color: var(--nf-color-accent); }.quick-stat--streak ion-icon { color: #e57932; }.quick-stat:last-child { border-right: 0; }
@media (max-width: 44rem) { .quick-stat { padding-inline: .55rem; } }
</style>
