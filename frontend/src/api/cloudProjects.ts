import { apiRequest } from './client'

export interface CloudProjectsResponse {
  cloud_project_ids: string[]
  cloud_project_count: number
  max_cloud_projects: number
}

function authorization(accessToken: string): Headers {
  const headers = new Headers()
  headers.set('Authorization', `Bearer ${accessToken}`)
  return headers
}

/** Metadata-only C8 API: it receives a project ID in the path and no content. */
export const cloudProjectsApi = {
  list(accessToken: string): Promise<CloudProjectsResponse> {
    return apiRequest<CloudProjectsResponse>('/api/v1/cloud/projects', {
      headers: authorization(accessToken),
    })
  },

  enable(accessToken: string, projectId: string): Promise<CloudProjectsResponse> {
    return apiRequest<CloudProjectsResponse>(`/api/v1/cloud/projects/${encodeURIComponent(projectId)}`, {
      method: 'POST',
      headers: authorization(accessToken),
    })
  },

  disable(accessToken: string, projectId: string): Promise<void> {
    return apiRequest<void>(`/api/v1/cloud/projects/${encodeURIComponent(projectId)}`, {
      method: 'DELETE',
      headers: authorization(accessToken),
    })
  },
}
