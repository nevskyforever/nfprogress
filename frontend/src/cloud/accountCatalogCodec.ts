import { canonical, timestamp } from './projectMetadataCodec';
import { ACCOUNT_ENTITY_TYPES, decryptAccountObject, encryptAccountObject, type AccountObjectEnvelope } from '@/crypto/accountObjectCrypto';
import type { AccountMasterKey } from '@/crypto';
export type CatalogType = typeof ACCOUNT_ENTITY_TYPES[number];
export const CATALOG_LIMITS = { entities: 16384, parents: 64, bytes: 4 * 1024 * 1024 } as const;
export interface CatalogHeader {
    account_id: string;
    scope: 'account';
    device_id: string;
    entity_type: CatalogType;
    entity_id: string;
    event_id: string;
    operation: 'create' | 'update' | 'delete' | 'resolution';
    parent_event_ids: string[];
    revision: number;
    generation: number;
    updated_at: string;
}
export interface CatalogDependencies {
    folders: Record<string, string[]>;
    projects: Record<string, {
        bootstrap_id: string;
        metadata_event_id: string;
    }>;
    memberships: Record<string, string[]>;
}
export type CatalogPayload = {
    name: string;
} | {
    folder_id: string | null;
} | {
    ids: string[];
} | null;
export interface CatalogEvent {
    version: 1;
    header: CatalogHeader;
    payload: CatalogPayload;
    dependencies: CatalogDependencies;
    deleted_at: string | null;
}
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const enc = new TextEncoder(), dec = new TextDecoder('utf-8', { fatal: true }), magic = [87, 79, 82, 84, 65, 45, 67, 49];
function fail(): never { throw new TypeError('invalid_catalog_frame'); }
const object = (v: unknown): v is Record<string, unknown> => !!v && typeof v === 'object' && !Array.isArray(v);
const exact = (v: Record<string, unknown>, keys: string[]) => Object.keys(v).length === keys.length && keys.every(k => Object.hasOwn(v, k));
const text = (v: unknown): v is string => typeof v === 'string' && !/[\uD800-\uDFFF]/u.test(v) && enc.encode(v).length > 0 && enc.encode(v).length <= 512;
const ids = (v: unknown): v is string[] => Array.isArray(v) && v.length <= CATALOG_LIMITS.entities && v.every(text) && new Set(v).size === v.length;
const heads = (v: unknown, empty = false): v is string[] => Array.isArray(v) && v.length >= (empty ? 0 : 1) && v.length <= 64 && v.every((s, i) => typeof s === 'string' && UUID.test(s) && (!i || s > v[i - 1]));
export function validateCatalogEvent(v: unknown): asserts v is CatalogEvent {
    if (!object(v) || !exact(v, ['version', 'header', 'payload', 'dependencies', 'deleted_at']) || v.version !== 1 || !object(v.header) || !object(v.dependencies))
        fail();
    const h = v.header, d = v.dependencies;
    if (!exact(h, ['account_id', 'scope', 'device_id', 'entity_type', 'entity_id', 'event_id', 'operation', 'parent_event_ids', 'revision', 'generation', 'updated_at']) || h.scope !== 'account'
        || !['account_id', 'device_id', 'event_id'].every(k => typeof h[k] === 'string' && UUID.test(h[k] as string)) || !text(h.entity_id)
        || !ACCOUNT_ENTITY_TYPES.includes(h.entity_type as CatalogType) || !['create', 'update', 'delete', 'resolution'].includes(String(h.operation))
        || !Number.isSafeInteger(h.revision) || (h.revision as number) < 1 || !Number.isSafeInteger(h.generation) || (h.generation as number) < 1 || !timestamp(h.updated_at)
        || !heads(h.parent_event_ids, true) || h.parent_event_ids.includes(h.event_id as string)
        || (h.operation === 'create' ? h.parent_event_ids.length !== 0 || h.revision !== 1 || h.generation !== 1 : !h.parent_event_ids.length || (h.revision as number) < 2 || (h.generation as number) < 2))
        fail();
    if (!exact(d, ['folders', 'projects', 'memberships']) || !object(d.folders) || !object(d.projects) || !object(d.memberships))
        fail();
    for (const map of [d.folders, d.memberships])
        if (Object.keys(map).length > CATALOG_LIMITS.entities || !Object.entries(map).every(([k, v]) => text(k) && heads(v)))
            fail();
    if (Object.keys(d.projects).length > CATALOG_LIMITS.entities || !Object.entries(d.projects).every(([k, p]) => text(k) && object(p) && exact(p, ['bootstrap_id', 'metadata_event_id']) && [p.bootstrap_id, p.metadata_event_id].every(s => typeof s === 'string' && UUID.test(s))))
        fail();
    if ((h.operation === 'update' || h.operation === 'delete') && h.parent_event_ids.length !== 1) fail();
    const p = v.payload;
    if (h.entity_type === 'folder') {
        if (Object.keys(d.folders).length || Object.keys(d.projects).length || Object.keys(d.memberships).length)
            fail();
        if (p === null ? v.deleted_at !== h.updated_at || !['delete', 'resolution'].includes(String(h.operation)) : !object(p) || !exact(p, ['name']) || !text(p.name) || [...p.name].length > 120 || !p.name.trim() || v.deleted_at !== null || h.operation === 'delete')
            fail();
    }
    else if (h.entity_type === 'folder_membership') {
        if (!object(p) || !exact(p, ['folder_id']) || !(p.folder_id === null || text(p.folder_id)) || !exact(d.projects, [h.entity_id as string]) || Object.keys(d.memberships).length
            || !exact(d.folders, p.folder_id === null ? [] : [p.folder_id]) || (p.folder_id === null ? v.deleted_at !== h.updated_at : v.deleted_at !== null)
            || (h.operation === 'delete' && p.folder_id !== null))
            fail();
    }
    else {
        if (h.entity_id !== h.entity_type || h.operation === 'delete' || v.deleted_at !== null || !object(p) || !exact(p, ['ids']) || !ids(p.ids))
            fail();
        if (h.entity_type === 'folder_order' ? !exact(d.folders, p.ids) || Object.keys(d.projects).length || Object.keys(d.memberships).length
            : !exact(d.projects, p.ids) || Object.keys(d.folders).length || !exact(d.memberships, p.ids))
            fail();
    }
}
export function frameCatalogEvent(e: CatalogEvent): Uint8Array {
    validateCatalogEvent(e);
    const bytes = enc.encode(canonical(e));
    if (bytes.length > CATALOG_LIMITS.bytes)
        fail();
    const frame = new Uint8Array(20 + bytes.length);
    frame.set(magic);
    frame.set([1, 4 + ACCOUNT_ENTITY_TYPES.indexOf(e.header.entity_type), 1, 0], 8);
    const view = new DataView(frame.buffer);
    view.setUint32(12, bytes.length);
    view.setUint32(16, bytes.length);
    frame.set(bytes, 20);
    return frame;
}
export function unframeCatalogEvent(frame: Uint8Array): CatalogEvent {
    if (frame.length < 20 || frame.length > CATALOG_LIMITS.bytes + 20 || !magic.every((b, i) => frame[i] === b) || frame[8] !== 1 || frame[10] !== 1 || frame[11] !== 0)
        fail();
    const view = new DataView(frame.buffer, frame.byteOffset, frame.byteLength);
    if (view.getUint32(12) !== frame.length - 20 || view.getUint32(16) !== frame.length - 20)
        fail();
    let v: unknown;
    try {
        v = JSON.parse(dec.decode(frame.subarray(20)));
    }
    catch {
        fail();
    }
    validateCatalogEvent(v);
    if (frame[9] !== 4 + ACCOUNT_ENTITY_TYPES.indexOf(v.header.entity_type) || canonical(v) !== dec.decode(frame.subarray(20)))
        fail();
    return v;
}
export async function sealCatalogEvent(amk: AccountMasterKey, e: CatalogEvent): Promise<AccountObjectEnvelope> {
    const frame = frameCatalogEvent(e), h = e.header;
    try {
        return await encryptAccountObject(amk, { userId: h.account_id, scope: 'account', entityId: h.entity_id, entityType: h.entity_type }, frame);
    }
    finally {
        frame.fill(0);
    }
}
export async function openCatalogEvent(amk: AccountMasterKey, userId: string, entityId: string, entityType: string, envelope: AccountObjectEnvelope): Promise<CatalogEvent> {
    const bytes = await decryptAccountObject(amk, { userId, scope: 'account', entityId, entityType }, envelope);
    try {
        const e = unframeCatalogEvent(bytes);
        if (e.header.account_id !== userId || e.header.entity_id !== entityId || e.header.entity_type !== entityType)
            fail();
        return e;
    }
    finally {
        bytes.fill(0);
    }
}
