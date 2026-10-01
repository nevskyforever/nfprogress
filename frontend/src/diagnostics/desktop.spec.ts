import { beforeEach, describe, expect, it, vi } from 'vitest'
import { invoke } from '@tauri-apps/api/core'
import { save } from '@tauri-apps/plugin-dialog'
import { writeText } from '@tauri-apps/plugin-clipboard-manager'
import { diagnostics } from './service'
import permissions from '../../src-tauri/capabilities/main.json'
vi.mock('@/platform/runtime',()=>({currentPlatform:()=> 'tauri'}))
vi.mock('@tauri-apps/api/core',()=>({invoke:vi.fn()}))
vi.mock('@tauri-apps/plugin-dialog',()=>({save:vi.fn()}))
vi.mock('@tauri-apps/plugin-clipboard-manager',()=>({writeText:vi.fn()}))
beforeEach(()=>{vi.mocked(invoke).mockReset();vi.mocked(save).mockReset();vi.mocked(writeText).mockReset()})
describe('explicit desktop support adapters',()=>{
  it('copies native sanitized text through the permitted clipboard command',async()=>{
    vi.mocked(invoke).mockResolvedValue('{"schema_version":1,"truncated":true}\n')
    await diagnostics.copy();expect(invoke).toHaveBeenCalledWith('diagnostic_text',{copy:true})
    expect(writeText).toHaveBeenCalledWith('{"schema_version":1,"truncated":true}\n')
    expect(permissions.permissions).toContain('clipboard-manager:allow-write-text')
  })
  it('exports only to an explicit selected JSONL destination; cancellation writes nothing',async()=>{
    vi.mocked(save).mockResolvedValue(null);await expect(diagnostics.export()).resolves.toBe(false);expect(invoke).not.toHaveBeenCalled()
    vi.mocked(save).mockResolvedValue('/tmp/selected-support.jsonl');await expect(diagnostics.export()).resolves.toBe(true)
    expect(invoke).toHaveBeenCalledWith('export_diagnostics',{path:'/tmp/selected-support.jsonl'})
    expect(save).toHaveBeenCalledWith({defaultPath:'worta-diagnostics.jsonl',filters:[{name:'JSONL',extensions:['jsonl']}]})
    expect(permissions.permissions).toContain('dialog:allow-save')
  })
  it('clears only the support journal and reads stats without cloud APIs',async()=>{
    vi.mocked(invoke).mockResolvedValue({count:0,bytes:0,last_event_at:null})
    await diagnostics.clear();expect(invoke).toHaveBeenCalledWith('clear_diagnostics')
    await expect(diagnostics.stats()).resolves.toMatchObject({count:0})
    expect(invoke).toHaveBeenCalledWith('diagnostic_stats')
  })
})
