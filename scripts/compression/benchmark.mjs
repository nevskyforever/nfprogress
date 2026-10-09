/** Non-CI timing evidence. Corpus is deterministic; timing has no pass threshold.
 * node scripts/compression/corpus.mjs > /tmp/corpus.json
 * node scripts/compression/benchmark.mjs /tmp/corpus.json > /tmp/timings.json
 * Optional rejected candidate: C18_BROTLI_PACKAGE=<temporary extracted package>
 */
import fs from 'node:fs'
import {createRequire} from 'node:module'
import {performance} from 'node:perf_hooks'
const require=createRequire(import.meta.url),pako=require('../../frontend/node_modules/pako')
const candidates=[['pako2.1.0',x=>pako.deflate(x,{level:6}),x=>pako.inflate(x)]]
if(process.env.C18_BROTLI_PACKAGE){const b=require(process.env.C18_BROTLI_PACKAGE);candidates.push(['brotli-wasm3.0.1',x=>b.compress(x,{quality:4}),x=>b.decompress(x)])}
const rows=[]
for(const c of JSON.parse(fs.readFileSync(process.argv[2]))){const input=Buffer.from(c.canonical)
 for(const [algorithm,encode,decode]of candidates){const a=performance.now(),compressed=encode(input),b=performance.now(),opened=decode(compressed),end=performance.now();if(!Buffer.from(opened).equals(input))throw Error('roundtrip')
  rows.push({name:c.name,algorithm,input:input.length,output:compressed.length,saved:input.length-compressed.length,percent:100*(1-compressed.length/input.length),compress_ms:b-a,decompress_ms:end-b,rss_process_bytes:process.memoryUsage().rss})}
}
process.stdout.write(JSON.stringify(rows,null,2)+'\n')
