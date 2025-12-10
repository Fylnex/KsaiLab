/**
 * API клиент для управления пользователями
 * Использует правильный httpClient из app/utils/
 */

import { getHttpClient } from '@/utils/httpClient'
import type { User } from './types'

interface UserFilters {
  search?: string
  role?: string
  is_active?: boolean
  start_date?: string
  end_date?: string
  exclude_group_id?: number
  available_for_group?: number
}

interface CreateUserPayload {
  username: string
  full_name: string
  password: string
  role: string
  is_active?: boolean
}

interface UpdateUserPayload {
  username?: string
  full_name?: string
  last_login?: string
  is_active?: boolean
  role?: string
}

interface BulkCreateStudentsPayload {
  students: Array<{
    username: string
    full_name: string
    password: string
    role?: string
    is_active?: boolean
  }>
  group_id: number
}

interface BulkCreateStudentsResponse {
  created_students: User[]
  group_assignments: Array<{
    user_id: number
    group_id: number
    status: string
  }>
  total_created: number
  errors: Array<{
    username: string
    error: string
  }>
}

export const userApi = {
  /**
   * Создать нового пользователя
   */
  createUser: async (userData: CreateUserPayload): Promise<User> => {
    const http = getHttpClient()
    const { data } = await http.post<User>('/users/create', userData)
    return data
  },

  /**
   * Получить пользователя по ID
   */
  getUser: async (id: number): Promise<User> => {
    const http = getHttpClient()
    const { data } = await http.get<User>(`/users/read/${id}`)
    return data
  },

  /**
   * Получить всех пользователей с фильтрами
   */
  getAllUsers: async (filters?: UserFilters): Promise<User[]> => {
    const http = getHttpClient()
    const { data } = await http.get<User[]>('/users/read', { params: filters })
    return data
  },

  /**
   * Обновить пользователя
   */
  updateUser: async (id: number, userData: UpdateUserPayload): Promise<User> => {
    const http = getHttpClient()
    const { data } = await http.put<User>(`/users/update/${id}`, userData)
    return data
  },

  /**
   * Удалить пользователя
   */
  deleteUser: async (id: number): Promise<void> => {
    const http = getHttpClient()
    await http.delete(`/users/${id}`)
  },

  /**
   * Массовое обновление ролей
   */
  bulkUpdateRoles: async (userIds: number[], role: string): Promise<User[]> => {
    const http = getHttpClient()
    const { data } = await http.put<User[]>('/users/bulk/roles', {
      userIds,
      role,
    })
    return data
  },

  /**
   * Массовое обновление статуса
   */
  bulkUpdateStatus: async (userIds: number[], is_active: boolean): Promise<User[]> => {
    const http = getHttpClient()
    const { data } = await http.put<User[]>('/users/bulk/status', {
      userIds,
      is_active,
    })
    return data
  },

  /**
   * Сброс пароля пользователя
   */
  resetPassword: async (id: number): Promise<{ message: string; new_password: string }> => {
    const http = getHttpClient()
    const { data } = await http.post(`/users/password/${id}/reset-password`)
    return data
  },

  /**
   * Архивировать пользователя
   */
  archiveUser: async (id: number): Promise<void> => {
    const http = getHttpClient()
    await http.post(`/users/archive/${id}/archive`)
  },

  /**
   * Восстановить пользователя из архива
   */
  restoreUser: async (id: number): Promise<void> => {
    const http = getHttpClient()
    await http.post(`/users/archive/${id}/restore`)
  },

  /**
   * Удалить пользователя навсегда
   */
  deleteUserPermanently: async (id: number): Promise<void> => {
    const http = getHttpClient()
    await http.delete(`/users/archive/${id}/permanent`)
  },

  /**
   * Экспортировать пользователей в CSV
   */
  exportUsers: async (filters?: UserFilters): Promise<Blob> => {
    const http = getHttpClient()
    const { data } = await http.get<ArrayBuffer>('/users/export', {
      params: filters,
      responseType: 'arraybuffer',
    })
    return new Blob([data], { type: 'text/csv' })
  },

  /**
   * Изменить пароль пользователя
   * 
   * Правила доступа:
   * - Администратор может менять пароль всем пользователям
   * - Преподаватель может менять пароль себе и студентам
   * - Студент может менять пароль только себе
   * 
   * @param passwordData - Данные для смены пароля
   * @param passwordData.current_password - Текущий пароль
   * @param passwordData.new_password - Новый пароль
   * @param passwordData.user_id - Опциональный ID пользователя (для админов и преподавателей)
   */
  changePassword: async (
    passwordData: {
      current_password: string
      new_password: string
      user_id?: number
    }
  ): Promise<{ message: string }> => {
    const http = getHttpClient()
    const { data } = await http.put('/users/password/change-password', passwordData)
    return data
  },

  /**
   * Массовое создание студентов с назначением в группу
   */
  bulkCreateStudents: async (
    payload: BulkCreateStudentsPayload
  ): Promise<BulkCreateStudentsResponse> => {
    const http = getHttpClient()
    const { data } = await http.post('/users/bulk/create-students', payload)
    return data
  },
}

export default userApi


