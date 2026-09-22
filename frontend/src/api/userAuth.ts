import { apiRequest } from './client'

export interface UserAuthTokens {
  access_token: string
  refresh_token: string
  access_expires_in: number
}

export interface CurrentUserAccount {
  id: string
  username: string
  email: string
  email_verified: boolean
  role: string
  status: string
  created_at: string
}

function authorization(accessToken: string): Headers {
  return new Headers({ Authorization: `Bearer ${accessToken}` })
}

export const userAuthApi = {
  login(username: string, password: string): Promise<UserAuthTokens> {
    return apiRequest('/api/v1/auth/login', { method: 'POST', body: { username, password } })
  },
  refresh(refreshToken: string): Promise<UserAuthTokens> {
    return apiRequest('/api/v1/auth/refresh', { method: 'POST', body: { refresh_token: refreshToken } })
  },
  me(accessToken: string): Promise<CurrentUserAccount> {
    return apiRequest('/api/v1/account/me', { headers: authorization(accessToken) })
  },
  logout(accessToken: string): Promise<void> {
    return apiRequest('/api/v1/auth/logout', { method: 'POST', headers: authorization(accessToken) })
  },
}

export type UserAuthTransport = typeof userAuthApi
