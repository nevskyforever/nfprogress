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
Object.assign(globalThis, { nativeRows, c21: { ...persistence, openBrowserCanonicalObject, frameStructuralEvent, frameProjectMetadata, compressCanonicalFrame, canonical, readerCases, readerFrame, readFixture, deviceFixture, contentIntentFixture, assertLocalSourceInTransaction, metadataFixture, encryptObjectBytes, createNoteSyncPlaintext, encodeNoteSyncPlaintext, sealProjectMetadataEvent, openNoteSyncEvent, decodeBase64Url, encodeBase64Url } })
