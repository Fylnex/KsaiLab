/**
 * API клиент для управления группами
 * Использует правильный httpClient из app/utils/
 */

import { getHttpClient } from '@/utils/httpClient'

export interface Group {
  id: number
  name: string
  start_year: number
  end_year: number
  description?: string
  creator_id?: number
  created_at: string
  updated_at: string
  is_archived: boolean
  students_count?: number
  teachers_count?: number
  students?: unknown[]
  teachers?: unknown[]
  topics?: unknown[]
  demo_students?: { id: number; full_name: string; patronymic: string; username: string }[]
  demo_teacher?: { id: number; full_name: string; patronymic: string; username: string }
}

export interface GroupStudent {
  group_id: number
  user_id: number
  status: 'active' | 'inactive'
  joined_at: string
  left_at?: string
  is_archived: boolean
}

export interface GroupTeacher {
  group_id: number
  user_id: number
  created_at: string
  assigned_at: string
  is_archived: boolean
}

export const groupApi = {
  /**
   * Получить список групп
   */
  getGroups: async (params?: {
    skip?: number
    limit?: number
    search?: string
    include_archived?: boolean
    include_counts?: boolean
  }): Promise<Group[]> => {
    const http = getHttpClient()
    const { data } = await http.get<Group[]>('/groups/management/', { params })
    return data
  },

  /**
   * Получить группу по ID
   */
  getGroup: async (
    groupId: number,
    options?: {
      include_students?: boolean
      include_teachers?: boolean
      include_topics?: boolean
    }
  ): Promise<Group> => {
    const http = getHttpClient()
    const params = {
      include_students: options?.include_students ?? true,
      include_teachers: options?.include_teachers ?? true,
      include_topics: options?.include_topics ?? false,
    }
    const { data } = await http.get<Group>(`/groups/management/${groupId}`, { params })
    return data
  },

  /**
   * Создать группу
   */
  createGroup: async (data: {
    name: string
    start_year: number
    end_year: number
    description?: string
  }): Promise<Group> => {
    const http = getHttpClient()
    const response = await http.post<Group>('/groups/management/', data)
    return response.data
  },

  /**
   * Обновить группу
   */
  updateGroup: async (
    groupId: number,
    data: {
      name?: string
      start_year?: number
      end_year?: number
      description?: string
    }
  ): Promise<Group> => {
    const http = getHttpClient()
    const response = await http.put<Group>(`/groups/management/${groupId}`, data)
    return response.data
  },

  /**
   * Удалить группу
   */
  deleteGroup: async (groupId: number): Promise<void> => {
    const http = getHttpClient()
    await http.delete(`/groups/management/${groupId}`)
  },

  /**
   * Получить студентов группы
   */
  getGroupStudents: async (groupId: number): Promise<GroupStudent[]> => {
    const http = getHttpClient()
    const { data } = await http.get<GroupStudent[]>(`/groups/management/${groupId}/students`)
    return data
  },

  /**
   * Добавить студента в группу
   */
  addStudent: async (groupId: number, userId: number): Promise<GroupStudent> => {
    const http = getHttpClient()
    const { data } = await http.post<GroupStudent>(`/groups/management/${groupId}/students/${userId}`)
    return data
  },

  /**
   * Удалить студента из группы
   */
  removeStudent: async (groupId: number, userId: number): Promise<void> => {
    const http = getHttpClient()
    await http.delete(`/groups/management/${groupId}/students/${userId}`)
  },

  /**
   * Получить учителей группы
   */
  getGroupTeachers: async (groupId: number): Promise<GroupTeacher[]> => {
    const http = getHttpClient()
    const { data } = await http.get<GroupTeacher[]>(`/groups/management/${groupId}/teachers`)
    return data
  },

  /**
   * Добавить учителя в группу
   */
  addTeacher: async (groupId: number, userId: number): Promise<GroupTeacher> => {
    const http = getHttpClient()
    const { data } = await http.post<GroupTeacher>(`/groups/management/${groupId}/teachers/${userId}`)
    return data
  },

  /**
   * Удалить учителя из группы
   */
  removeTeacher: async (groupId: number, userId: number): Promise<void> => {
    const http = getHttpClient()
    await http.delete(`/groups/management/${groupId}/teachers/${userId}`)
  },

  /**
   * Архивировать группу
   */
  archiveGroup: async (groupId: number): Promise<void> => {
    const http = getHttpClient()
    await http.post(`/groups/archive/${groupId}/archive`)
  },

  /**
   * Восстановить группу из архива
   */
  restoreGroup: async (groupId: number): Promise<void> => {
    const http = getHttpClient()
    await http.post(`/groups/archive/${groupId}/restore`)
  },

  /**
   * Удалить группу навсегда
   */
  deleteGroupPermanently: async (groupId: number): Promise<void> => {
    const http = getHttpClient()
    await http.delete(`/groups/archive/${groupId}/permanent`)
  },

  /**
   * Массовое добавление студентов в группу
   */
  bulkAddStudents: async (groupId: number, userIds: number[]): Promise<GroupStudent[]> => {
    const http = getHttpClient()
    const { data } = await http.post<GroupStudent[]>(`/groups/management/${groupId}/students/bulk`, {
      user_ids: userIds,
    })
    return data
  },

  /**
   * Массовое удаление студентов из группы
   */
  bulkRemoveStudents: async (groupId: number, userIds: number[]): Promise<void> => {
    const http = getHttpClient()
    await http.delete(`/groups/management/${groupId}/students/bulk`, {
      data: { user_ids: userIds },
    })
  },

  /**
   * Получить группы студента
   */
  getStudentGroups: async (userId: number): Promise<Group[]> => {
    const http = getHttpClient()
    const { data } = await http.get<Group[]>(`/groups/students/${userId}/groups`)
    return data
  },
}


