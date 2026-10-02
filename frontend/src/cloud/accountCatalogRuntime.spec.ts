// @vitest-environment node
import { describe, it, expect, vi, afterEach } from 'vitest';
import { AccountCatalogRuntime } from './accountCatalogRuntime';
import { NormalUserAuthRuntime } from '@/auth/userAuth';
import { encryptedSyncV2Api } from '@/api/encryptedSyncV2';
import { asAccountMasterKey, type AccountMasterKey } from '@/crypto';
import fixture from './__fixtures__/accountCatalogV1.json';
import type { CatalogEvent } from './accountCatalogCodec';
const catalogEvent = () => structuredClone(fixture) as CatalogEvent;
import type { CatalogPending } from '@/infrastructure/sqlite/accountCatalogRepository';
async function setup() { const e = catalogEvent(), user = e.header.account_id, device = e.header.device_id; const auth = new NormalUserAuthRuntime({ login: vi.fn().mockResolvedValue({ access_token: 'token', refresh_token: 'refresh', access_expires_in: 60 }), refresh: vi.fn(), logout: vi.fn(), me: vi.fn().mockResolvedValue({ id: user, username: 'u', email: 'u@example.test', email_verified: true, role: 'user', status: 'active', created_at: e.header.updated_at }) }); await auth.login('u', 'p'); const context = auth.requireContext(); const bindings = { ensureForCurrentUser: vi.fn(async () => ({ context })) }, identity = { read: vi.fn(async () => ({ local_account_id: 'local', device_id: device })) }, keys = { leaseForAccount: () => ({ canonicalUserId: user, authEpoch: context.authEpoch, isCurrent: () => true, use: (op: (amk: AccountMasterKey) => Promise<unknown>) => op(asAccountMasterKey(new Uint8Array(32))) }) }; const native = { authority: vi.fn(async () => ({ state: 'catalog_local' })), begin: vi.fn(async () => ({ state: 'captured' })), decide: vi.fn(async () => e.header.event_id), pending: vi.fn<() => Promise<CatalogPending[]>>(async () => []), seal: vi.fn(async () => { }), receipt: vi.fn(async () => { }) }, api = { pushAccount: vi.fn(async () => ({ results: [{ event_id: e.header.event_id, server_sequence: 1, duplicate: true }] })) }; vi.spyOn(encryptedSyncV2Api, 'capabilities').mockResolvedValue({ supported_transport_version: 2, writer_transport_version: 3, cutover_epoch: 2 } as never); return { e, device, native, api, runtime: new AccountCatalogRuntime(auth, bindings as never, identity as never, keys as never, native as never, api as never) }; }
afterEach(() => vi.restoreAllMocks());
describe('account catalog runtime', () => {
    it('inspection and empty queue cannot capture migration', async () => { const h = await setup(); await h.runtime.inspectCatalog('local', h.device); await h.runtime.sealCatalog('local', h.device); await h.runtime.uploadCatalog('local', h.device); expect(h.native.begin).not.toHaveBeenCalled(); await h.runtime.beginCatalog('local', h.device); expect(h.native.begin).toHaveBeenCalledTimes(1); });
    it('reuses immutable durable ciphertext and ID after a lost upload response', async () => { const h = await setup(); h.native.pending.mockResolvedValue([{ event: h.e, nonce: null, ciphertext: null }]); await h.runtime.sealCatalog('local', h.device); const args = h.native.seal.mock.calls[0] as unknown as [
        unknown,
        string,
        Uint8Array,
        Uint8Array,
        Uint8Array
    ]; h.native.pending.mockResolvedValue([{ event: h.e, nonce: Array.from(args[3]), ciphertext: Array.from(args[4]) }]); h.api.pushAccount.mockRejectedValueOnce(new Error('lost')); await expect(h.runtime.uploadCatalog('local', h.device)).rejects.toThrow(); expect(h.native.receipt).not.toHaveBeenCalled(); await h.runtime.uploadCatalog('local', h.device); expect(h.api.pushAccount.mock.calls[0]).toEqual(h.api.pushAccount.mock.calls[1]); expect(h.native.seal).toHaveBeenCalledTimes(1); });
});
