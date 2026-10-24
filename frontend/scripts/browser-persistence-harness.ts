import {bindPrivateMetadataHandoff} from '../src/platform/web/importedMetadataApply'
import {bindPrivateMetadataPrefix} from '../src/platform/web/privateMetadataPrefix'
import {BrowserHistoricalPrefixQualification} from '../src/platform/web/historicalPrefixQualification'
import {BrowserHistoricalContentAuthentication} from '../src/platform/web/historicalContentAuthentication'
import {BrowserV10OrdinaryApply} from '../src/platform/web/v10OrdinaryApply'
import {BrowserV10Recovery} from '../src/platform/web/v10Recovery'
import {BrowserMixedSourceWitness} from '../src/platform/web/mixedSourceWitness'
import {BrowserHistoricalMetadataDependency} from '../src/platform/web/historicalMetadataDependency'
import {BrowserV10Transport} from '../src/platform/web/v10Transport'
import {BrowserResolutionContinuation} from '../src/platform/web/resolutionContinuation'
import {BrowserResolutionPrefix} from '../src/platform/web/resolutionPrefix'
import {BrowserNoteReaderReadiness} from '../src/platform/web/noteReaderReadiness'
import {BrowserResolutionPlanner} from '../src/platform/web/resolutionPlanner'
import {encodeNoteSyncResolutionV2} from '../src/cloud/noteSyncResolutionV2Codec'
import type {VerifiedBrowserDevice} from '../src/platform/web/deviceRegistration'
import * as resolutionRecords from '../src/platform/web/resolutionRecords'
import {inspectResolutionDag} from '../src/platform/web/resolutionDag'
import {authenticateResolutionHistory} from '../src/platform/web/resolutionAuthentication'
import {BrowserContentNoteIntents} from '../src/platform/web/contentNoteIntents'
import type {BrowserSyncTransaction} from '../src/platform/web/syncDurability'
import {openBrowserCanonicalObject} from '../src/platform/web/canonicalReaders'
import {frameStructuralEvent} from '../src/cloud/stageCodec'
import { compressCanonicalFrame } from '../src/cloud/frameCompression'
import { readerCases, readerFrame, readFixture } from '../src/platform/web/canonicalReaders.testFixture'
import { encryptObjectBytes } from '../src/crypto'
import { createNoteSyncPlaintext } from '../src/cloud/encryptedSyncProtocol'
import { encodeNoteSyncPlaintext } from '../src/cloud/noteSyncCodec'
import { assertLocalSourceInTransaction } from '../src/platform/web/localAuthority'
import * as persistence from '../src/platform/web/persistence'
import { NormalUserAuthRuntime } from '../src/auth/userAuth'
import { AuthoritativeAccountBinding } from '../src/auth/accountBinding'
import { RuntimeKeyContext } from '../src/auth/keyContext'
import { asAccountMasterKey, wrapAmkWithPassphrase } from '../src/crypto'
import { encodeBase64Url } from '../src/api/base64url'
import { openNoteSyncEvent } from '../src/cloud/encryptedSyncProtocol'
import { decodeBase64Url } from '../src/api/base64url'
import { canonical, frameProjectMetadata, sealProjectMetadataEvent } from '../src/cloud/projectMetadataCodec'
import type { CurrentUserCryptoRecord } from '../src/api/accountCrypto'

// Isolated harness only: synthetic normal-user transport, actual auth/binding/key runtime and crypto.
// No test key or passphrase is ever stored in IndexedDB or included in production application composition.
async function metadataFixture(session: Awaited<ReturnType<typeof persistence.openBrowserPersistence>>, scope: { canonicalUserId: string; accountId: string; deviceId: string }) {
  const auth = new NormalUserAuthRuntime({ login: async () => ({ access_token: 'fixture-access', refresh_token: 'fixture-refresh', access_expires_in: 60 }), refresh: async () => { throw Error('fixture_no_refresh') }, logout: async () => {}, me: async () => ({ id: scope.canonicalUserId, username: 'fixture', email: 'fixture@example.test', email_verified: true, role: 'user', status: 'active', created_at: '2026-10-12T00:00:00.000000Z' }) })
  await auth.login('fixture', 'fixture')
  const bindings = new AuthoritativeAccountBinding(auth, session)
  const amk = asAccountMasterKey(new Uint8Array(32).fill(77))
  const wrapped = await wrapAmkWithPassphrase(amk, 'disposable-fixture-passphrase')
  const record: CurrentUserCryptoRecord = { provisioned: true, password: { ...wrapped, kdf: { ...wrapped.kdf, salt: encodeBase64Url(wrapped.kdf.salt) }, nonce: encodeBase64Url(wrapped.nonce), ciphertext: encodeBase64Url(wrapped.ciphertext) }, recovery: null }
  const keys = new RuntimeKeyContext(auth, bindings, { get: async () => record })
  await keys.unlockWithPassphrase(scope.accountId, 'disposable-fixture-passphrase')
  amk.fill(0); wrapped.ciphertext.fill(0); wrapped.nonce.fill(0); wrapped.kdf.salt.fill(0)
  return { auth, bindings, keys }
}
// Explicit test-only construction over the REAL session transaction/identity/lock tracking.
// No positive Content gate is added to BrowserPersistence or normal user composition.
function contentIntentFixture(session: Awaited<ReturnType<typeof persistence.openBrowserPersistence>>, meta: Awaited<ReturnType<typeof metadataFixture>>) {
  const internal=session as unknown as {syncTransaction:BrowserSyncTransaction;active:boolean}
  const transaction:BrowserSyncTransaction=(...args)=>internal.syncTransaction(...args)
  return new BrowserContentNoteIntents(transaction,session.localSource,()=>internal.active).bind(meta.auth,meta.bindings,meta.keys)
}
// Explicit test-only planner construction. Normal persistence composition stays unchanged.
function resolutionPlannerFixture(session: Awaited<ReturnType<typeof persistence.openBrowserPersistence>>, meta: Awaited<ReturnType<typeof metadataFixture>>, device: VerifiedBrowserDevice, loseCompletion=false) {
 const internal=session as unknown as {syncTransaction:BrowserSyncTransaction;active:boolean}
 const transaction:BrowserSyncTransaction=async(...args)=>{
  const value=await internal.syncTransaction(...args)
  // Harness-only lost completion signal AFTER the native transaction commits.
  if(loseCompletion&&args[2]==='readwrite')throw Error('DISPOSABLE_LOST_COMPLETION')
  return value
 }
 return new BrowserResolutionPlanner(transaction,session.localSource,()=>internal.active).bind(meta.auth,meta.bindings,meta.keys,device)
}
function resolutionContinuationFixture(session: Awaited<ReturnType<typeof persistence.openBrowserPersistence>>, meta: Awaited<ReturnType<typeof metadataFixture>>, device: VerifiedBrowserDevice, loseCompletion=false) {
 const internal=session as unknown as {syncTransaction:BrowserSyncTransaction;active:boolean}
 const transaction:BrowserSyncTransaction=async(...args)=>{
  const value=await internal.syncTransaction(...args)
  if(loseCompletion&&args[2]==='readwrite')throw Error('DISPOSABLE_H_LOST_COMPLETION')
  return value
 }
 return new BrowserResolutionContinuation(transaction,session.localSource,()=>internal.active).bind(meta.auth,meta.bindings,meta.keys,device)
}
function resolutionPrefixFixture(session: Awaited<ReturnType<typeof persistence.openBrowserPersistence>>, meta: Awaited<ReturnType<typeof metadataFixture>>, device: VerifiedBrowserDevice, loseCompletion=false) {
 const internal=session as unknown as {syncTransaction:BrowserSyncTransaction;active:boolean}
 const transaction:BrowserSyncTransaction=async(...args)=>{const value=await internal.syncTransaction(...args);if(loseCompletion&&args[2]==='readwrite')throw Error('DISPOSABLE_G_LOST_COMPLETION');return value}
 return new BrowserResolutionPrefix(transaction,()=>internal.active).bind(meta.auth,meta.bindings,meta.keys,device)
}
function noteReaderReadinessFixture(session: Awaited<ReturnType<typeof persistence.openBrowserPersistence>>, meta: Awaited<ReturnType<typeof metadataFixture>>, device: VerifiedBrowserDevice) {
 const internal=session as unknown as {syncTransaction:BrowserSyncTransaction;active:boolean}
 return new BrowserNoteReaderReadiness((...args)=>internal.syncTransaction(...args),()=>internal.active).bind(meta.auth,meta.bindings,meta.keys,device)
}
function mixedResolutionPrefixFixture(session: Awaited<ReturnType<typeof persistence.openBrowserPersistence>>, meta: Awaited<ReturnType<typeof metadataFixture>>, device: VerifiedBrowserDevice) {
 const internal=session as unknown as {syncTransaction:BrowserSyncTransaction;active:boolean}
 return new BrowserResolutionPrefix((...args)=>internal.syncTransaction(...args),()=>internal.active).bindMixedSources(meta.auth,meta.bindings,meta.keys,device)
}
function v10TransportFixture(session: Awaited<ReturnType<typeof persistence.openBrowserPersistence>>, meta: Awaited<ReturnType<typeof metadataFixture>>, device: VerifiedBrowserDevice) {
 const internal=session as unknown as {syncTransaction:BrowserSyncTransaction;active:boolean}
 return new BrowserV10Transport((...args)=>internal.syncTransaction(...args),()=>internal.active).bind(meta.auth,meta.bindings,meta.keys,device)
}
function v10RecoveryFixture(session: Awaited<ReturnType<typeof persistence.openBrowserPersistence>>, meta: Awaited<ReturnType<typeof metadataFixture>>, device: VerifiedBrowserDevice) {
 const internal=session as unknown as {syncTransaction:BrowserSyncTransaction;active:boolean}
 return new BrowserV10Recovery((...args)=>internal.syncTransaction(...args),session.localSource,()=>internal.active).bind(meta.auth,meta.bindings,meta.keys,device)
}
function mixedV10RecoveryFixture(session: Awaited<ReturnType<typeof persistence.openBrowserPersistence>>, meta: Awaited<ReturnType<typeof metadataFixture>>, device: VerifiedBrowserDevice) {
 const internal=session as unknown as {syncTransaction:BrowserSyncTransaction;active:boolean}
 return new BrowserV10Recovery((...args)=>internal.syncTransaction(...args),session.localSource,()=>internal.active).bindMixedSources(meta.auth,meta.bindings,meta.keys,device)
}
function v10OrdinaryOwnerFixture(session: Awaited<ReturnType<typeof persistence.openBrowserPersistence>>, meta: Awaited<ReturnType<typeof metadataFixture>>, device: VerifiedBrowserDevice) {
 const internal=session as unknown as {syncTransaction:BrowserSyncTransaction;active:boolean}
 return new BrowserV10OrdinaryApply((...args)=>internal.syncTransaction(...args),session.localSource,()=>internal.active).bind(meta.auth,meta.bindings,meta.keys,device)
}
function mixedSourceWitnessFixture(session: Awaited<ReturnType<typeof persistence.openBrowserPersistence>>, meta: Awaited<ReturnType<typeof metadataFixture>>, device: VerifiedBrowserDevice, beforeSecondRead?:()=>Promise<void>) {
 const internal=session as unknown as {syncTransaction:BrowserSyncTransaction;active:boolean};let reads=0
 const transaction:BrowserSyncTransaction=async(...args)=>{
  if(args[2]!=='readonly')throw Error('WITNESS_WRITE_FORBIDDEN')
  if(++reads===2)await beforeSecondRead?.()
  return internal.syncTransaction(...args)
 }
 return new BrowserMixedSourceWitness(transaction,()=>internal.active).bind(meta.auth,meta.bindings,meta.keys,device)
}
function historicalMetadataFixture(session: Awaited<ReturnType<typeof persistence.openBrowserPersistence>>, meta: Awaited<ReturnType<typeof metadataFixture>>, device: VerifiedBrowserDevice, beforeSecondRead?:()=>Promise<void>) {
 const internal=session as unknown as {syncTransaction:BrowserSyncTransaction;active:boolean};let reads=0
 const transaction:BrowserSyncTransaction=async(...args)=>{
  if(args[2]!=='readonly')throw Error('HISTORICAL_METADATA_WRITE_FORBIDDEN')
  if(++reads===2)await beforeSecondRead?.()
  return internal.syncTransaction(...args)
 }
 return new BrowserHistoricalMetadataDependency(transaction,()=>internal.active).bind(meta.auth,meta.bindings,meta.keys,device)
}
function historicalContentFixture(session: Awaited<ReturnType<typeof persistence.openBrowserPersistence>>, meta: Awaited<ReturnType<typeof metadataFixture>>, device: VerifiedBrowserDevice, beforeSecondRead?:()=>Promise<void>) {
 const internal=session as unknown as {syncTransaction:BrowserSyncTransaction;active:boolean};let reads=0
 const transaction:BrowserSyncTransaction=async(...args)=>{
  if(args[2]!=='readonly')throw Error('HISTORICAL_CONTENT_WRITE_FORBIDDEN')
  if(++reads===2)await beforeSecondRead?.()
  return internal.syncTransaction(...args)
 }
 return new BrowserHistoricalContentAuthentication(transaction,()=>internal.active).bind(meta.auth,meta.bindings,meta.keys,device)
}
function historicalPrefixFixture(session: Awaited<ReturnType<typeof persistence.openBrowserPersistence>>, meta: Awaited<ReturnType<typeof metadataFixture>>, device: VerifiedBrowserDevice, beforeSecondRead?:()=>Promise<void>, abortFirstRead=false) {
 const internal=session as unknown as {syncTransaction:BrowserSyncTransaction;active:boolean};let reads=0
 const transaction:BrowserSyncTransaction=async(...args)=>{
  if(args[2]!=='readonly')throw Error('HISTORICAL_PREFIX_WRITE_FORBIDDEN')
  if(++reads===2)await beforeSecondRead?.()
  if(abortFirstRead&&reads===1){const schedule=args[3];args[3]=(tx,result,abort)=>{schedule(tx,result,abort);tx.abort()}}
  return internal.syncTransaction(...args)
 }
 return new BrowserHistoricalPrefixQualification(transaction,()=>internal.active).bind(meta.auth,meta.bindings,meta.keys,device)
}
/** Acceptance-only injection around real native scheduling, never a runtime bypass. */
function privateMetadataFixture(session:Awaited<ReturnType<typeof persistence.openBrowserPersistence>>,meta:Awaited<ReturnType<typeof metadataFixture>>,device:VerifiedBrowserDevice,fault?:string){
 const internal=session as unknown as {syncTransaction:BrowserSyncTransaction;active:boolean};let active=true,written=false
 const transaction:BrowserSyncTransaction=async(...args)=>{
  if(fault==='postcheck'&&written&&args[2]==='readonly')throw Error('INJECTED_POST_COMMIT_READ')
  if(args[2]==='readwrite'&&fault&&fault!=='postcheck'){
   const schedule=args[3]
   args[3]=(tx,result,abort)=>{
    const proxy=new Proxy(tx,{get:(target,key)=>{
     if(key==='objectStore')return(name:string)=>{
      const store=target.objectStore(name)
      if(name!=='ownerHeads')return store
      return new Proxy(store,{get:(target,key)=>{
       if(key==='put')return(value:unknown)=>{
        const request=target.put(value)
        request.addEventListener('success',()=>{
         if(fault==='abort')tx.abort()
         else if(fault==='request')target.add(value) // Genuine duplicate-key request aborts natively.
         else if(fault==='key')meta.keys.lock()
         else if(fault==='profile')active=false
         else if(fault==='auth')void meta.auth.logout()
         else if(fault==='epoch')void meta.auth.login('fixture','fixture')
        },{once:true})
        return request
       }
       const value=Reflect.get(target,key);return typeof value==='function'?value.bind(target):value
      }})
     }
     const value=Reflect.get(target,key);return typeof value==='function'?value.bind(target):value
    }})
    schedule(proxy,result,abort)
   }
  }
  const result=await internal.syncTransaction(...args);if(args[2]==='readwrite')written=true;return result
 }
 return bindPrivateMetadataHandoff(transaction,()=>internal.active&&active,meta.auth,meta.bindings,meta.keys,device)
}
/** .18 acceptance-only native fault hooks; normal runtime transactions are unchanged. */
function postFMetadataFixture(session:Awaited<ReturnType<typeof persistence.openBrowserPersistence>>,meta:Awaited<ReturnType<typeof metadataFixture>>,device:VerifiedBrowserDevice,fault?:string){
 const internal=session as unknown as {syncTransaction:BrowserSyncTransaction;active:boolean};let active=true,completedKind=''
 const transaction:BrowserSyncTransaction=async(...args)=>{
  if(fault===`${completedKind}-postcheck`&&completedKind&&args[2]==='readonly')throw Error('INJECTED_POST_COMMIT_READ')
  let writtenKind=''
  if(args[2]==='readwrite'){
   const schedule=args[3]
   args[3]=(tx,result,abort)=>{
    const proxy=new Proxy(tx,{get:(target,key)=>{
     if(key==='objectStore')return(name:string)=>{
      const store=target.objectStore(name),kind=name==='ownerHeads'?'owner':name==='cursors'?'prefix':null
      if(!kind)return store
      return new Proxy(store,{get:(target,key)=>{
       if(key==='put')return(value:unknown)=>{
        const request=target.put(value);writtenKind=kind
        request.addEventListener('success',()=>{
         if(fault===`${kind}-abort`)tx.abort()
         else if(fault===`${kind}-request`)target.add(value)
         else if(fault===`${kind}-key`)meta.keys.lock()
         else if(fault===`${kind}-profile`)active=false
         else if(fault===`${kind}-auth`)void meta.auth.logout()
         else if(fault===`${kind}-epoch`)void meta.auth.login('fixture','fixture')
        },{once:true});return request
       }
       const value=Reflect.get(target,key);return typeof value==='function'?value.bind(target):value
      }})
     }
     const value=Reflect.get(target,key);return typeof value==='function'?value.bind(target):value
    }})
    schedule(proxy,result,abort)
   }
  }
  const result=await internal.syncTransaction(...args);if(writtenKind)completedKind=writtenKind;return result
 }
 const current=()=>internal.active&&active
 return{
  recovery:new BrowserV10Recovery(transaction,session.localSource,current).bindPostFMetadata(meta.auth,meta.bindings,meta.keys,device),
  prefix:bindPrivateMetadataPrefix(transaction,current,meta.auth,meta.bindings,meta.keys,device),
 }
}
// Identity-only fixture deliberately provisions no crypto reader/writer capabilities.
async function deviceFixture(session: Awaited<ReturnType<typeof persistence.openBrowserPersistence>>, user: string) {
  const auth = new NormalUserAuthRuntime({ login: async () => ({ access_token: 'fixture-device-access', refresh_token: 'fixture-device-refresh', access_expires_in: 60 }), refresh: async () => { throw Error('fixture_no_refresh') }, logout: async () => {}, me: async () => ({ id: user, username: 'fixture', email: 'fixture@example.test', email_verified: true, role: 'user', status: 'active', created_at: '2026-10-14T00:00:00Z' }) })
  await auth.login('fixture', 'fixture')
  return { auth, runtime: session.device.bind(auth, new AuthoritativeAccountBinding(auth, session)) }
}
async function nativeRows(store: string): Promise<unknown[]> {
  const db = await new Promise<IDBDatabase>((resolve, reject) => { const r = indexedDB.open(persistence.WEB_DATABASE_NAME); r.onsuccess = () => resolve(r.result); r.onerror = () => reject(r.error) })
  try { return await new Promise<unknown[]>((resolve, reject) => { const r = db.transaction(store).objectStore(store).getAll(); r.onsuccess = () => resolve(r.result); r.onerror = () => reject(r.error) }) } finally { db.close() }
}
Object.assign(globalThis, { nativeRows, c21: { ...persistence, postFMetadataFixture, privateMetadataFixture, historicalPrefixFixture, historicalContentFixture, historicalMetadataFixture, mixedV10RecoveryFixture, mixedResolutionPrefixFixture, v10OrdinaryOwnerFixture, mixedSourceWitnessFixture, v10RecoveryFixture, v10TransportFixture, noteReaderReadinessFixture, resolutionPrefixFixture, resolutionContinuationFixture, resolutionPlannerFixture, encodeNoteSyncResolutionV2, resolutionRecords, inspectResolutionDag, authenticateResolutionHistory, openBrowserCanonicalObject, frameStructuralEvent, frameProjectMetadata, compressCanonicalFrame, canonical, readerCases, readerFrame, readFixture, deviceFixture, contentIntentFixture, assertLocalSourceInTransaction, metadataFixture, encryptObjectBytes, createNoteSyncPlaintext, encodeNoteSyncPlaintext, sealProjectMetadataEvent, openNoteSyncEvent, decodeBase64Url, encodeBase64Url } })
