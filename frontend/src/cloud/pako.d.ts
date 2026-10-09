declare module 'pako' {
  export function deflate(data: Uint8Array, options?: { level?: number; windowBits?: number }): Uint8Array
}
declare module 'pako/lib/zlib/zstream.js' {
  export default class ZStream {
    input: Uint8Array; output: Uint8Array; next_in: number; next_out: number;
    avail_in: number; avail_out: number; total_in: number; total_out: number
  }
}
declare module 'pako/lib/zlib/inflate.js' {
  import ZStream from 'pako/lib/zlib/zstream.js'
  const inflate: { inflateInit2(s: ZStream, bits: number): number; inflate(s: ZStream, flush: number): number; inflateEnd(s: ZStream): number }
  export default inflate
}
