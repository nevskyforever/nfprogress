// @vitest-environment node
import { describe, expect, it } from 'vitest'
import fixture from './__fixtures__/stageCodecV1.json'
import { STAGE_FIELDS, frameStructuralEvent, unframeStructuralEvent, encodeStructuralEvent, sealStructuralEvent, openStructuralEvent, type StructuralEvent } from './stageCodec'
import { generateAccountMasterKey } from '@/crypto'
const event = () => structuredClone(fixture.event) as StructuralEvent
const context = (e: StructuralEvent) => ({account_id:e.header.account_id,project_id:e.header.project_id,entity_id:e.header.entity_id,entity_type:e.header.entity_type,event_id:e.header.event_id})
describe('C18 structural codec v1', () => {
  it('freezes exact portable fields and native golden canonical bytes', () => {
    expect([...STAGE_FIELDS]).toEqual(fixture.portable_fields)
    expect(new TextDecoder().decode(encodeStructuralEvent(event()))).toBe(fixture.canonical_json)
    expect(unframeStructuralEvent(frameStructuralEvent(event()))).toEqual(event())
    for (const sample of fixture.numeric_cases) { const e = event(); e.stage!.goal = sample.goal; expect(new TextDecoder().decode(encodeStructuralEvent(e))).toBe(sample.canonical_json) }
  })
  it('rejects unknown fields, versions, numbers and noncausal headers', () => {
    for (const mutate of [
      (e: any) => { e.stage.path = '/private/file' }, (e: any) => { e.path = 'x' },
      (e: any) => { e.version = '1' }, (e: any) => { e.version = true },
      (e: any) => { e.header.extra = true }, (e: any) => { e.version = 2 },
      (e: any) => { delete e.stage.created_at }, (e: any) => { e.stage.goal = Infinity },
      (e: any) => { e.stage.personal_goal = -1 }, (e: any) => { e.header.operation = 'update' },
      (e: any) => { e.header.account_id = 'other' },
    ]) { const e = event(); mutate(e); expect(() => frameStructuralEvent(e)).toThrow() }
  })
  it('rejects unsupported frame flags, length mismatch, trailing/noncanonical JSON', () => {
    for (const offset of [0,8,9,10,11,12,16]) { const f = frameStructuralEvent(event()); f[offset] = 255; expect(() => unframeStructuralEvent(f)).toThrow() }
    expect(() => unframeStructuralEvent(frameStructuralEvent(event()).subarray(0,30))).toThrow()
  })
  it('validates exact order payload and distinct codec ID', () => {
    const e = event(); e.header.entity_type = 'stage_order'; e.header.entity_id = 'stage_order'; e.stage = null
    e.stage_ids = ['S1','S2']; e.stage_heads = {S1:[e.header.event_id],S2:[e.header.metadata_event_id]}
    const f = frameStructuralEvent(e); expect(f[9]).toBe(3); expect(unframeStructuralEvent(f)).toEqual(e)
    e.stage_ids = ['S1','S1']; expect(() => frameStructuralEvent(e)).toThrow()
    e.stage_ids = ['S1']; expect(() => frameStructuralEvent(e)).toThrow()
  })
  it('authenticates account/project/entity/type/event context in the unchanged C11 namespace', async () => {
    const e = event(), key = await generateAccountMasterKey(), sealed = await sealStructuralEvent(key,e)
    expect(sealed.crypto_version).toBe(1); expect(sealed.aad_version).toBe(1)
    expect(await openStructuralEvent(key,context(e),sealed)).toEqual(e)
    for (const field of ['account_id','project_id','entity_id','entity_type','event_id'] as const) {
      await expect(openStructuralEvent(key,{...context(e),[field]:field==='entity_type'?'stage_order':'other'},sealed)).rejects.toThrow()
    }
    const tampered={...sealed,ciphertext:sealed.ciphertext.slice()};tampered.ciphertext[0] = tampered.ciphertext[0]! ^ 1
    await expect(openStructuralEvent(key,context(e),tampered)).rejects.toThrow()
  })
})

describe('C18 structural full-tip codec v2', () => {
  it('keeps v1 readable and gives decisions a distinct strict codec version', () => {
    const e = event(); e.version = 2; e.header.operation = 'update'; e.header.revision = 3; e.header.generation = 3
    e.header.parent_event_ids = [e.header.metadata_event_id, e.header.device_id].sort()
    const frame = frameStructuralEvent(e); expect(frame[10]).toBe(2); expect(unframeStructuralEvent(frame)).toEqual(e)
    e.header.parent_event_ids.reverse(); expect(() => frameStructuralEvent(e)).toThrow()
    e.header.parent_event_ids = [e.header.device_id, e.header.device_id]; expect(() => frameStructuralEvent(e)).toThrow()
    expect(unframeStructuralEvent(frameStructuralEvent(event())).version).toBe(1)
  })
  it('never reinterprets Stage frames as metadata or Note payloads', async () => {
    const { unframeProjectMetadata } = await import('./projectMetadataCodec')
    const { decodeNoteSyncPlaintext } = await import('./noteSyncCodec')
    const frame = frameStructuralEvent(event())
    expect(() => unframeProjectMetadata(frame)).toThrow()
    expect(() => decodeNoteSyncPlaintext(frame)).toThrow()
    expect(() => decodeNoteSyncPlaintext(encodeStructuralEvent(event()))).toThrow()
    const forgedMetadataFrame = frame.slice(); forgedMetadataFrame[9] = 1
    expect(() => unframeStructuralEvent(forgedMetadataFrame)).toThrow()
  })
})
