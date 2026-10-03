import contract from './progressCodecV1.contract.json'
import {canonical} from './projectMetadataCodec'
import {canonicalizeSyncTimestamp} from './syncTimestamp'
import type {DocumentHeader} from './documentCodec'

export interface ProgressFact {
  entry_id:string
  new_total:string
  delta:string
  unit:'symbols'|'A4'|'author_list'|'ficbook_pages'
  occurred_at:string|null
  writing_time:string|null
  writing_day:string
}
export interface ProgressEvent {
  version:1
  migration:{entry_count:number;final_total:string}|null
  header:Omit<DocumentHeader,'operation'> & {operation:'genesis'|'append'|'select'|'rebase'|'correct'|'tombstone'|'migrate'|'adopt_local'}
  base_total:string|null
  entries:ProgressFact[]
  selected_event_id:string|null
  target_entry_id:string|null
  rebased_from:string[]
}
export class ProgressCodecError extends Error {constructor(readonly code:string){super(code)}}
const fail=(code='invalid_progress_payload'):never=>{throw new ProgressCodecError(code)}
const enc=new TextEncoder(),dec=new TextDecoder('utf-8',{fatal:true})
const uuid=(s:unknown)=>typeof s==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(s)
const id=(s:unknown)=>typeof s==='string'&&s.length>0&&enc.encode(s).length<=512&&!s.includes('\0')&&!/[\uD800-\uDFFF]/u.test(s)
const time=(s:unknown)=>{try{return typeof s==='string'&&canonicalizeSyncTimestamp(s)===s}catch{return false}}
const day=(s:unknown)=>typeof s==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(s)&&time(`${s}T00:00:00.000000Z`)
const legacyTime=(s:unknown)=>typeof s==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?$/.test(s)&&(()=>{try{canonicalizeSyncTimestamp(`${s}Z`);return true}catch{return false}})()
function exact(value:unknown,keys:string[]):Record<string,unknown>{if(!value||typeof value!=='object'||Array.isArray(value))fail();const o=value as Record<string,unknown>;if(Object.keys(o).length!==keys.length||keys.some(k=>!Object.hasOwn(o,k)))fail();return o}
/** Fixed decimal strings preserve numeric facts independently of JSON float formatting. */
export function progressMicros(value:unknown):bigint {
  if(typeof value!=='string'||! /^-?(0|[1-9]\d{0,12})\.\d{6}$/.test(value)||value==='-0.000000')fail()
  const n=BigInt((value as string).replace('.',''));if(n>1000000000000000000n||n< -1000000000000000000n)fail('progress_resource_limit');return n
}
export function validateProgressEvent(value:unknown):asserts value is ProgressEvent {
  const e=exact(value,['version','migration','header','base_total','entries','selected_event_id','target_entry_id','rebased_from'])
  const h=exact(e.header,['account_id','device_id','project_id','stage_id','entity_id','event_id','bootstrap_id','metadata_event_id','stage_event_ids','parents','revision','generation','operation','updated_at'])
  if(e.version!==1||['account_id','device_id','event_id','bootstrap_id','metadata_event_id'].some(k=>!uuid(h[k]))||!id(h.project_id)||h.stage_id!==null&&!id(h.stage_id)||!id(h.entity_id)||h.entity_id!==(h.stage_id===null?'project':`stage:${h.stage_id}`)||!time(h.updated_at)||!Number.isSafeInteger(h.revision)||Number(h.revision)<1||h.generation!==h.revision||!contract.operations.includes(String(h.operation)))fail()
  for(const k of ['parents','stage_event_ids']){const a=h[k];if(!Array.isArray(a)||a.length>64||a.some((v,i)=>!uuid(v)||v===h.event_id||i>0&&String(a[i-1])>=String(v)))fail()}
  if((h.stage_id===null)!==((h.stage_event_ids as unknown[]).length===0))fail()
  const parents=h.parents as string[],op=h.operation
  if(op==='genesis'?parents.length!==0||h.revision!==1:parents.length===0||Number(h.revision)<2)fail()
  if(['append','migrate'].includes(String(op))&&parents.length!==1)fail()
  if(!Array.isArray(e.entries)||!Array.isArray(e.rebased_from))fail()
  const entries=e.entries as unknown[],rebased=e.rebased_from as unknown[]
  if(entries.length>1024||rebased.length>1024)fail('progress_resource_limit')
  const seen=new Set<string>()
  for(const raw of entries){const f=exact(raw,['entry_id','new_total','delta','unit','occurred_at','writing_time','writing_day']);if(!id(f.entry_id)||seen.has(String(f.entry_id))||!Object.hasOwn(contract.units,String(f.unit))||!day(f.writing_day))fail();seen.add(String(f.entry_id));if(progressMicros(f.new_total)<0n)fail();progressMicros(f.delta);if(f.occurred_at===null?!legacyTime(f.writing_time):!time(f.occurred_at)||f.writing_time!==null)fail();if(f.writing_time!==null&&String(f.writing_time).slice(0,10)!==f.writing_day)fail()}
  if(rebased.some(v=>!id(v))||new Set(rebased).size!==rebased.length)fail()
  if(op==='genesis'||op==='adopt_local'){const m=exact(e.migration,['entry_count','final_total']);if(!Number.isSafeInteger(m.entry_count)||Number(m.entry_count)<entries.length||Number(m.entry_count)>65536||progressMicros(m.final_total)<0n)fail();if((op==='adopt_local'&&(parents.length===0||Number(h.revision)<2))||e.selected_event_id!==null||e.target_entry_id!==null||rebased.length||entries.length>256||progressMicros(e.base_total)<0n)fail()}
  else {if(e.migration!==null||e.base_total!==null||!uuid(e.selected_event_id)||!parents.includes(String(e.selected_event_id)))fail();if(op==='append'&&(entries.length!==1||e.target_entry_id!==null||rebased.length))fail();if(op==='migrate'&&(!entries.length||entries.length>256||e.target_entry_id!==null||rebased.length))fail();if(op==='select'&&(entries.length||rebased.length||e.target_entry_id!==null))fail();if(['correct','tombstone'].includes(String(op))?!id(e.target_entry_id):e.target_entry_id!==null)fail();if(['rebase','correct','tombstone'].includes(String(op))&&entries.length!==rebased.length)fail()}
}
export async function frameProgressEvent(e:ProgressEvent):Promise<Uint8Array>{validateProgressEvent(e);const body=enc.encode(canonical(e));if(body.length+20>contract.limits.frame_bytes)fail('progress_resource_limit');const f=new Uint8Array(body.length+20);f.set(enc.encode('WORTA-C1'));f.set([1,11,1,0],8);const v=new DataView(f.buffer);v.setUint32(12,body.length);v.setUint32(16,body.length);f.set(body,20);return f}
export async function unframeProgressEvent(f:Uint8Array):Promise<ProgressEvent>{if(f.length>contract.limits.frame_bytes)fail('progress_resource_limit');if(f.length<20||dec.decode(f.subarray(0,8))!=='WORTA-C1'||f[8]!==1||f[9]!==11||f[10]!==1||f[11]!==0)fail('progress_codec_unsupported');const v=new DataView(f.buffer,f.byteOffset,f.byteLength);if(v.getUint32(12)!==f.length-20||v.getUint32(16)!==f.length-20)fail();let raw:string,e:unknown;try{raw=dec.decode(f.subarray(20));e=JSON.parse(raw)}catch{fail()}validateProgressEvent(e);if(canonical(e)!==raw!)fail();return e}
