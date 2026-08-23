import { ref } from 'vue'
import { defineStore } from 'pinia'

import type { GameNotifications } from '@/types/game'

export type NotificationKind = 'success' | 'error' | 'warning' | 'info'

export interface AppNotification {
  id: string
  kind: NotificationKind
  message: string
}

const DEFAULT_DURATION_SECONDS = 10
const MIN_DURATION_SECONDS = 1
const MAX_DURATION_SECONDS = 3600

function emptyGameHistory(): GameNotifications {
  return { unread: [], read: [], unread_count: 0 }
}

function normalizedDuration(value: unknown): number {
  if (
    typeof value !== 'number'
    || !Number.isFinite(value)
    || !Number.isInteger(value)
  ) {
    return DEFAULT_DURATION_SECONDS
  }
  return Math.min(MAX_DURATION_SECONDS, Math.max(MIN_DURATION_SECONDS, value))
}

export const useNotificationsStore = defineStore('notifications', () => {
  const notifications = ref<AppNotification[]>([])
  const gameHistory = ref<GameNotifications>(emptyGameHistory())
  const durationSeconds = ref(DEFAULT_DURATION_SECONDS)
  const timers = new Map<string, ReturnType<typeof setTimeout>>()
  let sequence = 0

  function setDurationSeconds(value: unknown): void {
    durationSeconds.value = normalizedDuration(value)
  }

  function setGameHistory(value: GameNotifications): void {
    gameHistory.value = {
      unread: [...value.unread],
      read: [...value.read],
      unread_count: value.unread_count,
    }
  }

  function dismiss(id: string): void {
    const timer = timers.get(id)
    if (timer !== undefined) {
      clearTimeout(timer)
      timers.delete(id)
    }
    notifications.value = notifications.value.filter((notification) => notification.id !== id)
  }

  function show(message: string, kind: NotificationKind = 'info'): string | null {
    const normalizedMessage = message.trim()
    if (!normalizedMessage) return null

    const id = `notice-${Date.now()}-${sequence++}`
    if (notifications.value.length >= 4) {
      const oldest = notifications.value[0]
      if (oldest) dismiss(oldest.id)
    }
    notifications.value = [
      ...notifications.value,
      { id, kind, message: normalizedMessage },
    ]
    const timer = setTimeout(() => dismiss(id), durationSeconds.value * 1000)
    timers.set(id, timer)
    return id
  }

  function success(message: string): string | null {
    return show(message, 'success')
  }

  function error(message: string): string | null {
    return show(message, 'error')
  }

  function warning(message: string): string | null {
    return show(message, 'warning')
  }

  function clear(): void {
    for (const timer of timers.values()) clearTimeout(timer)
    timers.clear()
    notifications.value = []
  }

  return {
    notifications,
    gameHistory,
    durationSeconds,
    setDurationSeconds,
    setGameHistory,
    dismiss,
    show,
    success,
    error,
    warning,
    clear,
  }
})
