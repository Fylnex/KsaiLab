/**
 * API клиент для управления вопросами
 * Использует правильный httpClient из app/utils/
 */

import { getHttpClient } from '@/utils/httpClient'

export interface Question {
  id: number
  test_id: number
  question: string
  question_type: string
  options?: string[]
  correct_answer?: string | number | Array<string | number> | null
  hint?: string
  is_final: boolean
  image_url?: string
  created_at?: string
  updated_at?: string
  is_archived: boolean
}

export const questionApi = {
  /**
   * Создать вопрос
   */
  createQuestion: async (
    data: Omit<Partial<Question>, 'id' | 'created_at' | 'updated_at' | 'is_archived'>
  ): Promise<Question> => {
    const http = getHttpClient()
    const { data: result } = await http.post<Question>('/questions/create', data)
    return result
  },

  /**
   * Получить вопросы теста
   */
  getQuestionsByTestId: async (testId: number): Promise<Question[]> => {
    const http = getHttpClient()
    const { data } = await http.get<Question[]>(`/questions/read/test/${testId}`)
    return data
  },

  /**
   * Получить все вопросы
   */
  getAllQuestions: async (): Promise<Question[]> => {
    const http = getHttpClient()
    const { data } = await http.get<Question[]>('/questions/read/all')
    return data
  },

  /**
   * Получить вопрос по ID
   */
  getQuestion: async (id: number): Promise<Question> => {
    const http = getHttpClient()
    const { data } = await http.get<Question>(`/questions/read/${id}`)
    return data
  },

  /**
   * Обновить вопрос
   */
  updateQuestion: async (id: number, data: Partial<Question>): Promise<Question> => {
    const http = getHttpClient()
    const { data: result } = await http.put<Question>(`/questions/update/${id}`, data)
    return result
  },

  /**
   * Архивировать вопрос
   */
  archiveQuestion: async (id: number): Promise<void> => {
    const http = getHttpClient()
    await http.post(`/questions/archive/${id}`)
  },

  /**
   * Восстановить вопрос из архива
   */
  restoreQuestion: async (id: number): Promise<void> => {
    const http = getHttpClient()
    await http.post(`/questions/archive/restore/${id}`)
  },

  /**
   * Удалить вопрос навсегда
   */
  deleteQuestionPermanently: async (id: number): Promise<void> => {
    const http = getHttpClient()
    await http.delete(`/questions/archive/permanent/${id}`)
  },

  /**
   * Добавить вопросы к тесту
   */
  addQuestionsToTest: async (testId: number, questionIds: number[]): Promise<void> => {
    const http = getHttpClient()
    await http.post(`/questions/tests/${testId}/add-questions`, { question_ids: questionIds })
  },

  /**
   * Алиас для getQuestionsByTestId (deprecated)
   */
  getAllQuestionsByTestId: async (testId: number): Promise<Question[]> => {
    return questionApi.getQuestionsByTestId(testId)
  },
}


