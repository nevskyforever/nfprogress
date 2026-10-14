// @vitest-environment node
import { describe, expect, it, vi } from 'vitest'
import { BROWSER_CANONICAL_READERS, openBrowserCanonicalObject } from './canonicalReaders'
import { readerCases, readerFrame, readFixture, readerContext, encryptedReaderFrame } from './canonicalReaders.testFixture'
import { asAccountMasterKey } from '@/crypto'
import * as compression from '@/cloud/frameCompression'
import { canonical } from '@/cloud/projectMetadataCodec'
const cases=readerCases()
describe('C21.1.20 authenticated canonical browser reader matrix',()=>{
 it('enumerates every frozen ID/version without a fallback',()=>{expect(BROWSER_CANONICAL_READERS.map(c=>c.id)).toEqual(Array.from({length:13},(_,i)=>i+1));expect(cases.map(c=>[c.id,c.version])).toEqual(BROWSER_CANONICAL_READERS.flatMap(c=>c.versions.map(v=>[c.id,v])).sort((a,b)=>cases.findIndex(c=>c.id===a[0]&&c.version===a[1])-cases.findIndex(c=>c.id===b[0]&&c.version===b[1])))})
 for(const c of cases)describe(`codec${c.id}/v${c.version}`,()=>{
  it('authenticated ID0/ID1 produce identical owning canonical entity',async()=>{const a=await readFixture(c,readerFrame(c)),b=await readFixture(c,readerFrame(c,true));expect(a).toEqual(c.event);expect(b).toEqual(a);expect(canonical(b)).toBe(canonical(c.event))})
  it.each(['codec','version','truncated','stream','length','trailing','semantic','family'] as const)('rejects %s after authentication',async kind=>{
   let f=readerFrame(c,true)
   if(kind==='codec')f[9]=99
   else if(kind==='version')f[10]=99
   else if(kind==='truncated')f=f.slice(0,19)
   else if(kind==='stream')f[f.length-1]=f[f.length-1]!^255
   else if(kind==='length')new DataView(f.buffer).setUint32(12,new DataView(f.buffer).getUint32(12)+1)
   else if(kind==='trailing'){const extra=new Uint8Array(f.length+1);extra.set(f);new DataView(extra.buffer).setUint32(16,extra.length-20);f=extra}
   else f=readerFrame({...c,event:kind==='semantic'?{...c.event,version:99}:{version:1,header:{},other_family:true}},true)
   await expect(readFixture(c,f)).rejects.toThrow()
  })
 })
 it('rejects unauthenticated ciphertext BEFORE decompression',async()=>{const c=cases[0]!,context=readerContext(c),sealed=await encryptedReaderFrame(context,readerFrame(c,true)),spy=vi.spyOn(compression,'normalizeAuthenticatedFrame');sealed.ciphertext[0]=sealed.ciphertext[0]!^255;await expect(openBrowserCanonicalObject(asAccountMasterKey(new Uint8Array(32).fill(29)),context,sealed)).rejects.toThrow();expect(spy).not.toHaveBeenCalled();spy.mockRestore()})
 it.each(['accountId','entityId','eventId','entityType','projectId'] as const)('rejects wrong authenticated reference %s',async field=>{const c=cases[0]!,ctx=readerContext(c),sealed=await encryptedReaderFrame(ctx,readerFrame(c,true));await expect(openBrowserCanonicalObject(asAccountMasterKey(new Uint8Array(32).fill(29)),{...ctx,[field]:'wrong'},sealed)).rejects.toThrow()})
 it('retains frozen compression limits/bomb and concatenation rejection',()=>{
  expect(()=>compression.decompressBounded(1,new Uint8Array(10),1000000,1000000)).toThrow('compression_resource_limit')
  expect(()=>compression.decompressBounded(1,new Uint8Array(1048577),1,100)).toThrow('compression_input_limit')
  expect(()=>compression.decompressBounded(1,new Uint8Array(10),8388589,8388589)).toThrow('compression_output_limit')
  expect(()=>compression.decompressBounded(2,new Uint8Array(),1,100)).toThrow('compression_unsupported')
  const c=cases[0]!,f=readerFrame(c,true),payload=f.slice(20),both=new Uint8Array(payload.length*2);both.set(payload);both.set(payload,payload.length);expect(()=>compression.decompressBounded(1,both,new DataView(f.buffer).getUint32(12),1048576)).toThrow()
 })
})
