import {afterEach,describe,it,expect,vi} from 'vitest'
import {projectsApi} from './projects'
import {invoke} from '@tauri-apps/api/core'
vi.mock('@tauri-apps/api/core',()=>({invoke:vi.fn(async()=>({}))}))
afterEach(()=>{vi.restoreAllMocks();vi.unstubAllGlobals()})
describe('ordinary catalog writer bridge',()=>{
 it('carries both folder assignment and explicit null removal into native patch',async()=>{vi.stubGlobal('window',{__TAURI_INTERNALS__:{}});await projectsApi.update('C1',{folder_id:'F1'});expect(invoke).toHaveBeenCalledWith('update_project',{projectId:'C1',patch:{folderId:'F1'}});await projectsApi.update('C1',{folder_id:null});expect(invoke).toHaveBeenLastCalledWith('update_project',{projectId:'C1',patch:{folderId:null}})})
 it('uses the native full-folder-order writer',async()=>{await projectsApi.reorderFolders(['F2','F1']);expect(invoke).toHaveBeenCalledWith('reorder_project_folders',{folderIds:['F2','F1']})})
})
