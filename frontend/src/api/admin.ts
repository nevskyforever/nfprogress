import { apiRequest } from './client'

export interface AdminTokens { access_token: string; refresh_token: string; access_expires_in: number }
export interface AdminUser { id: string; username: string; email: string; email_verified: boolean; role: string; status: string; registration_mode_at_signup: string | null; created_at: string; max_cloud_projects_override: number | null; effective_max_cloud_projects: number }
export interface AdminUsers { users: AdminUser[]; total: number; limit: number; offset: number }
export interface RegistrationSettings { mode: 'open' | 'approval' | 'closed'; max_users: number | null; active_users: number }
export interface ReservedUsername { username_normalized: string; created_at: string }
export interface AccountMe { id: string; username: string; email: string; email_verified: boolean; role: string; status: string; created_at: string }

let tokens: AdminTokens | null = null

function authorized<T>(path: string, options: Parameters<typeof apiRequest<T>>[1] = {}): Promise<T> {
  if (!tokens) return Promise.reject(new Error('Административная сессия не открыта.'))
  return apiRequest<T>(path, { ...options, headers: { ...options.headers, Authorization: `Bearer ${tokens.access_token}` } })
}

export const adminSession = {
  active: () => tokens !== null,
  clear: () => { tokens = null },
  async login(username: string, password: string): Promise<AccountMe> {
    tokens = await apiRequest<AdminTokens>('/api/v1/auth/login', { method: 'POST', body: { username, password } })
    const account = await authorized<AccountMe>('/api/v1/account/me')
    if (account.role !== 'admin' || account.status !== 'active') {
      await this.logout()
      throw new Error('Для этой учётной записи нет доступа администратора.')
    }
    return account
  },
  async refresh(): Promise<void> {
    if (!tokens) throw new Error('Административная сессия не открыта.')
    tokens = await apiRequest<AdminTokens>('/api/v1/auth/refresh', { method: 'POST', body: { refresh_token: tokens.refresh_token } })
  },
  async logout(): Promise<void> {
    const current = tokens
    tokens = null
    if (current) await apiRequest<void>('/api/v1/auth/logout', { method: 'POST', headers: { Authorization: `Bearer ${current.access_token}` } })
  },
}

export const adminApi = {
  users: (query = '') => authorized<AdminUsers>(`/api/v1/admin/users${query ? `?${query}` : ''}`),
  lifecycle: (id: string, action: 'approve' | 'reject' | 'block' | 'unblock') => authorized<AdminUser>(`/api/v1/admin/users/${id}/${action}`, { method: 'POST' }),
  revoke: (id: string) => authorized<{ code: string }>(`/api/v1/admin/users/${id}/sessions/revoke`, { method: 'POST' }),
  userLimit: (id: string, max_cloud_projects_override: number | null) => authorized(`/api/v1/admin/users/${id}/limits`, { method: 'PATCH', body: { max_cloud_projects_override } }),
  registration: () => authorized<RegistrationSettings>('/api/v1/admin/registration'),
  saveRegistration: (body: Partial<Pick<RegistrationSettings, 'mode' | 'max_users'>>) => authorized<RegistrationSettings>('/api/v1/admin/registration', { method: 'PATCH', body }),
  limits: () => authorized<{ max_cloud_projects: number }>('/api/v1/admin/limits'),
  saveLimits: (max_cloud_projects: number) => authorized<{ max_cloud_projects: number }>('/api/v1/admin/limits', { method: 'PATCH', body: { max_cloud_projects } }),
  reserved: () => authorized<ReservedUsername[]>('/api/v1/admin/reserved-usernames'),
  addReserved: (username: string) => authorized<ReservedUsername>('/api/v1/admin/reserved-usernames', { method: 'POST', body: { username } }),
  removeReserved: (username: string) => authorized<{ code: string }>(`/api/v1/admin/reserved-usernames?${new URLSearchParams({ username })}`, { method: 'DELETE' }),
}
