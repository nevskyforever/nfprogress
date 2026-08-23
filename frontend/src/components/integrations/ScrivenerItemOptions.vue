<script setup lang="ts">
import type { ScrivenerItem } from '@/types/integrations'

defineOptions({ name: 'ScrivenerItemOptions' })

withDefaults(
  defineProps<{
    items: ScrivenerItem[]
    level?: number
  }>(),
  { level: 0 },
)

function indentedTitle(title: string, level: number): string {
  return `${'\u00a0\u00a0'.repeat(level)}${level ? '↳ ' : ''}${title}`
}
</script>

<template>
  <template v-for="item in items" :key="item.id">
    <option :value="item.id">{{ indentedTitle(item.title, level) }}</option>
    <ScrivenerItemOptions
      v-if="item.children.length"
      :items="item.children"
      :level="level + 1"
    />
  </template>
</template>
