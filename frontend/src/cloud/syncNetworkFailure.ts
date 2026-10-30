import { ApiError } from '@/api/client'

/** Only unambiguous transport failures qualify for automatic retry. */
export function isSyncNetworkFailure(error: unknown): boolean {
  return error instanceof ApiError && ((error.status === 0 && error.code === 'network_error')
    || ([502, 503, 504].includes(error.status) && error.code === 'api_error'))
}

/** Retain the network classification when a bounded cycle returns stage errors. */
export function syncStageErrorCode(error: unknown): string {
  if (isSyncNetworkFailure(error)) return 'network_error'
  if (error instanceof Error && 'code' in error && typeof error.code === 'string') {
    // A server or local failure cannot opt into network retry by naming itself
    // network_error; only the transport status above can establish that.
    return error.code === 'network_error' ? 'unknown_error' : error.code
  }
  const name = error instanceof Error ? error.name : 'unknown_error'
  return name === 'network_error' ? 'unknown_error' : name
}
