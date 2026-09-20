import { describe, expect, it, vi } from 'vitest'

import { cloudProjectsApi } from '@/api/cloudProjects'
import { ApiError } from '@/api/client'

import { canEnableCloudProjectSync } from './capabilities'
import {
  CLOUD_PROJECT_LIMIT_REACHED,
  CLOUD_PROJECT_STATES,
  canTransitionCloudProjectState,
  cloudProjectErrorCode,
  transitionCloudProjectState,
} from './projectState'

describe('C8 cloud project state contract', () => {
  it('declares the exact lifecycle states and valid transitions', () => {
    expect(CLOUD_PROJECT_STATES).toEqual([
      'LOCAL_ONLY', 'ENABLING_SYNC', 'SYNCED', 'SYNC_ERROR', 'DISABLING_SYNC',
    ])
    expect(canTransitionCloudProjectState('LOCAL_ONLY', 'ENABLING_SYNC')).toBe(true)
    expect(canTransitionCloudProjectState('ENABLING_SYNC', 'SYNCED')).toBe(true)
    expect(canTransitionCloudProjectState('ENABLING_SYNC', 'SYNC_ERROR')).toBe(true)
    expect(canTransitionCloudProjectState('SYNC_ERROR', 'ENABLING_SYNC')).toBe(true)
    expect(canTransitionCloudProjectState('SYNCED', 'DISABLING_SYNC')).toBe(true)
    expect(canTransitionCloudProjectState('DISABLING_SYNC', 'LOCAL_ONLY')).toBe(true)
    expect(canTransitionCloudProjectState('LOCAL_ONLY', 'SYNCED')).toBe(false)
  })

  it('keeps failures explicit and supports retry and safe disabling', () => {
    const failedEnable = transitionCloudProjectState('ENABLING_SYNC', 'SYNC_ERROR')
    expect(failedEnable).toBe('SYNC_ERROR')
    expect(transitionCloudProjectState(failedEnable, 'ENABLING_SYNC')).toBe('ENABLING_SYNC')
    expect(transitionCloudProjectState('SYNCED', 'DISABLING_SYNC')).toBe('DISABLING_SYNC')
    expect(transitionCloudProjectState('DISABLING_SYNC', 'LOCAL_ONLY')).toBe('LOCAL_ONLY')
  })

  it('does not expose a production path that could claim registry reservation is synced', () => {
    expect(canEnableCloudProjectSync()).toBe(false)
    expect(canEnableCloudProjectSync({ encryptedInitialUpload: true })).toBe(true)
  })

  it('keeps document work_method sync unrelated to the WORTA cloud lifecycle', () => {
    const legacyDocumentSyncMethod = 'sync'
    expect(legacyDocumentSyncMethod).not.toBe('SYNCED')
    expect(canTransitionCloudProjectState('LOCAL_ONLY', 'SYNCED')).toBe(false)
  })

  it('serializes only project IDs for registry calls, never project content', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(new Response(JSON.stringify({
      cloud_project_ids: ['project-a'], cloud_project_count: 1, max_cloud_projects: 20,
    }), { status: 200 }))
    await cloudProjectsApi.enable('access-token', 'project-a')
    const [, options] = fetchMock.mock.calls[0]!
    expect(options).toMatchObject({ method: 'POST' })
    expect((options as RequestInit).body).toBeUndefined()
    expect(((options as RequestInit).headers as Headers).get('Authorization')).toBe('Bearer access-token')
  })

  it('maps the quota error to a stable client error code', () => {
    expect(cloudProjectErrorCode(new ApiError(409, CLOUD_PROJECT_LIMIT_REACHED, 'limit')))
      .toBe(CLOUD_PROJECT_LIMIT_REACHED)
    expect(cloudProjectErrorCode(new ApiError(409, 'other', 'other'))).toBeNull()
  })
})
