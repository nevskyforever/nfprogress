import { describe, expect, it } from 'vitest'
import fixture from './__fixtures__/gameCodecV1.json'
import { canonical } from './projectMetadataCodec'
import { frameGameEvent, unframeGameEvent, validateGameEvent, GAME_LIMITS, type GameEvent } from './gameCodec'
import { asAccountMasterKey, decryptObjectBytes, encryptObjectBytes, type ObjectCryptoEnvelope } from '@/crypto'
import { decryptAccountObject, encryptAccountObject } from '@/crypto/accountObjectCrypto'

const examples = fixture.examples.map(v => ({ ...v, event: v.event as GameEvent }))
describe('Game codec cross-language contract', () => {
  it.each(examples)('$name exact canonical bytes and frame allocation', v => {
    expect(canonical(v.event)).toBe(v.canonical_json)
    const frame = frameGameEvent(v.event)
    expect(Buffer.from(frame).toString('hex')).toBe(v.frame_hex)
    expect(unframeGameEvent(frame, v.event.header.scope)).toEqual(v.event)
    expect(() => unframeGameEvent(frame, v.event.header.scope === 'project' ? 'account' : 'project')).toThrow('game_codec_unsupported')
    for (const codec of [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]) {
      const wrong = frame.slice(); wrong[9] = codec
      expect(() => unframeGameEvent(wrong, v.event.header.scope)).toThrow('game_codec_unsupported')
    }
  })
  it.each(examples)('$name rejects arbitrary fields at each boundary', v => {
    for (const path of [[], ['header'], ['action']]) {
      const e = structuredClone(v.event) as unknown as Record<string, unknown>
      const node = path.reduce((n, k) => n[k] as Record<string, unknown>, e)
      node.extra = { raw_snapshot: true }
      expect(() => validateGameEvent(e)).toThrow()
    }
    const e = structuredClone(v.event); e.header.entity_id += ':foreign'
    expect(() => validateGameEvent(e)).toThrow()
  })
  it('rejects malformed UTF-8, lengths, compression, noncanonical JSON and overflow', () => {
    const event = examples[0]!.event, f = frameGameEvent(event)
    for (const offset of [8, 10, 11, 12, 16]) {
      const wrong = f.slice(); wrong[offset] = wrong[offset]! ^ 1
      expect(() => unframeGameEvent(wrong, 'project')).toThrow()
    }
    const wrong = f.slice(); wrong[21] = 0xff
    expect(() => unframeGameEvent(wrong, 'project')).toThrow()
    expect(() => unframeGameEvent(new Uint8Array(GAME_LIMITS.frameBytes + 1), 'project')).toThrow('game_resource_limit')
    const pretty = new TextEncoder().encode(JSON.stringify(event, null, 2))
    const noncanonical = new Uint8Array(20 + pretty.length); noncanonical.set(f.subarray(0, 20)); noncanonical.set(pretty, 20)
    const view = new DataView(noncanonical.buffer); view.setUint32(12, pretty.length); view.setUint32(16, pretty.length)
    expect(() => unframeGameEvent(noncanonical, 'project')).toThrow()
    const bad = structuredClone(event)
    if (bad.action.kind !== 'genesis' || !('history' in bad.action.base)) throw new Error('fixture')
    bad.action.base.history = Array.from({ length: GAME_LIMITS.days + 1 }, () => ({ day: '2026-10-01', frozen: false }))
    expect(() => frameGameEvent(bad)).toThrow('game_resource_limit')
  })
  it('preserves exact source identity and disambiguates completion scope', () => {
    const writing = structuredClone(examples.find(e => e.name === 'progress-reward-source')!.event)
    if (writing.action.kind !== 'writing') throw new Error('fixture')
    // Canonical UTC instant and local writing day intentionally differ.
    expect(() => validateGameEvent(writing)).not.toThrow()
    writing.action.progress_entity_id = 'stage:foreign'
    expect(() => validateGameEvent(writing)).toThrow()
    const stage = structuredClone(examples.find(e => e.name === 'stage-completion')!.event)
    if (stage.header.scope !== 'project' || stage.action.kind !== 'completion') throw new Error('fixture')
    stage.header.stage_id = 'project'; stage.action.progress_entity_id = 'stage:project'; stage.header.entity_id = `game:stage:project:${stage.header.event_id}`
    stage.action.completion_id = 'completion:["p",null]'
    expect(() => validateGameEvent(stage)).toThrow()
    stage.action.completion_id = 'completion:["p","project"]'
    expect(() => validateGameEvent(stage)).not.toThrow()
  })
  it('bounds decimals, claim identity, inventory counts and rejects unknown rules', () => {
    const e = structuredClone(examples.find(v => v.name === 'account-genesis')!.event)
    if (e.action.kind !== 'genesis' || e.header.scope !== 'account' || !('coins' in e.action.base)) throw new Error('fixture')
    e.action.base.coins = '1000000000001.000000'
    expect(() => validateGameEvent(e)).toThrow()
    e.action.base.coins = '250.000000'; e.action.base.inventory[0]!.count = 10001
    expect(() => validateGameEvent(e)).toThrow()
    e.action.base.inventory[0]!.count = 2; e.action.base.completion_claims.push(e.action.base.completion_claims[0]!)
    expect(() => validateGameEvent(e)).toThrow()
    const r = structuredClone(examples.find(v => v.name === 'linked-reward')!.event)
    if (r.action.kind !== 'reward') throw new Error('fixture')
    r.action.reward_id = 'reward:other'
    expect(() => validateGameEvent(r)).toThrow()
    const rule = structuredClone(examples[2]!.event) as unknown as { header: { rule: string } }
    rule.header.rule = 'future-game-rule'
    expect(() => validateGameEvent(rule)).toThrow()
  })
})

it('production project/account crypto separates Game scopes and every action identity', async () => {
  const amk = asAccountMasterKey(new Uint8Array(32).fill(71))
  const e = examples[0]!.event, h = e.header
  if (h.scope !== 'project') throw new Error('fixture')
  const context = { userId: h.account_id, projectId: h.project_id, entityType: 'project_game', entityId: h.entity_id }
  const envelope = await encryptObjectBytes(amk, context, frameGameEvent(e))
  expect(unframeGameEvent(await decryptObjectBytes(amk, context, envelope), 'project')).toEqual(e)
  for (const changed of [
    { ...context, projectId: 'p2' },
    { ...context, entityId: `game:stage:s1:${h.event_id}` },
    { ...context, entityId: `game:stage:s2:${h.event_id}` },
    ...['note', 'map', 'document', 'progress'].map(entityType => ({ ...context, entityType })),
  ]) await expect(decryptObjectBytes(amk, changed, envelope)).rejects.toThrow()
  const account = examples.find(v => v.name === 'account-genesis')!.event
  const a = account.header
  const accountContext = { userId: a.account_id, scope: 'account' as const, entityId: a.entity_id, entityType: 'account_game' }
  const accountEnvelope = await encryptAccountObject(amk, accountContext, frameGameEvent(account))
  expect(unframeGameEvent(await decryptAccountObject(amk, accountContext, accountEnvelope), 'account')).toEqual(account)
  for (const changed of [
    { ...accountContext, userId: '123e4567-e89b-42d3-a456-000000000099' },
    { ...accountContext, entityId: 'game:123e4567-e89b-42d3-a456-000000000099' },
    { ...accountContext, entityType: 'folder' },
  ]) await expect(decryptAccountObject(amk, changed, accountEnvelope)).rejects.toThrow()
  await expect(decryptObjectBytes(amk, context, accountEnvelope as unknown as ObjectCryptoEnvelope)).rejects.toThrow()
  await expect(decryptAccountObject(amk, accountContext, { ...envelope, crypto_version: 2, aad_version: 2 })).rejects.toThrow()
})
