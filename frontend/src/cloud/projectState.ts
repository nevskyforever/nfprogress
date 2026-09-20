import { ApiError } from '@/api/client'

/** Client-only lifecycle; it is intentionally not a server sync-status enum. */
export const CLOUD_PROJECT_STATES = [
  'LOCAL_ONLY',
  'ENABLING_SYNC',
  'SYNCED',
  'SYNC_ERROR',
  'DISABLING_SYNC',
] as const

export type CloudProjectState = (typeof CLOUD_PROJECT_STATES)[number]

const transitions: Readonly<Record<CloudProjectState, readonly CloudProjectState[]>> = {
  LOCAL_ONLY: ['ENABLING_SYNC'],
  ENABLING_SYNC: ['SYNCED', 'SYNC_ERROR'],
  SYNCED: ['DISABLING_SYNC'],
  SYNC_ERROR: ['ENABLING_SYNC'],
  DISABLING_SYNC: ['LOCAL_ONLY', 'SYNC_ERROR'],
}

export function canTransitionCloudProjectState(
  from: CloudProjectState,
  to: CloudProjectState,
): boolean {
  return transitions[from].includes(to)
}

export function transitionCloudProjectState(
  from: CloudProjectState,
  to: CloudProjectState,
): CloudProjectState {
  if (!canTransitionCloudProjectState(from, to)) {
    throw new Error(`Invalid cloud project transition: ${from} -> ${to}`)
  }
  return to
}

export const CLOUD_PROJECT_LIMIT_REACHED = 'cloud_project_limit_reached' as const

export function cloudProjectErrorCode(error: unknown): string | null {
  return error instanceof ApiError && error.code === CLOUD_PROJECT_LIMIT_REACHED
    ? CLOUD_PROJECT_LIMIT_REACHED
    : null
}
