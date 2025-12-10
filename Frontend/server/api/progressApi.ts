/**
 * API клиент для управления прогрессом
 * Использует правильный httpClient из app/utils/
 */

import { getHttpClient } from '@/utils/httpClient'

export interface StudentProgress {
  completedTests: number
  averageScore: number
  lastActivity: string
  testHistory: {
    testId: number
    score: number
    date: string
  }[]
  lastTestId?: number | null
  lastTestBestScore?: number | null
  lastTestCompletedAt?: string | null
}

export interface TopicProgress {
  id: number
  user_id: number
  topic_id: number
  status: string
  completion_percentage: number
  last_accessed: string
  created_at: string
  updated_at: string
  time_spent: number  // Время прохождения темы в секундах
}

export interface SectionProgress {
  id: number
  user_id: number
  section_id: number
  status: string
  completion_percentage: number
  last_accessed: string
  created_at: string
  updated_at: string
  time_spent: number  // Время прохождения секции в секундах
}

export interface SubsectionProgress {
  id: number
  user_id: number
  subsection_id: number
  is_viewed: boolean
  viewed_at?: string
  created_at: string
  updated_at: string
  time_spent_seconds?: number
  completion_percentage?: number
  is_completed?: boolean
}

export interface TestAttempt {
  id: number
  user_id: number
  test_id: number
  attempt_number: number
  score: number | null
  time_spent?: number
  answers?: unknown
  started_at: string
  completed_at?: string
  created_at: string
  updated_at: string
}

export const progressApi = {
  /**
   * Получить прогресс по темам
   */
  getTopicProgressList: async (userId?: number): Promise<TopicProgress[]> => {
    const http = getHttpClient()
    const { data } = await http.get<TopicProgress[]>('/progress/topics', {
      params: userId ? { user_id: userId } : {},
    })
    return data
  },

  /**
   * Получить прогресс по конкретной теме
   */
  getTopicProgress: async (
    userId: number,
    topicId: number
  ): Promise<{ percentage: number; time_spent: number } | null> => {
    try {
      const progressList = await progressApi.getTopicProgressList(userId)
      const topicProgress = progressList.find((progress) => progress.topic_id === topicId)

      if (!topicProgress) {
        return null
      }

      return {
        percentage: topicProgress.completion_percentage || 0,
        time_spent: topicProgress.time_spent || 0,  // Используем реальное значение из API
      }
    } catch (error) {
      console.error(`Ошибка получения прогресса для пользователя ${userId} по теме ${topicId}:`, error)
      return null
    }
  },

  /**
   * Получить прогресс по секциям
   */
  getSectionProgressList: async (userId?: number): Promise<SectionProgress[]> => {
    const http = getHttpClient()
    const { data } = await http.get<SectionProgress[]>('/progress/sections', {
      params: userId ? { user_id: userId } : {},
    })
    return data
  },

  /**
   * Получить прогресс по подсекциям
   */
  getSubsectionProgressList: async (userId?: number): Promise<SubsectionProgress[]> => {
    const http = getHttpClient()
    const { data } = await http.get<SubsectionProgress[]>('/progress/subsections', {
      params: userId ? { user_id: userId } : {},
    })
    return data
  },

  /**
   * Получить прогресс по конкретной подсекции
   */
  getSubsectionProgress: async (
    userId: number,
    subsectionId: number
  ): Promise<{ percentage: number; time_spent: number } | null> => {
    try {
      const http = getHttpClient()
      const { data: progressList } = await http.get<SubsectionProgress[]>('/progress/subsections', {
        params: {
          user_id: userId,
          subsection_ids: String(subsectionId),
        },
      })

      const subsectionProgress = progressList.find((progress) => progress.subsection_id === subsectionId)

      if (!subsectionProgress) {
        return null
      }

      return {
        percentage: subsectionProgress.completion_percentage || 0,
        time_spent: subsectionProgress.time_spent_seconds || 0,
      }
    } catch (error) {
      console.error(`Ошибка получения прогресса для пользователя ${userId} по подразделу ${subsectionId}:`, error)
      return null
    }
  },

  /**
   * Получить попытки тестов
   */
  getTestAttempts: async (userId?: number): Promise<TestAttempt[]> => {
    const http = getHttpClient()
    const { data } = await http.get<TestAttempt[]>('/progress/tests', {
      params: userId ? { user_id: userId } : {},
    })
    return data
  },

  /**
   * Получить обзор студента
   */
  getStudentOverview: async (): Promise<unknown> => {
    const http = getHttpClient()
    const { data } = await http.get('/analytics/student/overview/')
    return data
  },

  /**
   * Получить детальный прогресс студента
   */
  getStudentDetailedProgress: async (): Promise<unknown> => {
    const http = getHttpClient()
    const { data } = await http.get('/analytics/student/detailed/')
    return data
  },

  /**
   * Получить историю активности студента
   */
  getStudentActivityTimeline: async (): Promise<unknown> => {
    const http = getHttpClient()
    const { data } = await http.get('/analytics/student/timeline/')
    return data
  },

  /**
   * Получить достижения студента
   */
  getStudentAchievements: async (): Promise<unknown> => {
    const http = getHttpClient()
    const { data } = await http.get('/analytics/student/achievements/')
    return data
  },

  /**
   * Получить обзор студентов (учитель)
   */
  getTeacherStudentsOverview: async (): Promise<unknown> => {
    const http = getHttpClient()
    const { data } = await http.get('/analytics/teacher/overview/students')
    return data
  },

  /**
   * Получить обзор групп (учитель)
   */
  getTeacherGroupsOverview: async (): Promise<unknown> => {
    const http = getHttpClient()
    const { data } = await http.get('/analytics/teacher/overview/groups')
    return data
  },

  /**
   * Получить обзор контента (учитель)
   */
  getTeacherContentOverview: async (): Promise<unknown> => {
    const http = getHttpClient()
    const { data } = await http.get('/analytics/teacher/overview/content')
    return data
  },

  /**
   * Получить детальную аналитику студента (учитель)
   */
  getDetailedStudentAnalytics: async (studentId: number): Promise<unknown> => {
    const http = getHttpClient()
    const { data } = await http.get(`/analytics/teacher/detailed/student/${studentId}`)
    return data
  },

  /**
   * Получить детальную аналитику группы (учитель)
   */
  getDetailedGroupAnalytics: async (groupId: number): Promise<unknown> => {
    const http = getHttpClient()
    const { data } = await http.get(`/analytics/teacher/detailed/group/${groupId}`)
    return data
  },

  /**
   * Получить детальную аналитику темы (учитель)
   */
  getDetailedTopicAnalytics: async (topicId: number): Promise<unknown> => {
    const http = getHttpClient()
    const { data } = await http.get(`/analytics/teacher/detailed/topic/${topicId}`)
    return data
  },

  /**
   * Получить обзор платформы (админ)
   */
  getPlatformOverview: async (): Promise<unknown> => {
    const http = getHttpClient()
    const { data } = await http.get('/analytics/admin/overview/platform')
    return data
  },

  /**
   * Получить обзор пользователей (админ)
   */
  getUsersOverview: async (): Promise<unknown> => {
    const http = getHttpClient()
    const { data } = await http.get('/analytics/admin/overview/users')
    return data
  },

  /**
   * Получить обзор производительности (админ)
   */
  getPerformanceOverview: async (): Promise<unknown> => {
    const http = getHttpClient()
    const { data} = await http.get('/analytics/admin/overview/performance')
    return data
  },

  /**
   * Получить прогресс студента (deprecated - используйте getStudentOverview)
   */
  getStudentProgress: async (studentId: number): Promise<StudentProgress> => {
    const testAttempts = await progressApi.getTestAttempts(studentId)
    const completedAttempts = testAttempts.filter((attempt) => attempt.completed_at)

    const testsScoreMap = completedAttempts.reduce<Map<number, { bestScore: number }>>((map, attempt) => {
      const attemptScore = attempt.score ?? 0
      const existing = map.get(attempt.test_id)

      if (!existing || attemptScore > existing.bestScore) {
        map.set(attempt.test_id, { bestScore: attemptScore })
      }

      return map
    }, new Map())

    const completedTests = testsScoreMap.size
    const averageScore =
      completedTests > 0
        ? Math.round(
            Array.from(testsScoreMap.values()).reduce((sum, { bestScore }) => sum + bestScore, 0) / completedTests
          )
        : 0

    const sortedAttempts = [...completedAttempts].sort(
      (a, b) => new Date(b.completed_at || '').getTime() - new Date(a.completed_at || '').getTime()
    )
    const lastCompletedAttempt = sortedAttempts[0]

    const lastActivity = lastCompletedAttempt?.completed_at || new Date().toISOString()
    const lastTestId = lastCompletedAttempt?.test_id ?? null
    const lastTestBestScore = lastTestId ? testsScoreMap.get(lastTestId)?.bestScore ?? null : null
    const lastTestCompletedAt = lastCompletedAttempt?.completed_at ?? null

    const testHistory = completedAttempts.map((attempt) => ({
      testId: attempt.test_id,
      score: attempt.score || 0,
      date: attempt.completed_at || new Date().toISOString(),
    }))

    return {
      completedTests,
      averageScore,
      lastActivity,
      testHistory,
      lastTestId,
      lastTestBestScore,
      lastTestCompletedAt,
    }
  },
}


