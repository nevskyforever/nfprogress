import sodium from 'libsodium-wrappers-sumo'

import { CryptoError } from './errors'

/** A module singleton: concurrent callers await the same libsodium readiness promise. */
export async function getSodium(): Promise<typeof sodium> {
  try {
    await sodium.ready
    return sodium
  } catch {
    throw new CryptoError('runtime_unavailable')
  }
}
