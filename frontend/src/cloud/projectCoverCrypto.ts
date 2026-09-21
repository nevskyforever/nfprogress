import { decryptObjectBytes, encryptObjectBytes, type AccountMasterKey, type ObjectCryptoEnvelope } from '@/crypto'

export const PROJECT_COVER_ENTITY_TYPE = 'project_cover'
export const MAX_PROJECT_COVER_PLAINTEXT_BYTES = 2 * 1024 * 1024

export interface ProjectCoverIdentity {
  userId: string
  projectId: string
  blobId: string
}

function context(identity: ProjectCoverIdentity) {
  return { userId: identity.userId, projectId: identity.projectId, entityId: identity.blobId, entityType: PROJECT_COVER_ENTITY_TYPE }
}

export function createProjectCoverBlobId(): string {
  return crypto.randomUUID()
}

export async function encryptProjectCover(amk: AccountMasterKey, identity: ProjectCoverIdentity, bytes: Uint8Array): Promise<ObjectCryptoEnvelope> {
  if (!(bytes instanceof Uint8Array) || bytes.byteLength > MAX_PROJECT_COVER_PLAINTEXT_BYTES) throw new RangeError('Project cover exceeds 2 MiB.')
  return encryptObjectBytes(amk, context(identity), bytes)
}

export async function decryptProjectCover(amk: AccountMasterKey, identity: ProjectCoverIdentity, envelope: ObjectCryptoEnvelope): Promise<Uint8Array> {
  const plaintext = await decryptObjectBytes(amk, context(identity), envelope)
  if (plaintext.byteLength > MAX_PROJECT_COVER_PLAINTEXT_BYTES) throw new RangeError('Decrypted project cover exceeds 2 MiB.')
  return plaintext
}
