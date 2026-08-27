<script setup lang="ts">
import { useLocaleStore } from '@/stores/locale'
import type { GameProfile } from '@/types/game'

defineProps<{ profile: GameProfile }>()

const locale = useLocaleStore()
const t = locale.translate
</script>

<template>
  <aside class="character-quick-stats" :aria-label="t('Параметры персонажа')">
    <span class="quick-stat" :title="t('Уровень')" :aria-label="`${t('Уровень')}: ${profile.level}`">
      <span aria-hidden="true">✦</span>{{ profile.level }}
    </span>
    <span class="quick-stat" :title="t('Монеты')" :aria-label="`${t('Монеты')}: ${locale.formatNumber(profile.coins)}`">
      <span aria-hidden="true">🪙</span>{{ locale.formatNumber(profile.coins) }}
    </span>
    <span class="quick-stat" :title="t('Здоровье')" :aria-label="`${t('Здоровье')}: ${profile.health}/${profile.max_health}`">
      <span aria-hidden="true">♥</span>{{ locale.formatNumber(profile.health) }}/{{ locale.formatNumber(profile.max_health) }}
    </span>
    <span class="quick-stat" :title="t('Вдохновение')" :aria-label="`${t('Вдохновение')}: ${profile.inspiration}/${profile.max_inspiration}`">
      <span aria-hidden="true">✧</span>{{ profile.inspiration }}/{{ profile.max_inspiration }}
    </span>
    <span class="quick-stat" :title="t('Стрик сессий')" :aria-label="`${t('Стрик сессий')}: ${profile.writing_session_streak}`">
      <span aria-hidden="true">🔥</span>{{ profile.writing_session_streak }}
    </span>
  </aside>
</template>

<style scoped>
.character-quick-stats { position: sticky; z-index: 4; top: calc(env(safe-area-inset-top) + 4rem); display: flex; width: fit-content; max-width: 100%; margin: 0 0 var(--nf-space-3) auto; overflow-x: auto; border: 1px solid color-mix(in srgb, var(--nf-color-border) 86%, transparent); border-radius: var(--nf-radius-pill); background: color-mix(in srgb, var(--nf-color-surface-raised) 92%, transparent); box-shadow: 0 .6rem 1.5rem color-mix(in srgb, var(--nf-color-canvas) 28%, transparent); backdrop-filter: blur(12px); }
.quick-stat { display: inline-flex; flex: 0 0 auto; gap: .35rem; align-items: center; min-height: 2.35rem; padding: .45rem .7rem; border-right: 1px solid var(--nf-color-border); color: var(--nf-color-text); font-size: .82rem; font-variant-numeric: tabular-nums; font-weight: 750; white-space: nowrap; }
.quick-stat:first-child { color: var(--nf-color-primary); }.quick-stat:nth-child(3) span { color: var(--nf-color-danger); }.quick-stat:nth-child(4) span { color: var(--nf-color-accent); }.quick-stat:last-child { border-right: 0; }
@media (max-width: 44rem) { .character-quick-stats { margin-left: auto; } .quick-stat { padding-inline: .55rem; } }
</style>
