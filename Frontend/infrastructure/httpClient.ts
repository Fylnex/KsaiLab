/**
 * Infrastructure: HTTP Client
 * HTTP клиент для работы с API бэкенда
 * Использует $fetch из Nuxt для универсальной работы на сервере и клиенте
 */

interface HttpClientOptions {
  headers?: Record<string, string>
  timeout?: number
  [key: string]: unknown
}

export interface HttpClientResponse<T> {
  data: T
}

export interface HttpClient {
  get<T>(url: string, options?: HttpClientOptions): Promise<HttpClientResponse<T>>
  post<T>(url: string, body?: unknown, options?: HttpClientOptions): Promise<HttpClientResponse<T>>
  put<T>(url: string, body?: unknown, options?: HttpClientOptions): Promise<HttpClientResponse<T>>
  delete<T>(url: string, options?: HttpClientOptions): Promise<HttpClientResponse<T>>
}

/**
 * Получить базовый URL API
 */
function getApiBaseUrl(): string {
  const apiUrl = process.env.NUXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'
  return apiUrl
}

/**
 * Получить токен доступа из хранилища
 */
function getAccessToken(): string | null {
  if (import.meta.server) {
    try {
      const cookie = useCookie('access_token')
      return cookie.value || null
    } catch {
      return null
    }
  } else {
    try {
      return localStorage.getItem('access_token')
    } catch {
      return null
    }
  }
}

/**
 * Создает HTTP клиент с автоматической авторизацией
 */
export function getHttpClient(): HttpClient {
  const baseUrl = getApiBaseUrl()

  const createHeaders = (customHeaders?: Record<string, string>): Record<string, string> => {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...customHeaders,
    }

    const token = getAccessToken()
    if (token) {
      headers.Authorization = `Bearer ${token}`
    }

    return headers
  }

  const defaultTimeout = 60000 // 60 секунд по умолчанию

  const fetchWithTimeout = async <T>(
    url: string,
    options: {
      method: string
      headers: Record<string, string>
      body?: unknown
      timeout?: number
      [key: string]: unknown
    }
  ): Promise<T> => {
    const timeout = options.timeout || defaultTimeout

    try {
      const response = await $fetch<T>(url, {
        ...options,
        timeout,
      })
      return response
    } catch (error: any) {
      // Обработка ошибок таймаута
      if (error.name === 'AbortError' || error.message?.includes('timeout')) {
        throw new Error(`Request timeout after ${timeout}ms: ${url}`)
      }
      throw error
    }
  }

  return {
    async get<T>(url: string, options?: HttpClientOptions): Promise<HttpClientResponse<T>> {
      const response = await fetchWithTimeout<T>(`${baseUrl}${url}`, {
        method: 'GET',
        headers: createHeaders(options?.headers),
        timeout: options?.timeout,
        ...options,
      })
      return { data: response }
    },

    async post<T>(url: string, body?: unknown, options?: HttpClientOptions): Promise<HttpClientResponse<T>> {
      const response = await fetchWithTimeout<T>(`${baseUrl}${url}`, {
        method: 'POST',
        headers: createHeaders(options?.headers),
        body,
        timeout: options?.timeout,
        ...options,
      })
      return { data: response }
    },

    async put<T>(url: string, body?: unknown, options?: HttpClientOptions): Promise<HttpClientResponse<T>> {
      const response = await fetchWithTimeout<T>(`${baseUrl}${url}`, {
        method: 'PUT',
        headers: createHeaders(options?.headers),
        body,
        timeout: options?.timeout,
        ...options,
      })
      return { data: response }
    },

    async delete<T>(url: string, options?: HttpClientOptions): Promise<HttpClientResponse<T>> {
      const response = await fetchWithTimeout<T>(`${baseUrl}${url}`, {
        method: 'DELETE',
        headers: createHeaders(options?.headers),
        timeout: options?.timeout,
        ...options,
      })
      return { data: response }
    },
  }
}

