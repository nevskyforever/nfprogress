<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

export interface ContextAction {
  id: string
  label: string
  danger?: boolean
  separator?: boolean
  children?: ContextAction[]
}

const props = defineProps<{
  open: boolean
  x: number
  y: number
  label: string
  actions: ContextAction[]
}>()
const emit = defineEmits<{ close: []; select: [action: ContextAction] }>()
const menu = ref<HTMLElement | null>(null)
const openSubmenu = ref<ContextAction | null>(null)
const submenuPosition = ref({ x: 0, y: 0 })

function closeOnEscape(event: KeyboardEvent): void {
  if (!props.open || event.key !== 'Escape') return
  if (openSubmenu.value) {
    openSubmenu.value = null
    return
  }
  emit('close')
}
function closeOutside(event: PointerEvent): void {
  if (props.open && !menu.value?.contains(event.target as Node)) emit('close')
}

async function selectAction(action: ContextAction, event: MouseEvent): Promise<void> {
  if (!action.children?.length) {
    emit('select', action)
    return
  }
  const trigger = event.currentTarget as HTMLElement | null
  if (!trigger) return
  openSubmenu.value = action
  await nextTick()
  const submenu = menu.value?.querySelector<HTMLElement>('.context-action-menu__submenu')
  if (!submenu) return
  const triggerBounds = trigger.getBoundingClientRect()
  const submenuBounds = submenu.getBoundingClientRect()
  const x = triggerBounds.right + 4 + submenuBounds.width <= window.innerWidth - 8
    ? triggerBounds.right + 4
    : triggerBounds.left - submenuBounds.width - 4
  submenuPosition.value = {
    x: Math.max(8, x),
    y: Math.max(8, Math.min(triggerBounds.top, window.innerHeight - submenuBounds.height - 8)),
  }
}

watch(() => props.open, async (open) => {
  openSubmenu.value = null
  if (!open) return
  await nextTick()
  const element = menu.value
  if (!element) return
  const bounds = element.getBoundingClientRect()
  element.style.left = `${Math.max(8, Math.min(props.x, window.innerWidth - bounds.width - 8))}px`
  element.style.top = `${Math.max(8, Math.min(props.y, window.innerHeight - bounds.height - 8))}px`
  element.querySelector<HTMLButtonElement>('button')?.focus()
})

onMounted(() => {
  window.addEventListener('keydown', closeOnEscape)
  window.addEventListener('pointerdown', closeOutside, true)
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', closeOnEscape)
  window.removeEventListener('pointerdown', closeOutside, true)
})
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      ref="menu"
      class="context-action-menu"
      role="menu"
      :aria-label="label"
      :style="{ left: `${x}px`, top: `${y}px` }"
      @contextmenu.prevent
    >
      <button
        v-for="action in actions"
        :key="action.id"
        type="button"
        role="menuitem"
        :class="{
          'context-action-menu__item--danger': action.danger,
          'context-action-menu__item--separated': action.separator,
          'context-action-menu__item--submenu': action.children?.length,
        }"
        :aria-expanded="action.children?.length ? openSubmenu?.id === action.id : undefined"
        :aria-haspopup="action.children?.length ? 'menu' : undefined"
        @click="selectAction(action, $event)"
      >{{ action.label }}</button>
      <div
        v-if="openSubmenu"
        class="context-action-menu context-action-menu__submenu"
        role="menu"
        :aria-label="openSubmenu.label"
        :style="{ left: `${submenuPosition.x}px`, top: `${submenuPosition.y}px` }"
      >
        <button
          v-for="action in openSubmenu.children"
          :key="action.id"
          type="button"
          role="menuitem"
          :class="{
            'context-action-menu__item--danger': action.danger,
            'context-action-menu__item--separated': action.separator,
          }"
          @click="emit('select', action)"
        >{{ action.label }}</button>
      </div>
    </div>
  </Teleport>
</template>

<style>
.context-action-menu { position: fixed; z-index: 100000; display: grid; min-width: 13rem; max-width: min(22rem, calc(100vw - 1rem)); padding: .4rem; border: 1px solid var(--nf-color-border); border-radius: var(--nf-radius-sm); background: var(--nf-color-surface-raised); box-shadow: 0 18px 48px rgb(20 30 27 / 24%); }
.context-action-menu button { min-height: 2.4rem; padding: .55rem .75rem; border: 0; border-radius: calc(var(--nf-radius-sm) - .2rem); background: transparent; color: var(--nf-color-text); font: inherit; font-size: .88rem; font-weight: 650; text-align: left; cursor: pointer; }
.context-action-menu button:hover, .context-action-menu button:focus-visible { outline: 0; background: var(--nf-color-primary-soft); color: var(--nf-color-primary); }
.context-action-menu__item--danger { color: var(--nf-color-danger) !important; }
.context-action-menu__item--separated { margin-top: .35rem; border-top: 1px solid var(--nf-color-border) !important; }
.context-action-menu__item--submenu::after { content: '›'; float: right; margin-left: 1.5rem; font-size: 1.15rem; line-height: .9; }
.context-action-menu__submenu { position: fixed; }
</style>
