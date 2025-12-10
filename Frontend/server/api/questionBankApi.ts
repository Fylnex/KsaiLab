/**
 * API клиент для банка вопросов
 * Использует правильный httpClient из app/utils/
 */

import { getHttpClient } from '@/utils/httpClient'

export interface QuestionAuthor {
  user_id: number
  full_name: string
  role: string
  added_at: string
}

export interface QuestionBankEntry {
  id: number
  topic_id: number
  section_id: number | null
  question: string
  question_type: 'single_choice' | 'multiple_choice' | 'open_text'
  options?: string[] | null
  correct_answer: string | number | Array<string | number> | null
  hint?: string | null
  image_url?: string | null
  is_final: boolean
  tags?: string[] | null
  created_by: number
  created_at: string
  updated_at?: string | null
  is_archived: boolean
  section_title?: string | null
  author?: QuestionAuthor | null
}

export interface QuestionBankEntryPayload {
  topic_id: number
  section_id?: number | null
  question: string
  question_type: 'single_choice' | 'multiple_choice' | 'open_text'
  options?: string[] | null
  correct_answer: string | number | Array<string | number> | null
  hint?: string | null
  image_url?: string | null
  is_final?: boolean
}

export interface QuestionBankUpdatePayload {
  section_id?: number | null
  question?: string
  question_type?: 'single_choice' | 'multiple_choice' | 'open_text'
  options?: string[] | null
  correct_answer?: string | number | Array<string | number> | null
  hint?: string | null
  image_url?: string | null
  is_final?: boolean
}

export interface TopicAuthorInfo {
  topic_id: number
  user_id: number
  full_name?: string | null
  role?: string | null
  is_archived: boolean
  added_at?: string | null
  added_by?: number | null
}

export const questionBankApi = {
  /**
   * Создать запись в банке вопросов
   */
  createEntry: async (payload: QuestionBankEntryPayload): Promise<QuestionBankEntry> => {
    const http = getHttpClient()
    // Явно исключаем tags из payload
    const { tags, ...payloadWithoutTags } = payload as QuestionBankEntryPayload & { tags?: unknown }
    const { data } = await http.post<QuestionBankEntry>('/question-bank/create', payloadWithoutTags)
    return data
  },

  /**
   * Получить записи банка вопросов по теме
   */
  listEntriesByTopic: async (
    topicId: number,
    options?: { sectionId?: number | null; includeArchived?: boolean; skip?: number; limit?: number }
  ): Promise<QuestionBankEntry[]> => {
    const http = getHttpClient()
    const params = new URLSearchParams()
    if (options?.sectionId) params.append('section_id', String(options.sectionId))
    if (options?.includeArchived) params.append('include_archived', 'true')
    if (typeof options?.skip === 'number') params.append('skip', String(options.skip))
    if (typeof options?.limit === 'number') params.append('limit', String(options.limit))

    const query = params.toString() ? `?${params.toString()}` : ''
    const { data } = await http.get<QuestionBankEntry[]>(`/question-bank/read/topics/${topicId}${query}`)
    return data
  },

  /**
   * Получить запись банка вопросов по ID
   */
  getEntry: async (entryId: number): Promise<QuestionBankEntry> => {
    const http = getHttpClient()
    const { data } = await http.get<QuestionBankEntry>(`/question-bank/read/entries/${entryId}`)
    return data
  },

  /**
   * Обновить запись в банке вопросов
   */
  updateEntry: async (entryId: number, payload: QuestionBankUpdatePayload): Promise<QuestionBankEntry> => {
    const http = getHttpClient()
    // Явно исключаем tags из payload
    const { tags, ...payloadWithoutTags } = payload as QuestionBankUpdatePayload & { tags?: unknown }
    const { data } = await http.put<QuestionBankEntry>(`/question-bank/update/${entryId}`, payloadWithoutTags)
    return data
  },

  /**
   * Архивировать запись
   */
  archiveEntry: async (entryId: number): Promise<void> => {
    const http = getHttpClient()
    await http.post(`/question-bank/archive/${entryId}/archive`)
  },

  /**
   * Восстановить запись из архива
   */
  restoreEntry: async (entryId: number): Promise<void> => {
    const http = getHttpClient()
    await http.post(`/question-bank/archive/${entryId}/restore`)
  },

  /**
   * Удалить запись навсегда
   */
  deleteEntryPermanently: async (entryId: number): Promise<void> => {
    const http = getHttpClient()
    await http.delete(`/question-bank/archive/${entryId}/permanent`)
  },

  /**
   * Получить авторов темы
   */
  getTopicAuthors: async (topicId: number): Promise<TopicAuthorInfo[]> => {
    const http = getHttpClient()
    const { data } = await http.get<TopicAuthorInfo[]>(`/question-bank/topics/${topicId}/authors`)
    return data
  },

  /**
   * Добавить авторов к теме
   */
  addTopicAuthors: async (topicId: number, userIds: number[]): Promise<void> => {
    const http = getHttpClient()
    await http.post(`/question-bank/topics/${topicId}/authors`, { user_ids: userIds })
  },

  /**
   * Удалить авторов темы
   */
  removeTopicAuthors: async (topicId: number, userIds: number[]): Promise<void> => {
    const http = getHttpClient()
    await http.delete(`/question-bank/topics/${topicId}/authors`, { data: { user_ids: userIds } })
  },
}

export default questionBankApi


