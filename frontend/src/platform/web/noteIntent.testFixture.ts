import { fixture,scope } from './bootstrap.testFixture'
export async function active(){const f=await fixture([]),captured=(await f.capture.capture(scope,f.registered)).binding;const binding=await f.completion.markCompleting(scope,captured);f.db.projectBindings=[{...binding,remote_state:'active',remote_high_water:0}];return f}
export const token=async(f:Awaited<ReturnType<typeof fixture>>)=>(await f.writer.local.readSnapshot(scope,'p')).token
export const intent=async(f:Awaited<ReturnType<typeof fixture>>)=>(await f.writer.list(scope,'p'))[0]!
