/**
 * API клиент для управления темами
 * Использует правильный httpClient из app/utils/
 */

import { getHttpClient } from '@/utils/httpClient'

export interface TopicAuthor {
  id: number
  full_name: string
  username?: string
  email?: string
}

export interface Topic {
  id: number
  title: string
  description?: string
  category?: string
  image?: string
  created_at?: string
  is_archived: boolean
  creator_full_name: string
  authors?: TopicAuthor[]
}

interface TopicPayload extends Partial<Topic> {
  author_ids?: number[]
}

export interface Section {
  id: number
  topic_id: number
  title: string
  content?: string
  description?: string
  order: number
  created_at?: string
  is_archived: boolean
}

export interface SectionWithProgress extends Section {
  is_completed: boolean
  is_available: boolean
  completion_percentage: number
}

export interface MyTopicsResponse {
  topics: Topic[]
}

export const topicApi = {
  /**
   * Создать тему
   */
  createTopic: async (data: TopicPayload): Promise<Topic> => {
    const http = getHttpClient()
    const { data: result } = await http.post<Topic>('/topics/create/', data)
    return result
  },

  /**
   * Получить все темы
   */
  getTopics: async (): Promise<Topic[]> => {
    const http = getHttpClient()
    const { data } = await http.get<Topic[]>('/topics/read/')
    return data
  },

  /**
   * Получить архивные темы
   */
  getArchivedTopics: async (): Promise<Topic[]> => {
    const http = getHttpClient()
    const { data } = await http.get<Topic[]>('/topics/read/', {
      params: {
        include_archived: true,
      },
    })
    // Фильтруем только архивированные темы
    return data.filter((topic: Topic) => topic.is_archived)
  },

  /**
   * Получить тему по ID
   */
  getTopic: async (
    id: number,
    options?: {
      includeSections?: boolean
      includeArchivedSections?: boolean
      includeFinalTests?: boolean
    }
  ): Promise<Topic> => {
    const http = getHttpClient()
    const params = new URLSearchParams()
    if (options?.includeSections) params.append('include_sections', 'true')
    if (options?.includeArchivedSections) params.append('include_archived_sections', 'true')
    if (options?.includeFinalTests) params.append('include_final_tests', 'true')

    const query = params.toString() ? `?${params.toString()}` : ''
    const { data } = await http.get<Topic>(`/topics/read/${id}${query}`)
    return data
  },

  /**
   * Алиас для getTopic
   */
  getTopicById: async (
    id: number,
    options?: {
      includeSections?: boolean
      includeArchivedSections?: boolean
      includeFinalTests?: boolean
    }
  ): Promise<Topic> => {
    return topicApi.getTopic(id, options)
  },

  /**
   * Получить прогресс по теме
   */
  getTopicProgress: async (id: number): Promise<unknown> => {
    const http = getHttpClient()
    const { data } = await http.get(`/topics/read/${id}/progress`)
    return data
  },

  /**
   * Получить секции по теме
   */
  getSectionsByTopic: async (
    topicId: number,
    options?: { include_archived?: boolean }
  ): Promise<Section[]> => {
    const http = getHttpClient()
    const params: any = {
      topic_id: topicId,
    }

    // Добавляем include_archived только если он явно указан
    if (options?.include_archived !== undefined) {
      params.include_archived = options.include_archived
    }

    const { data } = await http.get<Section[]>('/sections/read', {
      params,
    })
    return data
  },

  /**
   * Алиас для getSectionsByTopic (для совместимости)
   */
  getTopicSections: async (
    topicId: number,
    options?: { include_archived?: boolean }
  ): Promise<Section[]> => {
    return topicApi.getSectionsByTopic(topicId, options)
  },

  /**
   * Обновить тему
   */
  updateTopic: async (id: number, data: TopicPayload): Promise<Topic> => {
    const http = getHttpClient()
    const { data: result } = await http.put<Topic>(`/topics/update/${id}`, data)
    return result
  },

  /**
   * Архивировать тему
   */
  archiveTopic: async (id: number): Promise<void> => {
    const http = getHttpClient()
    await http.post(`/topics/archive/${id}/archive`)
  },

  /**
   * Восстановить тему из архива
   */
  restoreTopic: async (id: number): Promise<void> => {
    const http = getHttpClient()
    await http.post(`/topics/archive/${id}/restore`)
  },

  /**
   * Удалить тему навсегда
   */
  deleteTopicPermanently: async (id: number): Promise<void> => {
    const http = getHttpClient()
    await http.delete(`/topics/archive/${id}/permanent`)
  },

  /**
   * Получить мои темы
   */
  getMyTopics: async (): Promise<MyTopicsResponse> => {
    const http = getHttpClient()
    const { data } = await http.get<MyTopicsResponse>('/topics/my-topics/')
    return data
  },

  /**
   * Назначить тему группе
   */
  assignTopicToGroup: async (topicId: number, groupId: number): Promise<void> => {
    const http = getHttpClient()
    await http.post(`/topics/${topicId}/groups/${groupId}`)
  },

  /**
   * Удалить тему из группы
   */
  removeTopicFromGroup: async (topicId: number, groupId: number): Promise<void> => {
    const http = getHttpClient()
    await http.delete(`/topics/${topicId}/groups/${groupId}`)
  },

  /**
   * Получить группы темы
   */
  getTopicGroups: async (topicId: number): Promise<unknown[]> => {
    const http = getHttpClient()
    const { data } = await http.get<unknown[]>(`/topics/${topicId}/groups`)
    return data
  },

  /**
   * Добавить авторов к теме
   */
  addAuthorsToTopic: async (topicId: number, authorIds: number[]): Promise<void> => {
    const http = getHttpClient()
    await http.post(`/topics/${topicId}/authors`, { author_ids: authorIds })
  },

  /**
   * Удалить авторов из темы
   */
  removeAuthorsFromTopic: async (topicId: number, authorIds: number[]): Promise<void> => {
    const http = getHttpClient()
    await http.delete(`/topics/${topicId}/authors`, { data: { author_ids: authorIds } })
  },
}


