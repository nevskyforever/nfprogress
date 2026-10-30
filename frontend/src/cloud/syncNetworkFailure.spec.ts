import { describe, expect, it } from 'vitest'
import { ApiError } from '@/api/client'
import { isSyncNetworkFailure, syncStageErrorCode } from './syncNetworkFailure'

describe('C21 transport failure classification', () => {
  it('retries connectivity and generic gateway outages, not security or protocol failures', () => {
    for (const error of [new ApiError(0, 'network_error', 'offline'), new ApiError(503, 'api_error', 'unavailable')]) {
      expect(isSyncNetworkFailure(error)).toBe(true)
      expect(syncStageErrorCode(error)).toBe('network_error')
    }
    for (const error of [new ApiError(401, 'invalid_token', 'expired'), new ApiError(0, 'invalid_token', 'expired'), new ApiError(401, 'network_error', 'expired'), new ApiError(503, 'note_readers_not_ready', 'blocked'), new Error('corrupt')]) {
      expect(isSyncNetworkFailure(error)).toBe(false)
      expect(syncStageErrorCode(error)).not.toBe('network_error')
    }
  })
})
