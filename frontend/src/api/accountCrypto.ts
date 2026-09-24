import { apiRequest } from './client'

export interface PasswordWrappedAmkWireRecord {
  crypto_version: number
  wrapping_version: number
  kdf: {
    kdf_version: number
    algorithm: string
    salt: string
    opslimit: number
    memlimit: number
  }
  nonce: string
  ciphertext: string
}

export interface RecoveryWrappedAmkWireRecord {
  crypto_version: number
  wrapping_version: number
  nonce: string
  ciphertext: string
}

export interface InitialAccountCryptoProvisioningRequest {
  password: PasswordWrappedAmkWireRecord
  recovery: RecoveryWrappedAmkWireRecord
}

export type CurrentUserCryptoRecord =
  | { provisioned: false; password: null; recovery: null }
  | { provisioned: true; password: PasswordWrappedAmkWireRecord; recovery: RecoveryWrappedAmkWireRecord | null }

export interface AccountCryptoTransport {
  get(accessToken: string): Promise<CurrentUserCryptoRecord>
}

export interface AccountCryptoProvisioningTransport extends AccountCryptoTransport {
  provision(accessToken: string, request: InitialAccountCryptoProvisioningRequest): Promise<CurrentUserCryptoRecord>
}

export const accountCryptoApi: AccountCryptoProvisioningTransport = {
  get(accessToken: string): Promise<CurrentUserCryptoRecord> {
    return apiRequest('/api/v1/account/crypto', {
      headers: new Headers({ Authorization: `Bearer ${accessToken}` }),
    })
  },
  provision(accessToken: string, request: InitialAccountCryptoProvisioningRequest): Promise<CurrentUserCryptoRecord> {
    return apiRequest('/api/v1/account/crypto', {
      method: 'POST',
      headers: new Headers({ Authorization: `Bearer ${accessToken}` }),
      body: request,
    })
  },
}
