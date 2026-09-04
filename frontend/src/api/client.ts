interface DomainErrorDetail {
  code?: unknown
  message?: unknown
}

interface ErrorEnvelope {
  detail?: DomainErrorDetail | Array<{ msg?: unknown }>
}

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly details: unknown

  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
  }
}

type ApiRequestOptions = Omit<RequestInit, 'body' | 'headers'> & {
  body?: unknown
  rawBody?: BodyInit
  headers?: HeadersInit
}

function configuredBaseUrl(): string {
  const value = import.meta.env.VITE_API_BASE_URL ?? ''
  return value.trim().replace(/\/+$/, '')
}

function requestUrl(path: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${configuredBaseUrl()}${normalizedPath}`
}

async function errorFromResponse(response: Response): Promise<ApiError> {
  let details: unknown
  try {
    details = await response.json()
  } catch {
    details = undefined
  }

  const envelope = details as ErrorEnvelope | undefined
  if (envelope?.detail && !Array.isArray(envelope.detail)) {
    const code = typeof envelope.detail.code === 'string' ? envelope.detail.code : 'api_error'
    const message =
      typeof envelope.detail.message === 'string'
        ? envelope.detail.message
        : `API вернул ошибку ${response.status}.`
    return new ApiError(response.status, code, message, details)
  }

  if (Array.isArray(envelope?.detail)) {
    const validationMessages = envelope.detail
      .map((item) => (typeof item.msg === 'string' ? item.msg : null))
      .filter((message): message is string => message !== null)
    const message = validationMessages.join(' ') || 'Проверьте введённые данные.'
    return new ApiError(response.status, 'request_validation', message, details)
  }

  return new ApiError(
    response.status,
    'api_error',
    `API вернул ошибку ${response.status}.`,
    details,
  )
}

export async function apiRequest<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const {
    body: jsonBody,
    rawBody,
    headers: suppliedHeaders,
    ...requestOptions
  } = options
  const headers = new Headers(suppliedHeaders)
  headers.set('Accept', 'application/json')

  let body: BodyInit | undefined
  if (jsonBody !== undefined && rawBody !== undefined) {
    throw new TypeError('Укажите только JSON body или rawBody.')
  }
  if (rawBody !== undefined) {
    body = rawBody
  } else if (jsonBody !== undefined) {
    headers.set('Content-Type', 'application/json')
    body = JSON.stringify(jsonBody)
  }

  let response: Response
  try {
    response = await fetch(requestUrl(path), {
      ...requestOptions,
      headers,
      body,
    })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw error
    }
    throw new ApiError(
      0,
      'network_error',
      'Не удалось подключиться к nfprogress API.',
      error,
    )
  }

  if (!response.ok) {
    throw await errorFromResponse(response)
  }
  if (response.status === 204) {
    return undefined as T
  }
  return (await response.json()) as T
}

export function apiErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message
  }
  return 'Произошла непредвиденная ошибка.'
}
