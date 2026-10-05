import { invoke } from '@tauri-apps/api/core'
import type { MetadataScope } from './projectMetadataMigrationRepository'
export interface ProjectCoverRepository {
  command<T>(scope:MetadataScope,projectId:string,action:string,data:unknown,now:string):Promise<T>
}
export class SQLiteProjectCoverRepository implements ProjectCoverRepository {
  command<T>(scope:MetadataScope,projectId:string,action:string,data:unknown,now:string):Promise<T> {
    return invoke('project_cover_command',{scope,projectId,action,data,now})
  }
}
