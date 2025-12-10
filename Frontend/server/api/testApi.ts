/**
 * API клиент для управления тестами
 * Использует правильный httpClient из app/utils/
 */

import { getHttpClient } from '@/utils/httpClient'
import type { Question } from './questionApi'

export interface Test {
  id: number
  title: string
  description?: string
  type: string
  duration?: number
  section_id?: number
  topic_id?: number
  questions?: Question[]
  questions_count?: number
  target_questions?: number | null
  question_ids?: number[] | null // ID вопросов, связанных с тестом (для обычных тестов)
  completion_percentage?: number
  max_attempts?: number
  max_questions_per_attempt?: number | null // Для обратной совместимости
  created_at?: string
  updated_at?: string
  is_archived: boolean
  is_available?: boolean
}

export interface TestStartResponse {
  attempt_id: number
  questions: Question[]
  randomized_config: Record<string, unknown>
}

export interface TestSubmitData {
  attempt_id: number
  answers: Array<{
    question_id: number
    answer: string | number | Array<string | number> | null
  }>
  time_spent: number
}

export interface TestResult {
  id: number
  user_id: number
  test_id: number
  attempt_number: number
  score: number
  time_spent: number
  started_at: string
  completed_at: string
  status: string
  correctCount: number
  totalQuestions: number
}

export interface TestStatus {
  is_available: boolean
  max_attempts: number
  used_attempts: number
  can_start: boolean
  last_attempt?: TestResult
}

export const testApi = {
  /**
   * Получить тест (админ)
   */
  getTest: async (id: number): Promise<Test> => {
    const http = getHttpClient()
    const { data } = await http.get<Test>(`/tests/admin/${id}`)
    return data
  },

  /**
   * Получить все тесты (админ)
   */
  getAllTests: async (): Promise<Test[]> => {
    const http = getHttpClient()
    const { data } = await http.get<Test[]>('/tests/admin/')
    return data
  },

  /**
   * Получить архивные тесты (админ)
   */
  getArchivedTests: async (): Promise<Test[]> => {
    const http = getHttpClient()
    const { data } = await http.get<Test[]>('/tests/admin/', {
      params: { is_archived: true },
    })
    return data
  },

  /**
   * Получить тесты секции (админ)
   */
  getTestsBySection: async (sectionId: number): Promise<Test[]> => {
    const http = getHttpClient()
    const { data } = await http.get<Test[]>(`/tests/admin/by-section/${sectionId}`)
    return data
  },

  /**
   * Получить тесты темы (админ)
   */
  getTestsByTopic: async (topicId: number, options?: { include_archived?: boolean }): Promise<Test[]> => {
    const http = getHttpClient()
    const params =
      options?.include_archived !== undefined ? { include_archived: options.include_archived } : {}
    const { data } = await http.get<Test[]>(`/tests/admin/by-topic/${topicId}`, { params })
    return data
  },

  /**
   * Получить архивные тесты темы (админ)
   */
  getArchivedTestsByTopic: async (topicId: number): Promise<Test[]> => {
    const http = getHttpClient()
    const { data } = await http.get<Test[]>(`/tests/admin/by-topic/${topicId}`, {
      params: { include_archived: true },
    })
    return data.filter((test) => test.is_archived)
  },

  /**
   * Создать тест (админ)
   */
  createTest: async (data: Partial<Test>): Promise<Test> => {
    const http = getHttpClient()
    const { data: result } = await http.post<Test>('/tests/admin/', data)
    return result
  },

  /**
   * Обновить тест (админ)
   */
  updateTest: async (id: number, data: Partial<Test>): Promise<Test> => {
    const http = getHttpClient()
    const { data: result } = await http.put<Test>(`/tests/admin/${id}`, data)
    return result
  },

  /**
   * Удалить тест (админ)
   */
  deleteTest: async (id: number): Promise<void> => {
    const http = getHttpClient()
    await http.delete(`/tests/admin/${id}`)
  },

  /**
   * Архивировать тест (админ)
   */
  archiveTest: async (id: number): Promise<void> => {
    const http = getHttpClient()
    await http.post(`/tests/admin/${id}/archive`)
  },

  /**
   * Восстановить тест из архива (админ)
   */
  restoreTest: async (id: number): Promise<void> => {
    const http = getHttpClient()
    await http.post(`/tests/admin/${id}/restore`)
  },

  /**
   * Удалить тест навсегда (админ)
   */
  deleteTestPermanently: async (id: number): Promise<void> => {
    const http = getHttpClient()
    await http.delete(`/tests/admin/${id}/permanent`)
  },

  /**
   * Получить попытки теста (админ)
   */
  getTestAttempts: async (id: number): Promise<TestResult[]> => {
    const http = getHttpClient()
    const { data } = await http.get<TestResult[]>(`/tests/admin/${id}/attempts`)
    return data
  },

  /**
   * Получить статистику теста (админ)
   */
  getTestStatistics: async (id: number): Promise<unknown> => {
    const http = getHttpClient()
    const { data } = await http.get(`/tests/admin/${id}/statistics`)
    return data
  },

  /**
   * Сбросить попытки теста (админ)
   */
  resetTestAttempts: async (id: number): Promise<void> => {
    const http = getHttpClient()
    await http.post(`/tests/admin/${id}/reset-attempts`)
  },

  /**
   * Сбросить попытки пользователя (админ)
   */
  resetAttempts: async (
    testId: number,
    userId: number
  ): Promise<{ message: string; reset_count: number }> => {
    if (!testId || isNaN(testId)) {
      throw new Error(`Невалидный testId: ${testId}`)
    }
    if (!userId || isNaN(userId)) {
      throw new Error(`Невалидный userId: ${userId}`)
    }
    const http = getHttpClient()
    const { data } = await http.post<{ message: string; reset_count: number }>(
      `/tests/admin/${testId}/reset-attempts`,
      {
        test_id: testId,
        user_id: userId,
      }
    )
    return data
  },

  /**
   * Начать тест (студент)
   */
  startTest: async (testId: number): Promise<TestStartResponse> => {
    const http = getHttpClient()
    const { data } = await http.post<TestStartResponse>(`/tests/student/${testId}/start`)
    return data
  },

  /**
   * Отправить тест (студент)
   */
  submitTest: async (testId: number, submitData: TestSubmitData): Promise<TestResult> => {
    const http = getHttpClient()
    const { data } = await http.post<TestResult>(`/tests/student/${testId}/submit`, submitData)
    return data
  },

  /**
   * Получить результат попытки (студент)
   */
  getAttemptResult: async (attemptId: number): Promise<TestResult> => {
    const http = getHttpClient()
    const { data } = await http.get<TestResult>(`/tests/student/attempts/${attemptId}`)
    return data
  },

  /**
   * Получить все попытки пользователя по тесту (студент)
   */
  getMyAttempts: async (testId: number): Promise<TestResult[]> => {
    const http = getHttpClient()
    const { data } = await http.get<TestResult[]>(`/tests/student/${testId}/my-attempts`)
    return data
  },

  /**
   * Получить доступные тесты для студента
   */
  getAvailableTests: async (): Promise<Test[]> => {
    const http = getHttpClient()
    const { data } = await http.get<Test[]>('/tests/student/available')
    return data
  },

  /**
   * Получить доступные тесты для студента (алиас для getAvailableTests)
   * @deprecated Используйте getAvailableTests
   */
  getAvailableTestsForStudent: async (): Promise<Test[]> => {
    return testApi.getAvailableTests()
  },

  /**
   * Получить доступные тесты по разделу (студент)
   */
  getAvailableTestsBySection: async (sectionId: number): Promise<Test[]> => {
    const http = getHttpClient()
    const { data } = await http.get<Test[]>(`/tests/student/available/by-section/${sectionId}`)
    return data
  },

  /**
   * Получить доступные тесты по теме (студент)
   */
  getAvailableTestsByTopic: async (topicId: number): Promise<Test[]> => {
    const http = getHttpClient()
    const { data } = await http.get<Test[]>(`/tests/student/available/by-topic/${topicId}`)
    return data
  },

  /**
   * Получить тест для студента (с информацией о доступности)
   */
  getTestForStudent: async (testId: number): Promise<Test> => {
    const http = getHttpClient()
    const { data } = await http.get<Test>(`/tests/student/${testId}`)
    return data
  },

  /**
   * Получить статус попытки теста (студент)
   */
  getTestStatus: async (testId: number): Promise<TestStatus> => {
    const http = getHttpClient()
    const { data } = await http.get<TestStatus>(`/tests/student/${testId}/status`)
    return data
  },

  /**
   * Получить попытки студента по тесту
   */
  getStudentTestAttempts: async (testId: number): Promise<TestResult[]> => {
    const http = getHttpClient()
    const { data } = await http.get<TestResult[]>(`/tests/student/${testId}/attempts`)
    return data
  },

  /**
   * Добавить вопросы к тесту (админ/учитель) - использует новую архитектуру связей
   */
  addQuestionsToTest: async (testId: number, questionIds: number[]): Promise<unknown> => {
    const http = getHttpClient()
    const { data } = await http.post(`/questions/tests/links/${testId}/questions`, {
      question_ids: questionIds,
    })
    return data
  },

  /**
   * Заменить все вопросы в тесте (админ/учитель)
   */
  replaceQuestionsInTest: async (testId: number, questionIds: number[]): Promise<unknown> => {
    const http = getHttpClient()
    const { data } = await http.put(`/questions/tests/links/${testId}/questions`, {
      question_ids: questionIds,
    })
    return data
  },
}


