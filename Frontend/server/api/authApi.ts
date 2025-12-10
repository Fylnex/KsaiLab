/**
 * API клиент для аутентификации
 * Использует правильный httpClient из app/utils/
 */

import { getHttpClient } from '@/utils/httpClient'
import type { User } from './types'
import { tokenStorage } from '@/utils/tokenStorage'
import { persistAuthCookies } from '@/utils/authCookies'

interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

interface AuthResponse {
  access_token: string
  refresh_token: string
  user: User
}

export const authApi = {
  /**
   * Вход в систему
   */
  login: async (username: string, password: string): Promise<AuthResponse> => {
    const http = getHttpClient()
    
    // Получаем токены
    const { data: tokenData } = await http.post<LoginResponse>('/auth/login', {
      username,
      password,
    })

    console.log('[authApi] Login response:', tokenData)

    const { access_token, refresh_token } = tokenData

    if (!access_token || !refresh_token) {
      console.error('[authApi] Missing tokens:', { access_token, refresh_token, fullResponse: tokenData })
      throw new Error('No tokens received from login')
    }

    // Сохраняем токены
    tokenStorage.setTokens({
      accessToken: access_token,
      refreshToken: refresh_token,
    })
    persistAuthCookies(access_token, refresh_token)

    // Получаем данные пользователя
    const { data: user } = await http.get<User>('/auth/me')

    return {
      access_token,
      refresh_token,
      user,
    }
  },

  /**
   * Получить текущего пользователя
   */
  getCurrentUser: async (): Promise<User> => {
    const http = getHttpClient()
    const { data } = await http.get<User>('/auth/me')
    return data
  },

  /**
   * Обновить токен доступа
   */
  refreshToken: async (
    refreshToken: string
  ): Promise<{ access_token: string; refresh_token: string }> => {
    const http = getHttpClient()
    
    const { data } = await http.post<LoginResponse>(
      '/auth/refresh',
      {},
      {
        headers: { Authorization: `Bearer ${refreshToken}` },
      }
    )

    const { access_token, refresh_token } = data

    // Сохраняем новые токены
    if (access_token && refresh_token) {
      tokenStorage.setTokens({
        accessToken: access_token,
        refreshToken: refresh_token,
      })
      persistAuthCookies(access_token, refresh_token)
    }

    return { access_token, refresh_token }
  },

  /**
   * Выход из системы
   */
  logout: async (): Promise<void> => {
    const http = getHttpClient()
    try {
      await http.post('/auth/logout')
    } catch (error) {
      console.error('Logout failed:', error)
    }
  },
}


