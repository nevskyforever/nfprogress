import { describe, expect, it, vi } from 'vitest'
vi.mock('@tauri-apps/api/core',()=>({invoke:vi.fn(async()=>[])}))
import { invoke } from '@tauri-apps/api/core'
import { SQLiteNoteSyncResolutionUploadRepository } from './noteSyncResolutionUploadRepository'
describe('resolution upload IPC',()=>it('uses only C1 scoped commands',async()=>{const repo=new SQLiteNoteSyncResolutionUploadRepository();await repo.list({account_id:'a',device_id:'d',canonical_user_id:'u',limit:1});await repo.commit({account_id:'a',device_id:'d',canonical_user_id:'u',receipts:[]});expect(invoke).toHaveBeenCalledWith('list_sealed_note_resolution_uploads',{command:{account_id:'a',device_id:'d',canonical_user_id:'u',limit:1}});expect(invoke).toHaveBeenCalledWith('commit_note_resolution_upload_acceptance',{command:{account_id:'a',device_id:'d',canonical_user_id:'u',receipts:[]}})}))
