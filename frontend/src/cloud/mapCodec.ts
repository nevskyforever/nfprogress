import { normalizeAuthenticatedFrame } from './frameCompression'
import contract from './mapCodecV1.contract.json'
import {canonical} from './projectMetadataCodec'
import {canonicalizeSyncTimestamp} from './syncTimestamp'

export const MAP_CODEC_ID=9
export const MAX_MAP_FRAME_BYTES=contract.limits.frame_bytes
type ObjectValue=Record<string,unknown>
export interface MapHeader {
 account_id:string;device_id:string;project_id:string;stage_id:string|null;entity_id:string;event_id:string;
 bootstrap_id:string;metadata_event_id:string;stage_event_ids:string[];parents:string[];
 revision:number;generation:number;operation:'create'|'update'|'delete'|'resolution';updated_at:string
}
export interface MapEvent {version:1;header:MapHeader;mutation:'upsert'|'delete';map:{data:ObjectValue;annotations:ObjectValue}|null;deleted_at:string|null}
export class MapCodecError extends Error {constructor(readonly code:string){super(code)}}
function fail(code='invalid_map_payload'):never{throw new MapCodecError(code)}
const encoder=new TextEncoder(),decoder=new TextDecoder('utf-8',{fatal:true})
const uuid=(v:unknown):v is string=>typeof v==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(v)
function obj(v:unknown):ObjectValue {if(!v||typeof v!=='object'||Array.isArray(v))fail();return v as ObjectValue}
function list(v:unknown):unknown[]{if(!Array.isArray(v))fail();return v}
function text(v:unknown,max:number):v is string {
 if(typeof v!=='string'||[...v].length>max||v.includes('\0'))return false
 for(let i=0;i<v.length;i++){const c=v.charCodeAt(i);if(c>=0xd800&&c<=0xdbff){const n=v.charCodeAt(++i);if(!(n>=0xdc00&&n<=0xdfff))return false}else if(c>=0xdc00&&c<=0xdfff)return false}
 return true
}
const id=(v:unknown):v is string=>text(v,512)&&!!v&&encoder.encode(v).length<=512
function timestamp(v:unknown):boolean{if(!text(v,64))return false;try{return canonicalizeSyncTimestamp(v)===v}catch{return false}}
function fields(v:unknown,kind:keyof typeof contract.fields,required:string[]=[]):ObjectValue {
 const o=obj(v),allowed=contract.fields[kind] as readonly string[]
 if(required.some(k=>!Object.hasOwn(o,k)))fail()
 if(Object.keys(o).some(k=>!allowed.includes(k)))fail('map_unsupported_extension')
 return o
}
function exact(v:unknown,keys:string[]):ObjectValue{const o=obj(v);if(Object.keys(o).length!==keys.length||keys.some(k=>!Object.hasOwn(o,k)))fail();return o}
function strings(v:unknown,count:number,length:number){const a=list(v);if(a.length>count||a.some(v=>!text(v,length)))fail()}
const coordinate=(v:unknown):v is number=>typeof v==='number'&&Number.isFinite(v)&&Math.abs(v)<=1e9
function point(v:unknown){const p=fields(v,'position',['x','y']);if(!coordinate(p.x)||!coordinate(p.y))fail()}
function style(v:unknown){if(Object.values(fields(v,'style')).some(v=>!text(v,2048)&&!coordinate(v)))fail()}
function resourcePreflight(values:unknown[]){
 const stack=values.map(value=>({value,depth:0}));let bytes=0
 const stringBytes=(value:string)=>{let size=2;for(const c of value){const code=c.codePointAt(0)!;size+=c==='"'||c==='\\'||['\n','\r','\t','\b','\f'].includes(c)?2:code<32?6:code<128?1:code<2048?2:code<65536?3:4}return size}
 while(stack.length){const {value,depth}=stack.pop()!;if(depth>contract.limits.depth*2+32)fail('map_resource_limit')
  if(typeof value==='string')bytes+=stringBytes(value)
  else if(Array.isArray(value)){bytes+=2+Math.max(0,value.length-1);for(const child of value)stack.push({value:child,depth:depth+1})}
  else if(value!==null&&typeof value==='object'){const entries=Object.entries(value);bytes+=2+Math.max(0,entries.length-1);for(const [key,child] of entries){bytes+=stringBytes(key)+1;stack.push({value:child,depth:depth+1})}}
  else {const scalar=JSON.stringify(value);if(scalar===undefined)fail();bytes+=scalar.length}
  if(bytes>MAX_MAP_FRAME_BYTES-20)fail('map_resource_limit')
 }
}
export function validateMap(data:unknown,annotations:unknown):Map<string,string>{
 resourcePreflight([data,annotations])
 const d=fields(data,'map',['nodeData']),ids=new Set<string>(),notes=new Map<string,string>(),children=new Map<string,number>();let count=0
 function node(v:unknown,depth:number,free:boolean){
  if(depth>contract.limits.depth||count++>=contract.limits.nodes)fail('map_resource_limit')
  const n=fields(v,'node',['id','topic','children'])
  if(!id(n.id)||!text(n.topic,300000)||ids.has(n.id))fail();ids.add(n.id)
  const cs=list(n.children);children.set(n.id,cs.length)
  for(const k of ['root','expanded','nfprogressFreeRoot','nfprogressNote'])if(Object.hasOwn(n,k)&&typeof n[k]!=='boolean')fail()
  if(Object.hasOwn(n,'direction')&&(!Number.isInteger(n.direction)||Number(n.direction)<0||Number(n.direction)>2))fail()
  if(Object.hasOwn(n,'style'))style(n.style);if(Object.hasOwn(n,'position'))point(n.position)
  for(const k of ['hyperLink','branchColor'])if(Object.hasOwn(n,k)&&!text(n[k],8192))fail()
  for(const k of ['tags','icons'])if(Object.hasOwn(n,k))strings(n[k],100,512)
  if(Object.hasOwn(n,'image')){const image=fields(n.image,'image',['url','width','height']);if(!text(image.url,MAX_MAP_FRAME_BYTES)||['width','height'].some(k=>!coordinate(image[k])||Number(image[k])<=0||Number(image[k])>1e6)||Object.hasOwn(image,'fit')&&!text(image.fit,32))fail()}
  if(n.nfprogressNote===true){if(!free)fail('map_note_link_invalid');notes.set(n.id,n.topic)}
  cs.forEach(c=>node(c,depth+1,free))
 }
 node(d.nodeData,0,false);if(Object.hasOwn(d,'freeNodes'))list(d.freeNodes).forEach(n=>node(n,0,true))
 const floating=new Set<string>()
 if(Object.hasOwn(d,'nfprogressFloatingItems')){
  const items=list(d.nfprogressFloatingItems);if(items.length+count>contract.limits.nodes)fail('map_resource_limit')
  for(const value of items){const item=fields(value,'floating',['id','kind','text','x','y']);if(!id(item.id)||!text(item.text,300000)||!['node','note'].includes(String(item.kind))||floating.has(item.id))fail();floating.add(item.id);point({x:item.x,y:item.y});if(['x','y'].some(k=>Number(item[k])<0||Number(item[k])>100))fail();if(ids.has(item.id)){if(item.kind!=='note'||notes.get(item.id)!==item.text)fail('map_note_link_invalid')}else if(item.kind==='note')notes.set(item.id,item.text)}
  for(const value of items){const item=obj(value);if(Object.hasOwn(item,'parentId')&&(item.kind!=='node'||!id(item.parentId)||item.parentId===item.id||!floating.has(item.parentId)))fail()}
  const parents=new Map<string,string>();for(const value of items){const item=obj(value);if(typeof item.parentId==='string')parents.set(String(item.id),item.parentId)}
  const done=new Set<string>();for(const start of parents.keys()){const path=new Set<string>();let current:string|undefined=start;while(current!==undefined&&!done.has(current)){if(path.has(current))fail();path.add(current);current=parents.get(current)}for(const key of path)done.add(key)}
 }
 const refs=new Set<string>();let referenceCount=0
 for(const [key,kind,required] of [['arrows','arrow',['id','from','to']],['summaries','summary',['id','parent','start','end','label']],['nfprogressFloatingLinks','link',['id','fromType','from','toType','to']]] as const){
  if(!Object.hasOwn(d,key))continue
  for(const value of list(d[key])){
   if(++referenceCount>contract.limits.references)fail('map_resource_limit')
   const item=fields(value,kind,[...required]);if(!id(item.id)||refs.has(item.id))fail();refs.add(item.id)
   if(Object.hasOwn(item,'style'))style(item.style);if(Object.hasOwn(item,'label')&&!text(item.label,300000))fail()
   if(kind==='summary'){
    if(!id(item.parent)||!ids.has(item.parent)||['start','end'].some(k=>!Number.isSafeInteger(item[k])||Number(item[k])<0||Number(item[k])>=50000)||Number(item.start)>Number(item.end)||Object.hasOwn(item,'nfprogressFreeSelf')&&typeof item.nfprogressFreeSelf!=='boolean')fail()
    if(item.nfprogressFreeSelf===true){if(item.start!==0||item.end!==0)fail()}else if(Number(item.end)>=children.get(item.parent)!)fail('map_reference_missing')
   }else{
    for(const end of ['from','to']){const target=item[end];if(!id(target))fail();const known=kind==='link'?(item[end+'Type']==='floating'?floating.has(target):item[end+'Type']==='node'&&ids.has(target)):ids.has(target);if(!known)fail('map_reference_missing')}
    for(const k of ['delta1','delta2'])if(Object.hasOwn(item,k))point(item[k]);if(Object.hasOwn(item,'bidirectional')&&typeof item.bidirectional!=='boolean')fail()
   }
  }
 }
 if(Object.hasOwn(d,'direction')&&(!Number.isInteger(d.direction)||Number(d.direction)<0||Number(d.direction)>2))fail()
 if(Object.hasOwn(d,'compact')&&typeof d.compact!=='boolean')fail()
 if(Object.hasOwn(d,'meta'))fields(d.meta,'meta')
 if(Object.hasOwn(d,'theme')){const theme=fields(d.theme,'theme',['name','type','palette','cssVar']);if(!text(theme.name,512)||!text(theme.type,64))fail();strings(theme.palette,256,512);const css=obj(theme.cssVar);if(Object.keys(css).length>128||Object.entries(css).some(([k,v])=>!k.startsWith('--')||encoder.encode(k).length>128||!text(v,2048)))fail()}
 const a=obj(annotations),noteIds=new Set<string>();if(Object.keys(a).length>50000||Object.keys(a).length!==notes.size)fail('map_note_link_invalid')
 for(const [source,value] of Object.entries(a)){
  if(!notes.has(source))fail('map_note_link_invalid')
  const n=fields(value,'annotation',[...contract.fields.annotation]);fields(n.metadata,'meta');if(!id(n.note_id)||noteIds.has(n.note_id)||!text(n.title,500)||!text(n.color,32)||typeof n.pinned!=='boolean'||typeof n.archived!=='boolean'||!Number.isSafeInteger(n.sort_order)||Number(n.sort_order)<0)fail();noteIds.add(n.note_id)
  if(!timestamp(n.created_at))fail();strings(n.tags,100,512)
  const checks=list(n.checklist),checkIds=new Set<string>();if(checks.length>500)fail('map_resource_limit')
  for(const value of checks){const c=fields(value,'checklist',['id','text','checked']);if(!id(c.id)||checkIds.has(c.id)||!text(c.text,1000)||typeof c.checked!=='boolean')fail();checkIds.add(c.id)}
 }
 return notes
}
export async function mapEntityId(stage:string|null):Promise<string>{if(stage===null)return 'project-map';if(!id(stage))fail();const hash=await crypto.subtle.digest('SHA-256',encoder.encode(stage));return 'stage-map-'+Array.from(new Uint8Array(hash),b=>b.toString(16).padStart(2,'0')).join('')}
export async function validateMapEvent(value:unknown):Promise<void>{
 resourcePreflight([value])
 const e=exact(value,['version','header','mutation','map','deleted_at']),h=exact(e.header,['account_id','device_id','project_id','stage_id','entity_id','event_id','bootstrap_id','metadata_event_id','stage_event_ids','parents','revision','generation','operation','updated_at'])
 if(e.version!==1||['account_id','device_id','event_id','bootstrap_id','metadata_event_id'].some(k=>!uuid(h[k]))||!id(h.project_id)||h.stage_id!==null&&!id(h.stage_id)||h.entity_id!==await mapEntityId(h.stage_id as string|null)||!Number.isSafeInteger(h.revision)||Number(h.revision)<1||h.generation!==h.revision||!timestamp(h.updated_at))fail()
 const parents=list(h.parents),stages=list(h.stage_event_ids);if((h.stage_id===null)!==(stages.length===0))fail()
 for(const ids of [parents,stages])if(ids.length>64||ids.some((p,i)=>!uuid(p)||p===h.event_id||i>0&&String(ids[i-1])>=p))fail()
 if(h.operation==='create'){if(parents.length||h.revision!==1)fail()}else if(h.operation==='update'||h.operation==='delete'){if(parents.length!==1||Number(h.revision)<2)fail()}else if(h.operation==='resolution'){if(parents.length<2||Number(h.revision)<2)fail()}else fail()
 if(e.mutation==='upsert'){if(e.deleted_at!==null||h.operation==='delete')fail();const m=exact(e.map,['data','annotations']);validateMap(m.data,m.annotations)}else if(e.mutation==='delete'){if(e.map!==null||e.deleted_at!==h.updated_at||!['delete','resolution'].includes(String(h.operation)))fail()}else fail()
}
export async function frameMapEvent(e:MapEvent):Promise<Uint8Array>{await validateMapEvent(e);const body=encoder.encode(canonical(e));if(body.length+20>MAX_MAP_FRAME_BYTES)fail('map_resource_limit');const bytes=new Uint8Array(body.length+20);bytes.set([87,79,82,84,65,45,67,49,1,9,1,0]);const view=new DataView(bytes.buffer);view.setUint32(12,body.length);view.setUint32(16,body.length);bytes.set(body,20);return bytes}
export async function unframeMapEvent(bytes:Uint8Array):Promise<MapEvent>{
  if (bytes.length >= 20 && bytes[11] !== 0 && [9].includes(bytes[9]!) && [1].includes(bytes[10]!)) bytes = normalizeAuthenticatedFrame(bytes, [9], [1], MAX_MAP_FRAME_BYTES-20)

 if(bytes.length>MAX_MAP_FRAME_BYTES)fail('map_resource_limit');if(bytes.length<20||!bytes.subarray(0,12).every((b,i)=>b===[87,79,82,84,65,45,67,49,1,9,1,0][i]))fail('map_codec_unsupported')
 const view=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength);if(view.getUint32(12)!==bytes.length-20||view.getUint32(16)!==bytes.length-20)fail()
 let raw:string,value:unknown;try{raw=decoder.decode(bytes.subarray(20));value=JSON.parse(raw)}catch{fail()}
 await validateMapEvent(value);if(canonical(value)!==raw!)fail();return value as MapEvent
}
