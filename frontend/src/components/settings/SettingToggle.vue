<script setup lang="ts">
defineProps<{
  id: string
  modelValue: boolean
  label: string
  description: string
  disabled?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

function update(event: Event): void {
  emit('update:modelValue', (event.target as HTMLInputElement).checked)
}
</script>

<template>
  <label class="setting-toggle" :for="id" :class="{ 'setting-toggle--disabled': disabled }">
    <span>
      <strong>{{ label }}</strong>
      <small>{{ description }}</small>
    </span>
    <input
      :id="id"
      type="checkbox"
      role="switch"
      :checked="modelValue"
      :disabled="disabled"
      @change="update"
    />
  </label>
</template>

<style scoped>
.setting-toggle {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: var(--nf-space-5);
  align-items: center;
  min-height: 4.25rem;
  padding: var(--nf-space-4) 0;
  border-bottom: 1px solid var(--nf-color-border);
  cursor: pointer;
}

.setting-toggle:last-child {
  border-bottom: 0;
}

.setting-toggle strong,
.setting-toggle small {
  display: block;
}

.setting-toggle strong {
  color: var(--nf-color-text);
  font-size: 0.98rem;
}

.setting-toggle small {
  margin-top: var(--nf-space-1);
  color: var(--nf-color-text-muted);
  font-size: 0.82rem;
  line-height: 1.45;
}

.setting-toggle input {
  width: 2.9rem;
  height: 1.65rem;
  margin: 0;
  appearance: none;
  border: 1px solid var(--nf-color-border);
  border-radius: var(--nf-radius-pill);
  background: var(--nf-color-surface-muted);
  cursor: pointer;
  transition: background-color 140ms ease;
}

.setting-toggle input::before {
  display: block;
  width: 1.15rem;
  height: 1.15rem;
  margin: 0.18rem;
  border-radius: 50%;
  background: var(--nf-color-text-muted);
  content: '';
  transition: transform 140ms ease, background-color 140ms ease;
}

.setting-toggle input:checked {
  border-color: var(--nf-color-primary);
  background: var(--nf-color-primary);
}

.setting-toggle input:checked::before {
  background: #fff;
  transform: translateX(1.22rem);
}

.setting-toggle--disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

:global(html[data-motion='reduced']) .setting-toggle input,
:global(html[data-motion='reduced']) .setting-toggle input::before {
  transition: none;
}
</style>
