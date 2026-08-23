import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

export const MOTION_PREFERENCES = ['system', 'full', 'reduced'] as const
export type MotionPreference = (typeof MOTION_PREFERENCES)[number]

export function isMotionPreference(value: unknown): value is MotionPreference {
  return typeof value === 'string'
    && MOTION_PREFERENCES.includes(value as MotionPreference)
}

export const useMotionStore = defineStore('motion', () => {
  // Existing installs did not have a motion preference. Keep progress feedback
  // visible for them, while still offering explicit system/reduced modes.
  const preference = ref<MotionPreference>('full')
  const systemReduced = ref(false)
  let mediaQuery: MediaQueryList | null = null

  const reduced = computed(() =>
    preference.value === 'reduced'
    || (preference.value === 'system' && systemReduced.value),
  )

  function setPreference(value: MotionPreference): void {
    preference.value = value
    document.documentElement.dataset.motion = reduced.value ? 'reduced' : 'full'
  }

  function handleSystemMotion(event: MediaQueryListEvent): void {
    systemReduced.value = event.matches
    document.documentElement.dataset.motion = reduced.value ? 'reduced' : 'full'
  }

  function initialize(): void {
    mediaQuery?.removeEventListener('change', handleSystemMotion)
    mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
    systemReduced.value = mediaQuery.matches
    mediaQuery.addEventListener('change', handleSystemMotion)
    document.documentElement.dataset.motion = reduced.value ? 'reduced' : 'full'
  }

  function dispose(): void {
    mediaQuery?.removeEventListener('change', handleSystemMotion)
    mediaQuery = null
  }

  return { preference, reduced, initialize, dispose, setPreference }
})
