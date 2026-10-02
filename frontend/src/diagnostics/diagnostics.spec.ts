import { afterEach, describe, expect, it, vi } from 'vitest'
import { Diagnostics, type DiagnosticAdapter } from './service'
import { sanitizeContext, safeError, type DiagnosticEvent } from './events'
import { presentStatus } from './presentation'
vi.mock('@/platform/runtime', () => ({ currentPlatform: () => 'web' }))
const secret = 'PRIVATE_PASSWORD_AMK_TOKEN_DOCUMENT_SENTINEL'
function adapter() {
  const events: DiagnosticEvent[] = []
  const port: DiagnosticAdapter = {
    append: vi.fn(async batch => { events.push(...batch) }), stats: vi.fn(async () => ({count: events.length, bytes: 0, last_event_at: null})),
    text: vi.fn(async copy => JSON.stringify({copy, events})), copy: vi.fn(async () => {}), export: vi.fn(async () => true), clear: vi.fn(async () => {events.length = 0}),
  }
  return { port, events, service: new Diagnostics(port) }
}
afterEach(() => vi.useRealTimers())
describe('support diagnostic privacy and orchestration', () => {
  it('rejects all free-form context, content and secret fields at copy/export ingress', async () => {
    const h = adapter()
    const hostile = { password: secret, AMK: secret, key: secret, token: secret, Authorization: secret, nonce: secret, email: secret, username: secret, name: secret, note: secret, document: secret, payload: {text: secret}, status: secret, error_code: secret, count: 2, retry: true }
    expect(sanitizeContext(hostile)).toEqual({count: 2, retry: true})
    h.service.record('documents', 'load', 'failed', undefined, hostile, 'error')
    await h.service.copy(); await h.service.export()
    expect(JSON.stringify(h.events)).not.toContain(secret)
    expect(h.port.copy).toHaveBeenCalledWith(expect.not.stringContaining(secret))
    expect(h.port.text).toHaveBeenCalledWith(true)
    expect(h.port.export).toHaveBeenCalledOnce()
    await h.service.clear(); expect((await h.service.stats()).count).toBe(0)
  })
  it('preserves business results/errors and one correlation from request to terminal', async () => {
    const h = adapter()
    await expect(h.service.run('game', 'restore_streak', async () => 7)).resolves.toBe(7)
    const error = Object.assign(new TypeError(secret), {code: 'Validation', body: secret})
    await expect(h.service.run('game', 'restore_streak', async () => {throw error})).rejects.toBe(error)
    await h.service.flush()
    expect(h.events.map(e => e.code)).toEqual(['requested','started','succeeded','requested','started','failed'])
    expect(new Set(h.events.slice(0,3).map(e => e.correlation_id)).size).toBe(1)
    expect(new Set(h.events.slice(3).map(e => e.correlation_id)).size).toBe(1)
    expect(h.events[5]?.context).toEqual({error_code: 'Validation', error_class: 'TypeError'})
    expect(JSON.stringify(h.events)).not.toContain(secret)
    expect(safeError(new Error('metadata_import_resource_limit')).error_code).toBe('metadata_import_resource_limit')
    for(const code of ['content_note_codec_unsupported','content_note_map_owned','content_note_unsupported_source','content_note_scope_mismatch','content_note_resource_limit']) expect(sanitizeContext({error_code:code,content:secret,title:secret,stage_name:secret})).toEqual({error_code:code})
    expect(safeError(new Error(secret)).error_code).toBe('unknown_error')
    expect(safeError({code: secret, message: secret})).toEqual({error_code: 'unknown_error', error_class: 'Error'})
  })
  it('bounds batches, excludes debug, and tolerates unavailable storage without changing business outcome', async () => {
    vi.useFakeTimers(); const h = adapter()
    h.service.record('application', 'runtime_start', 'started', undefined, {}, 'debug')
    for (let i=0;i<100;i++) h.service.record('application','load','succeeded',undefined,{count:i})
    await h.service.flush(); expect(h.events).toHaveLength(64); expect(h.events[0]?.context.count).toBe(36)
    vi.mocked(h.port.append).mockRejectedValue(new Error(secret))
    await expect(h.service.run('sync','retry',async()=>42)).resolves.toBe(42)
    await expect(h.service.flush()).resolves.toBeUndefined()
    expect((await h.service.stats()).write_failed).toBe(true)
    await h.service.clear(); expect((await h.service.stats()).write_failed).toBe(false)
  })
})
describe('central friendly presentations', () => {
  it.each([
    ['metadata','local_differs_from_authenticated','Версии различаются'], ['structure','published_self_echo_pending','Изменения ожидают подтверждения'],
    ['error','content_note_codec_unsupported','Эти данные пока не поддерживаются'],
    ['error','content_note_map_owned','Эти данные пока не поддерживаются'],
    ['error','content_note_unsupported_source','Эти данные пока не поддерживаются'],
    ['error','content_note_scope_mismatch','Требуется ваше внимание'],
    ['error','content_note_resource_limit','Не удалось обработать всю историю'],
    ['error','orphan','Ожидает связанных данных'], ['error','conflict_preserved','Есть конфликт изменений'],
    ['error','stale_structural_resolution','Во время выбора появились новые изменения'], ['error','metadata_import_resource_limit','Не удалось обработать всю историю'],
    ['session','key_locked','Введите пароль шифрования'], ['error','future_safe_code','Не удалось завершить действие'],
  ] as const)('presents %s/%s separately from its code', (domain,code,title) => {
    const status = presentStatus(domain,code); expect(status.title).toBe(title); expect(status.title).not.toContain(code); expect(status.technicalCode).toBe(code)
    expect(status.description).toBeTruthy()
  })
  it('offers a concrete stale-choice action and never includes opaque suffixes', () => {
    expect(presentStatus('error','stale_structural_resolution:private-id').action).toContain('выберите')
    expect(presentStatus('error','bad code '+secret).technicalCode).toBe('unknown_error')
  })
})
