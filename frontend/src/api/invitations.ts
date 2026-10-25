import { apiRequest } from './client'

/** The invitation secret stays in memory and is never persisted by this client. */
export const invitationApi = {
  accept: (token: string, password: string) => apiRequest<{ code: string; username: string }>(
    '/api/v1/auth/invitations/accept', { method: 'POST', body: { token, password } },
  ),
}
