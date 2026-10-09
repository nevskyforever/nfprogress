/** Start Vite on an isolated port, then:
 * node scripts/compression/browser-vectors.mjs http://127.0.0.1:5174
 * Uses an empty harness page; never mounts the user's application or contacts its API.
 */
import {createRequire} from 'node:module'
const require=createRequire(new URL('../../frontend/package.json',import.meta.url))
const {chromium}=require('@playwright/test')
const origin=new URL(process.argv[2]||'http://127.0.0.1:5174').origin
const browser=await chromium.launch({headless:true})
try{
 const page=await browser.newPage()
 await page.route(origin+'/',route=>route.fulfill({contentType:'text/html',body:'<!doctype html><title>Compression vectors</title>'}))
 await page.goto(origin+'/')
 const result=await page.evaluate(async()=>{
  const {decompressBounded}=await import('/src/cloud/frameCompression.ts')
  const fixture=(await import('/src/cloud/__fixtures__/frameCompressionV1.json')).default
  const rows=[]
  for(const v of fixture.vectors){const input=new TextEncoder().encode(v.prefix+v.unit.repeat(v.repeat)+v.suffix)
   for(const key of ['ts_hex','rust_hex']){const compressed=Uint8Array.from(v[key].match(/../g).map(x=>parseInt(x,16)))
    const opened=decompressBounded(1,compressed,v.declared,8*1024*1024-20)
    if(opened.length!==input.length||opened.some((b,i)=>b!==input[i]))throw Error('browser vector mismatch')
   }
   rows.push({name:v.name,bytes:input.length})
  }
  return rows
 })
 console.log(JSON.stringify(result))
}finally{await browser.close()}
