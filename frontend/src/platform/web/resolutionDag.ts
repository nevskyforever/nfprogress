import type { BrowserSyncScope } from './syncDurability'
import type { BrowserNoteCandidate } from './noteHistoryRecords'
import { readFutureHistoryRecord, resolutionBad as bad, resolutionSame as same, type BrowserResolution4 } from './resolutionRecords'

export interface ResolutionDagNode { project: string; note: string; bootstrap: string; event: string; revision: number; parents: string[]; kind: 'candidate'|'original'|'retained' }
export const resolutionNodeKey = (project:string,note:string,bootstrap:string,event:string) => JSON.stringify([project,note,bootstrap,event])
/** Structural only. This result is never an apply or ACK certificate. No storage access. */
export function inspectResolutionDag(scope:BrowserSyncScope,values:readonly unknown[]) {
  if(values.length>16384)bad() // Bounded read-only snapshot; never truncate a graph.
  const history=values.map(r=>readFutureHistoryRecord(r,scope)),keys=new Set<string>(),events=new Map<string,BrowserNoteCandidate|BrowserResolution4>()
  for(const r of history){
    const key=JSON.stringify([r.project_id,r.note_id,r.record_kind,r.record_id]);if(keys.has(key))bad();keys.add(key)
    if(r.record_kind==='candidate'||r.record_kind==='resolution'){if(events.has(r.event_id))bad();events.set(r.event_id,r)}
  }
  const nodes=new Map<string,ResolutionDagNode>(),visiting=new Set<string>()
  const resolve=(project:string,note:string,bootstrap:string,event:string):ResolutionDagNode=>{
    const key=resolutionNodeKey(project,note,bootstrap,event),cached=nodes.get(key);if(cached)return cached
    if(visiting.has(key))bad();visiting.add(key)
    const r=events.get(event)
    if(!r||r.project_id!==project||r.bootstrap_id!==bootstrap)bad()
    let kind:ResolutionDagNode['kind'],parents:string[]=[]
    if(r.record_kind==='candidate'){
      if(r.note_id!==note)bad();kind='candidate'
      if(r.header.parent_event_id!==null){const p=resolve(project,note,bootstrap,r.header.parent_event_id);if(r.header.revision!==p.revision+1)bad();parents=[resolutionNodeKey(project,note,bootstrap,p.event)]}
      else if(r.header.revision!==1)bad()
    }else{
      if(note!==r.note_id&&note!==r.retained_note_id)bad()
      kind=note===r.note_id?'original':'retained'
      const resolved=r.parent_event_ids.map(id=>resolve(project,r.note_id,bootstrap,id))
      if(r.header.revision!==Math.max(...resolved.map(p=>p.revision))+1)bad()
      parents=resolved.map(p=>resolutionNodeKey(project,r.note_id,bootstrap,p.event))
    }
    const result={project,note,bootstrap,event,revision:r.header.revision,parents,kind};nodes.set(key,result);visiting.delete(key);return result
  }
  for(const r of events.values()){resolve(r.project_id,r.note_id,r.bootstrap_id,r.event_id);if(r.record_kind==='resolution'&&r.retained_note_id)resolve(r.project_id,r.retained_note_id,r.bootstrap_id,r.event_id)}
  const cloneOwners=new Map<string,{project:string;bootstrap:string;event:string}>()
  for(const r of events.values())if(r.record_kind==='resolution'&&r.retained_note_id){
    if(cloneOwners.has(r.retained_note_id))bad()
    cloneOwners.set(r.retained_note_id,{project:r.project_id,bootstrap:r.bootstrap_id,event:r.event_id})
  }
  for(const [note,owner] of cloneOwners){
    const anchor=resolutionNodeKey(owner.project,note,owner.bootstrap,owner.event)
    const reaches=(key:string,seen=new Set<string>()):boolean=>{if(key===anchor)return true;if(seen.has(key))return false;seen.add(key);return nodes.get(key)?.parents.some(parent=>reaches(parent,seen))??false}
    for(const [key,n] of nodes)if(n.note===note&&(n.project!==owner.project||n.bootstrap!==owner.bootstrap||!reaches(key)))bad()
  }
  const frontier=(project:string,note:string,bootstrap:string):string[]=>{
    const own=[...nodes.entries()].filter(([,n])=>n.project===project&&n.note===note&&n.bootstrap===bootstrap),consumed=new Set(own.flatMap(([,n])=>n.parents))
    return own.filter(([key])=>!consumed.has(key)).map(([,n])=>n.event).sort()
  }
  for(const r of history){
    if(r.record_kind==='head'){
      const n=resolve(r.project_id,r.note_id,r.bootstrap_id,r.linear_head_event_id)
      if(!same(r.tip_event_ids,frontier(r.project_id,r.note_id,r.bootstrap_id)))bad()
      if(r.record_version===2){const ref=r.node_ref
        if(ref.kind==='candidate'){if(n.kind!=='candidate')bad()}
        else {const source=events.get(ref.resolution_event_id);if(source?.record_kind!=='resolution'||source.record_digest!==ref.resolution_digest||n.kind!==ref.result_role)bad()}
      }else if(n.kind!=='candidate')bad()
    }
    if(r.record_kind==='local_version'){const p=resolve(r.project_id,r.note_id,r.bootstrap_id,r.header.parent_event_id!);if(r.header.revision!==p.revision+1)bad()}
    if(r.record_kind==='group'){
      const p=resolve(r.project_id,r.note_id,r.bootstrap_id,r.common_parent_event_id)
      for(const member of r.members){const v=member.source==='local_unsealed'?history.find(v=>v.record_kind==='local_version'&&v.version_id===member.version_id&&v.project_id===r.project_id&&v.note_id===r.note_id&&v.bootstrap_id===r.bootstrap_id):events.get(member.event_id)
        if(!v||v.record_kind==='resolution'||v.record_kind!=='candidate'&&v.record_kind!=='local_version'||v.project_id!==r.project_id||v.note_id!==r.note_id||v.bootstrap_id!==r.bootstrap_id||v.header.parent_event_id!==p.event||v.header.revision!==r.tip_revision||v.header.revision!==p.revision+1)bad()
      }
    }
  }
  return {history,events,nodes,resolve,frontier}
}
export type ResolutionDag = ReturnType<typeof inspectResolutionDag>
