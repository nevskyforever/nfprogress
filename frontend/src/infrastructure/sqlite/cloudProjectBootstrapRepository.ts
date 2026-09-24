import { invoke } from '@tauri-apps/api/core'

export type CloudProjectBootstrapMode = 'upload_existing' | 'import_remote'
export type CloudProjectBootstrapPhase = 'prepared' | 'registered' | 'captured' | 'completing' | 'ready' | 'paused' | 'blocked'

export interface CloudProjectBootstrapRecord {
  project_id: string
  account_id: string
  device_id: string
  bootstrap_id: string
  mode: CloudProjectBootstrapMode
  phase: CloudProjectBootstrapPhase
  remote_state: 'initializing' | 'active' | null
  initial_event_count: number
  initial_local_ordinal_hi: number
  remote_high_water: number | null
  initial_max_server_sequence: number | null
  blocked_reason: string | null
}

export interface CloudProjectInitialCohortStatus {
  event_count: number
  accepted_count: number
  max_server_sequence: number
  complete: boolean
}

export interface CloudProjectBootstrapScope {
  project_id: string
  account_id: string
  device_id: string
  bootstrap_id: string
}

export interface CloudProjectBootstrapRepository {
  preflight(projectId: string): Promise<Array<{ note_id: string, code: string }>>
  prepare(projectId: string, accountId: string, deviceId: string, mode: CloudProjectBootstrapMode): Promise<CloudProjectBootstrapRecord>
  confirmRegistration(scope: CloudProjectBootstrapScope, remoteState: 'initializing' | 'active', remoteHighWater: number): Promise<CloudProjectBootstrapRecord>
  capture(scope: CloudProjectBootstrapScope): Promise<CloudProjectBootstrapRecord>
  cohort(scope: CloudProjectBootstrapScope): Promise<CloudProjectInitialCohortStatus>
  markCompleting(scope: CloudProjectBootstrapScope): Promise<CloudProjectBootstrapRecord>
  markReady(scope: CloudProjectBootstrapScope): Promise<CloudProjectBootstrapRecord>
  list(accountId: string): Promise<CloudProjectBootstrapRecord[]>
  importRemote(projectId: string, displayName: string, accountId: string, deviceId: string, bootstrapId: string, remoteHighWater: number): Promise<CloudProjectBootstrapRecord>
  setPaused(scope: CloudProjectBootstrapScope, paused: boolean): Promise<CloudProjectBootstrapRecord>
}

export class SQLiteCloudProjectBootstrapRepository implements CloudProjectBootstrapRepository {
  preflight(projectId: string) {
    return invoke<Array<{ note_id: string, code: string }>>('preflight_cloud_project_bootstrap', { projectId })
  }

  prepare(projectId: string, accountId: string, deviceId: string, mode: CloudProjectBootstrapMode) {
    return invoke<CloudProjectBootstrapRecord>('prepare_cloud_project_bootstrap', {
      command: { project_id: projectId, account_id: accountId, device_id: deviceId, mode },
    })
  }

  confirmRegistration(scope: CloudProjectBootstrapScope, remoteState: 'initializing' | 'active', remoteHighWater: number) {
    return invoke<CloudProjectBootstrapRecord>('confirm_cloud_project_registration', {
      command: { ...scope, remote_state: remoteState, remote_high_water: remoteHighWater },
    })
  }

  capture(scope: CloudProjectBootstrapScope) {
    return invoke<CloudProjectBootstrapRecord>('capture_initial_note_sync_intents', { command: scope })
  }

  cohort(scope: CloudProjectBootstrapScope) {
    return invoke<CloudProjectInitialCohortStatus>('read_initial_note_cohort_status', { command: scope })
  }

  markCompleting(scope: CloudProjectBootstrapScope) {
    return invoke<CloudProjectBootstrapRecord>('mark_cloud_project_bootstrap_completing', { command: scope })
  }

  markReady(scope: CloudProjectBootstrapScope) {
    return invoke<CloudProjectBootstrapRecord>('mark_cloud_project_bootstrap_ready', { command: scope })
  }

  list(accountId: string) {
    return invoke<CloudProjectBootstrapRecord[]>('list_cloud_project_bootstraps', { accountId })
  }

  importRemote(projectId: string, displayName: string, accountId: string, deviceId: string, bootstrapId: string, remoteHighWater: number) {
    return invoke<CloudProjectBootstrapRecord>('import_remote_cloud_project', {
      command: {
        project_id: projectId, display_name: displayName, account_id: accountId,
        device_id: deviceId, bootstrap_id: bootstrapId, remote_high_water: remoteHighWater,
      },
    })
  }

  setPaused(scope: CloudProjectBootstrapScope, paused: boolean) {
    return invoke<CloudProjectBootstrapRecord>('set_cloud_project_bootstrap_paused', { command: scope, paused })
  }
}
