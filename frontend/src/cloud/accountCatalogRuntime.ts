import { AccountObjectReader } from './accountObjectReader';
import { frameCatalogEvent, sealCatalogEvent, validateCatalogEvent } from './accountCatalogCodec';
import { SQLiteAccountCatalogRepository, type CatalogDecision, type CatalogView } from '@/infrastructure/sqlite/accountCatalogRepository';
import { encryptedSyncV3Api } from '@/api/encryptedSyncV3';
import { StaleAuthContextError, type NormalUserAuthRuntime } from '@/auth/userAuth';
import { KeyNotProvisionedError, type RuntimeKeyContext } from '@/auth/keyContext';
import type { AuthoritativeAccountBinding } from '@/auth/accountBinding';
import type { CloudIdentityRepository } from '@/infrastructure/sqlite/cloudIdentityRepository';
const now = () => new Date().toISOString().replace(/(\.\d{3})Z$/, '$1000Z');
export class AccountCatalogRuntime extends AccountObjectReader {
    constructor(auth: NormalUserAuthRuntime, bindings: AuthoritativeAccountBinding, identity: CloudIdentityRepository, keys: RuntimeKeyContext, private readonly catalog = new SQLiteAccountCatalogRepository(), private readonly catalogApi = encryptedSyncV3Api) { super(auth, bindings, identity, keys); }
    async inspectCatalog(accountId: string, deviceId: string): Promise<CatalogView> { const { scope, context } = await this.scope(accountId, deviceId); const view = await this.catalog.authority(scope); this.assertCurrent(context); return view; }
    async beginCatalog(accountId: string, deviceId: string): Promise<CatalogView> { await this.requireMode3(accountId, deviceId); const { scope, context } = await this.scope(accountId, deviceId); const view = await this.catalog.begin(scope, now()); this.assertCurrent(context); return view; }
    async decideCatalog(accountId: string, deviceId: string, decision: CatalogDecision): Promise<string> { await this.requireMode3(accountId, deviceId); const { scope, context } = await this.scope(accountId, deviceId); const id = await this.catalog.decide(scope, decision, now()); this.assertCurrent(context); return id; }
    async sealCatalog(accountId: string, deviceId: string): Promise<number> {
        await this.requireMode3(accountId, deviceId);
        const { scope, context } = await this.scope(accountId, deviceId);
        const items = await this.catalog.pending(scope, false, now());
        for (const { event } of items) {
            validateCatalogEvent(event);
            const h = event.header;
            if (h.account_id !== context.userId || h.device_id !== deviceId)
                throw new TypeError('account_scope_rejected');
            const lease = this.keys.leaseForAccount(accountId);
            if (!lease)
                throw new KeyNotProvisionedError();
            if (!lease.isCurrent() || lease.canonicalUserId !== context.userId || lease.authEpoch !== context.authEpoch)
                throw new StaleAuthContextError();
            await lease.use(async (amk) => { const sealed = await sealCatalogEvent(amk, event); this.assertCurrent(context); const frame = frameCatalogEvent(event); try {
                await this.catalog.seal(scope, h.event_id, frame, sealed.nonce, sealed.ciphertext);
            }
            finally {
                frame.fill(0);
            } });
        }
        return items.length;
    }
    async uploadCatalog(accountId: string, deviceId: string): Promise<number> {
        await this.requireMode3(accountId, deviceId);
        const { scope, context } = await this.scope(accountId, deviceId);
        const items = await this.catalog.pending(scope, true, now());
        for (const { event, nonce, ciphertext } of items) {
            validateCatalogEvent(event);
            const h = event.header;
            if (!nonce || !ciphertext || h.account_id !== context.userId || h.device_id !== deviceId)
                throw new TypeError('account_scope_rejected');
            const pushed = await this.auth.authorized(token => this.catalogApi.pushAccount(token, deviceId, [{ event: { event_id: h.event_id, canonical_user_id: h.account_id, scope: 'account', entity_id: h.entity_id, entity_type: h.entity_type, operation: event.deleted_at === null ? 'upsert' : 'delete', revision: h.revision, updated_at: h.updated_at, deleted_at: event.deleted_at }, object: { crypto_version: 2, aad_version: 2, nonce: Uint8Array.from(nonce), ciphertext: Uint8Array.from(ciphertext) } }]));
            this.assertCurrent(context);
            if (pushed.context.userId !== context.userId || pushed.context.authEpoch !== context.authEpoch)
                throw new StaleAuthContextError();
            const r = pushed.value.results[0];
            if (pushed.value.results.length !== 1 || r?.event_id !== h.event_id)
                throw new TypeError('catalog_receipt_mismatch');
            await this.catalog.receipt(scope, h.event_id, r.server_sequence);
        }
        return items.length;
    }
}
