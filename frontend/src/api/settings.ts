import { apiRequest } from './client'
import type { SettingsResponse, SettingsValues } from '@/types/content'

export const settingsApi = {
  get(signal?: AbortSignal): Promise<SettingsResponse> {
    return apiRequest<SettingsResponse>('/api/settings', { signal })
  },

  update(values: SettingsValues): Promise<SettingsResponse> {
    return apiRequest<SettingsResponse>('/api/settings', {
      method: 'PATCH',
      body: { values },
    })
  },

  acceptUserAgreement(agreementId: string): Promise<SettingsResponse> {
    return apiRequest<SettingsResponse>('/api/settings/user-agreement/accept', {
      method: 'POST',
      body: { agreement_id: agreementId },
    })
  },
}
