<script setup lang="ts">
import type { HelpSection } from '@/types/content'

defineOptions({ name: 'HelpTree' })

defineProps<{
  sections: HelpSection[]
  selectedKey: string | null
}>()

const emit = defineEmits<{
  select: [section: HelpSection]
}>()
</script>

<template>
  <ul class="help-tree">
    <li v-for="section in sections" :key="section.key">
      <button
        type="button"
        :class="{ 'help-tree__button--active': section.key === selectedKey }"
        :aria-current="section.key === selectedKey ? 'page' : undefined"
        @click="emit('select', section)"
      >
        {{ section.title }}
      </button>
      <HelpTree
        v-if="section.children.length"
        :sections="section.children"
        :selected-key="selectedKey"
        @select="emit('select', $event)"
      />
    </li>
  </ul>
</template>

<style scoped>
.help-tree {
  display: grid;
  gap: var(--nf-space-1);
  padding: 0;
  margin: 0;
  list-style: none;
}

.help-tree .help-tree {
  padding-left: var(--nf-space-4);
  margin: var(--nf-space-1) 0 var(--nf-space-2);
  border-left: 1px solid var(--nf-color-border);
}

.help-tree__button {
  width: 100%;
}

button {
  width: 100%;
  min-height: 2.6rem;
  padding: var(--nf-space-2) var(--nf-space-3);
  border: 0;
  border-radius: var(--nf-radius-sm);
  background: transparent;
  color: var(--nf-color-text-muted);
  font-size: 0.88rem;
  line-height: 1.35;
  text-align: left;
  cursor: pointer;
}

button:hover,
.help-tree__button--active {
  background: var(--nf-color-primary-soft);
  color: var(--nf-color-primary);
}

.help-tree__button--active {
  font-weight: 750;
}
</style>
