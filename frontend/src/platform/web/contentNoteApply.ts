import type { NormalUserAuthRuntime } from '@/auth/userAuth'
import type { AuthoritativeAccountBinding } from '@/auth/accountBinding'
import type { RuntimeKeyContext } from '@/auth/keyContext'
import { BrowserLegacyNoteApply,type BrowserLegacyNoteApplyRuntime,type VerifiedNoteCausalPlan } from './legacyNoteApply'
import type { BrowserSyncScope } from './syncDurability'
/** Explicit production Content entry; shares the accepted Note planner, authority and atomic commit. */
export class BrowserContentNoteApply {
 constructor(private readonly notes:BrowserLegacyNoteApply){}
 bind(auth:NormalUserAuthRuntime,bindings:AuthoritativeAccountBinding,keys:RuntimeKeyContext){return new BrowserContentNoteApplyRuntime(this.notes.bind(auth,bindings,keys))}
}
export class BrowserContentNoteApplyRuntime {
 constructor(private readonly notes:BrowserLegacyNoteApplyRuntime){}
 prepare(scope:BrowserSyncScope,sequence:number){return this.notes.prepareContentOrdinary(scope,sequence)}
 commit(token:VerifiedNoteCausalPlan){return this.notes.commit(token)}
 async apply(scope:BrowserSyncScope,sequence:number){return this.commit(await this.prepare(scope,sequence))}
}
