import{scope}from'./bootstrap.testFixture'
import{type BrowserPrefixInventory}from'./provenPrefixRecords'
export function inventory(f:{db:Record<string,unknown[]>}):BrowserPrefixInventory{const c=f.db.cursors![0] as any;return{rows:structuredClone(f.db.inbox!),out:structuredClone(f.db.outbox!),receipts:structuredClone(f.db.receipts!),bindings:structuredClone(f.db.projectBindings!),owners:structuredClone(f.db.ownerHeads!),history:structuredClone(f.db.legacyNoteHistory!),cursor:{pull_cursor:c?.pull_cursor??0,ack_cursor:c?.ack_cursor??0,proven_prefix:c?.proven_prefix??0,next_local_ordinal:c?.next_local_ordinal??1}}}
export{scope}
