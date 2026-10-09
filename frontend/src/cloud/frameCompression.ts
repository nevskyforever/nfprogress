/** C18.7.01: authenticated frame transform only. Production selection requires explicit account reader authorization.
 * Low-level inflate intentionally avoids convenience APIs that join members or
 * allocate from an untrusted stream. Never call this before AEAD authentication.
 */
import inflate from 'pako/lib/zlib/inflate.js'
import ZStream from 'pako/lib/zlib/zstream.js'
import { deflate } from 'pako'
export const COMPRESSION_LIMITS = { bytes: 8 * 1024 * 1024 - 20, inputBytes: 1024 * 1024, ratio: 512, window: 32768, chunk: 16384 } as const
export const COMPRESSION_POLICY = { minimumBytes: 1024, minimumSaving: 128, minimumPercent: 10, level: 6 } as const
export const COMPRESSION_CODES = ['compression_unsupported', 'compression_invalid_stream', 'compression_input_limit', 'compression_output_limit', 'compression_resource_limit', 'compression_length_mismatch'] as const
export type CompressionCode = typeof COMPRESSION_CODES[number]
export class FrameCompressionError extends Error { constructor(readonly code: CompressionCode) { super(code) } }
const fail = (code: CompressionCode): never => { throw new FrameCompressionError(code) }
export function decompressBounded(algorithm: number, compressed: Uint8Array, declaredSize: number, entityLimit: number): Uint8Array {
  if (algorithm !== 0 && algorithm !== 1) fail('compression_unsupported')
  if (compressed.length > (algorithm === 0 ? COMPRESSION_LIMITS.bytes : COMPRESSION_LIMITS.inputBytes)) fail('compression_input_limit')
  if (!Number.isSafeInteger(declaredSize) || declaredSize < 0 || !Number.isSafeInteger(entityLimit) || entityLimit < 0
    || declaredSize > Math.min(entityLimit, COMPRESSION_LIMITS.bytes)) fail('compression_output_limit')
  if (algorithm === 0) { if (compressed.length !== declaredSize) fail('compression_length_mismatch'); return compressed }
  if (!declaredSize || declaredSize > compressed.length * COMPRESSION_LIMITS.ratio) fail('compression_resource_limit')
  if (compressed.length < 6 || compressed[0]! % 16 !== 8 || compressed[0]! >> 4 > 7
    || (compressed[0]! * 256 + compressed[1]!) % 31 !== 0 || (compressed[1]! & 32) !== 0) fail('compression_invalid_stream')
  // One overflow sentinel; never grow or join output buffers.
  const output = new Uint8Array(declaredSize + 1)
  const stream = new ZStream()
  if (inflate.inflateInit2(stream, 15) !== 0) fail('compression_invalid_stream')
  stream.input = compressed; stream.next_in = 0; stream.avail_in = compressed.length; stream.output = output
  try {
    for (;;) {
      const beforeIn = stream.total_in, beforeOut = stream.total_out
      stream.avail_out = Math.min(COMPRESSION_LIMITS.chunk, output.length - stream.next_out)
      const status = inflate.inflate(stream, 0)
      if (stream.total_out > declaredSize) fail('compression_length_mismatch')
      if (status === 1) {
        if (stream.avail_in !== 0) fail('compression_invalid_stream')
        if (stream.total_out !== declaredSize) fail('compression_length_mismatch')
        return output.subarray(0, declaredSize)
      }
      if (status !== 0 || stream.total_in === beforeIn && stream.total_out === beforeOut) fail('compression_invalid_stream')
    }
  } finally { inflate.inflateEnd(stream) }
}
/** Frozen policy primitive. Capability authorization is separate from payload selection. */
export function compressForFrame(canonicalBytes: Uint8Array, codecId: number): { algorithm: 0 | 1; payload: Uint8Array } {
  if (canonicalBytes.length > COMPRESSION_LIMITS.bytes) fail('compression_output_limit')
  const none = { algorithm: 0 as const, payload: canonicalBytes }
  if (!Number.isInteger(codecId) || codecId < 1 || codecId > 13 || canonicalBytes.length < COMPRESSION_POLICY.minimumBytes) return none
  let payload: Uint8Array
  // A library failure before persistence leaves the validated canonical ID0
  // candidate usable. Reader failures and persisted frames never use fallback.
  try { payload = deflate(canonicalBytes, { level: COMPRESSION_POLICY.level, windowBits: 15 }) }
  catch { return none }
  const saving = canonicalBytes.length - payload.length
  if (payload.length > COMPRESSION_LIMITS.inputBytes || saving < COMPRESSION_POLICY.minimumSaving || saving * 100 < canonicalBytes.length * COMPRESSION_POLICY.minimumPercent
    || canonicalBytes.length > payload.length * COMPRESSION_LIMITS.ratio) return none
  return { algorithm: 1, payload }
}
/** Convert a verified frame to its historical ID0 view, then let the owning
 * codec revalidate exact canonical bytes. No authority/event/history rewrite.
 */
export function normalizeAuthenticatedFrame(frame: Uint8Array, codecs: readonly number[], versions: readonly number[], entityLimit: number): Uint8Array {
  if (frame.length < 20 || ![87,79,82,84,65,45,67,49].every((b,i) => frame[i] === b)
    || frame[8] !== 1 || !codecs.includes(frame[9]!) || !versions.includes(frame[10]!)) fail('compression_invalid_stream')
  const view = new DataView(frame.buffer, frame.byteOffset, frame.byteLength)
  if (view.getUint32(16) !== frame.length - 20) fail('compression_invalid_stream')
  const payload = decompressBounded(frame[11]!, frame.subarray(20), view.getUint32(12), entityLimit)
  if (frame[11] === 0) return frame
  const normalized = new Uint8Array(20 + payload.length)
  normalized.set(frame.subarray(0,20)); normalized[11] = 0
  new DataView(normalized.buffer).setUint32(16, payload.length)
  normalized.set(payload,20); payload.fill(0)
  return normalized
}
export const compressionBlocker = (error: unknown): CompressionCode | undefined => error instanceof FrameCompressionError ? error.code : undefined


/** Called only for a freshly validated canonical writer candidate, never a
 * persisted ciphertext retry. Canonical identity remains the original ID0 view.
 */
export function compressCanonicalFrame(frame: Uint8Array): Uint8Array {
  if (frame.length < 20 || frame[11] !== 0) fail('compression_invalid_stream')
  const original = normalizeAuthenticatedFrame(frame, [1,2,3,4,5,6,7,8,9,10,11,12,13], [1,2], COMPRESSION_LIMITS.bytes)
  const result = compressForFrame(original.subarray(20), original[9]!)
  if (result.algorithm === 0) return frame
  const selected = new Uint8Array(20 + result.payload.length)
  selected.set(original.subarray(0,20)); selected[11] = 1
  new DataView(selected.buffer).setUint32(16, result.payload.length)
  selected.set(result.payload,20)
  return selected
}


/** Admission precedes first encryption/persistence. Unknown/false admission is
 * ID0; a sealed retry never calls this function. Caller owns authentication and
 * canonical entity validation, and must wipe both returned/original buffers.
 */
export async function selectWriterFrame(canonical: Uint8Array, authorize: () => Promise<boolean>): Promise<Uint8Array> {
  const candidate = compressCanonicalFrame(canonical)
  if (candidate === canonical) return canonical
  try {
    if (await authorize()) return candidate
    candidate.fill(0)
    return canonical
  } catch (error) { candidate.fill(0); throw error }
}
