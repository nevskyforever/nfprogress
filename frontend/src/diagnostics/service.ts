import { currentPlatform } from '@/platform/runtime'
import { correlationId, sanitizeContext, safeError, type DiagnosticEvent, type Operation, type Subsystem } from './events'
export interface DiagnosticStats { count: number; bytes: number; last_event_at: string | null; write_failed?: boolean }
export interface DiagnosticAdapter {
  append(events: DiagnosticEvent[]): Promise<void>; stats(): Promise<DiagnosticStats>
  text(copy: boolean): Promise<string>; clear(): Promise<void>; export(): Promise<boolean>; copy(text: string): Promise<void>
}
const desktop: DiagnosticAdapter = {
  async append(events) { const { invoke } = await import('@tauri-apps/api/core'); await invoke('append_diagnostics', { events }) },
  async stats() { const { invoke } = await import('@tauri-apps/api/core'); return invoke('diagnostic_stats') },
  async text(copy) { const { invoke } = await import('@tauri-apps/api/core'); return invoke('diagnostic_text', { copy }) },
  async clear() { const { invoke } = await import('@tauri-apps/api/core'); await invoke('clear_diagnostics') },
  async export() {
    const { save } = await import('@tauri-apps/plugin-dialog')
    const path = await save({ defaultPath: 'worta-diagnostics.jsonl', filters: [{ name: 'JSONL', extensions: ['jsonl'] }] })
    if (!path) return false
    const { invoke } = await import('@tauri-apps/api/core'); await invoke('export_diagnostics', { path }); return true
  },
  async copy(text) { const { writeText } = await import('@tauri-apps/plugin-clipboard-manager'); await writeText(text) },
}
export class Diagnostics {
  private writeFailed = false
  private queue: DiagnosticEvent[] = []
  private timer: ReturnType<typeof setTimeout> | undefined
  private flight: Promise<void> = Promise.resolve()
  constructor(private readonly adapter: DiagnosticAdapter, private readonly enabled = () => true) {}
  record(subsystem: Subsystem, operation: Operation, code: DiagnosticEvent['code'], correlation = correlationId(), context: unknown = {}, severity: DiagnosticEvent['severity'] = 'info'): string {
    if (!this.enabled() || severity === 'debug') return correlation
    this.queue.push({ schema_version: 1, timestamp: new Date().toISOString(), severity, subsystem, operation, code, correlation_id: correlation, context: sanitizeContext(context) })
    if (this.queue.length > 64) this.queue.shift()
    if (!this.timer) this.timer = setTimeout(() => { this.timer = undefined; void this.flush() }, 150)
    return correlation
  }
  async flush(): Promise<void> {
    clearTimeout(this.timer); this.timer = undefined
    const batch = this.queue.splice(0)
    this.flight = this.flight.catch(() => undefined).then(async () => { if (batch.length) { await this.adapter.append(batch); this.writeFailed = false } })
    // A diagnostic write failure never alters the business operation or sync ACK.
    await this.flight.catch(() => { this.writeFailed = true })
  }
  async run<T>(subsystem: Subsystem, operation: Operation, action: (correlation: string) => Promise<T>, correlation?: string): Promise<T> {
    const id = this.record(subsystem, operation, 'requested', correlation)
    this.record(subsystem, operation, 'started', id)
    try { const result = await action(id); this.record(subsystem, operation, 'succeeded', id); return result }
    catch (error) { this.record(subsystem, operation, 'failed', id, safeError(error), 'error'); throw error }
  }
  async stats() { await this.flush(); return { ...await this.adapter.stats(), write_failed: this.writeFailed } }
  async copy() { await this.flush(); await this.adapter.copy(await this.adapter.text(true)) }
  async export() { await this.flush(); return this.adapter.export() }
  async clear() { await this.flush(); await this.adapter.clear(); this.writeFailed = false }
}
export const diagnostics = new Diagnostics(desktop, () => currentPlatform() === 'tauri')
