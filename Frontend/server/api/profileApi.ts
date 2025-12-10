/**
 * API клиент для профиля пользователя
 * Использует правильный httpClient из app/utils/
 */

import { getHttpClient } from '@/utils/httpClient'

export interface Profile {
  user_id: number
  topics: unknown[]
  sections: unknown[]
  subsections: unknown[]
  tests: unknown[]
  generated_at: string
}

export const profileApi = {
  /**
   * Получить профиль текущего пользователя
   */
  getProfile: async (): Promise<Profile> => {
    const http = getHttpClient()
    const { data } = await http.get<Profile>('/profile')
    return data
  },
}


