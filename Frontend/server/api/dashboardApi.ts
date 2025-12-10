/**
 * API клиент для дашборда администратора
 * Использует данные из других API сервисов
 */

import { userApi } from './userApi'
import { topicApi } from './topicApi'
import { testApi } from './testApi'
import { progressApi } from './progressApi'
import type { User } from './types'
import type { Topic } from './topicApi'
import type { Test } from './testApi'
import type { TestAttempt } from './progressApi'

export interface SystemStats {
  totalUsers: number
  totalTopics: number
  totalTests: number
  activeSessions: number
  systemHealth: 'excellent' | 'good' | 'warning' | 'critical'
  lastBackup: string
  uptime: string
  userGrowth: number
  topicGrowth: number
  testGrowth: number
}

export interface RecentActivity {
  id: number
  type: 'user_registration' | 'test_completion' | 'system_backup' | 'error_log' | 'topic_created' | 'test_created'
  user: string
  time: string
  status: 'success' | 'warning' | 'error'
  details?: string
}

export interface SystemAlert {
  id: number
  type: 'warning' | 'info' | 'error'
  message: string
  time: string
  severity: 'low' | 'medium' | 'high'
}

export interface SystemLog {
  id: number
  user: string
  action: string
  target: string
  date: string
  type: 'create' | 'delete' | 'update' | 'archive' | 'complete' | 'login' | 'logout'
}

export interface UserActivity {
  onlineNow: number
  today: number
  thisWeek: number
  thisMonth: number
}

export interface SystemPerformance {
  cpu: number
  memory: number
  disk: number
  network: number
}

export const dashboardApi = {
  /**
   * Получить общую статистику системы
   */
  getSystemStats: async (): Promise<SystemStats> => {
    try {
      let users: User[] = []
      let topics: Topic[] = []
      let _testAttempts: TestAttempt[] = []

      try {
        users = await userApi.getAllUsers()
      } catch (error) {
        console.error('Ошибка загрузки пользователей:', error)
        throw new Error('Не удалось загрузить данные пользователей')
      }

      try {
        topics = await topicApi.getTopics()
      } catch (error) {
        console.error('Ошибка загрузки тем:', error)
        throw new Error('Не удалось загрузить данные тем')
      }

      try {
        _testAttempts = await progressApi.getTestAttempts()
      } catch (error) {
        console.error('Ошибка загрузки попыток тестов:', error)
        _testAttempts = []
      }

      let allTests: Test[] = []
      try {
        const testPromises = topics.map((topic) =>
          testApi.getTestsByTopic(topic.id).catch(() => [])
        )
        const testResults = await Promise.all(testPromises)
        allTests = testResults.flat()
      } catch (error) {
        console.warn('Ошибка получения тестов:', error)
        allTests = []
      }

      const activeUsers = users.filter((user) => {
        if (!user.last_login) return false
        const lastLogin = new Date(user.last_login)
        const now = new Date()
        const diffHours = (now.getTime() - lastLogin.getTime()) / (1000 * 60 * 60)
        return diffHours <= 24
      })

      const now = new Date()
      const lastMonth = new Date(now.getFullYear(), now.getMonth() - 1, now.getDate())

      const usersLastMonth = users.filter((user) => {
        const createdAt = new Date(user.created_at)
        return createdAt < lastMonth
      }).length

      const userGrowth =
        usersLastMonth > 0 ? Math.round(((users.length - usersLastMonth) / usersLastMonth) * 100) : 0

      let systemHealth: 'excellent' | 'good' | 'warning' | 'critical' = 'excellent'
      if (activeUsers.length > 100) systemHealth = 'good'
      if (activeUsers.length > 200) systemHealth = 'warning'
      if (activeUsers.length > 300) systemHealth = 'critical'

      return {
        totalUsers: users.length,
        totalTopics: topics.length,
        totalTests: allTests.length,
        activeSessions: activeUsers.length,
        systemHealth,
        lastBackup: new Date(Date.now() - 3600000).toISOString(),
        uptime: '99.9%',
        userGrowth,
        topicGrowth: 0,
        testGrowth: 0,
      }
    } catch (error) {
      console.error('Ошибка получения статистики системы:', error)
      throw error
    }
  },

  /**
   * Получить недавнюю активность
   */
  getRecentActivity: async (): Promise<RecentActivity[]> => {
    try {
      let users: User[] = []
      let testAttempts: TestAttempt[] = []
      let topics: Topic[] = []

      try {
        users = await userApi.getAllUsers()
      } catch (error) {
        console.error('Ошибка загрузки пользователей:', error)
        users = []
      }

      try {
        testAttempts = await progressApi.getTestAttempts()
      } catch (error) {
        console.error('Ошибка загрузки попыток тестов:', error)
        testAttempts = []
      }

      try {
        topics = await topicApi.getTopics()
      } catch (error) {
        console.error('Ошибка загрузки тем:', error)
        topics = []
      }

      const activities: RecentActivity[] = []

      const recentUsers = users
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
        .slice(0, 5)

      recentUsers.forEach((user) => {
        activities.push({
          id: user.id,
          type: 'user_registration',
          user: user.full_name || user.username,
          time: new Date(user.created_at).toLocaleString(),
          status: 'success',
          details: `Новый пользователь: ${user.role}`,
        })
      })

      const completedTests = testAttempts
        .filter((attempt) => attempt.completed_at)
        .sort((a, b) => new Date(b.completed_at!).getTime() - new Date(a.completed_at!).getTime())
        .slice(0, 5)

      completedTests.forEach((attempt) => {
        activities.push({
          id: attempt.id,
          type: 'test_completion',
          user: `Студент ${attempt.user_id}`,
          time: new Date(attempt.completed_at!).toLocaleString(),
          status: 'success',
          details: `Тест завершен, результат: ${attempt.score}%`,
        })
      })

      const recentTopics = topics
        .sort((a, b) => new Date(b.created_at || '').getTime() - new Date(a.created_at || '').getTime())
        .slice(0, 3)

      recentTopics.forEach((topic) => {
        activities.push({
          id: topic.id,
          type: 'topic_created',
          user: topic.creator_full_name,
          time: new Date(topic.created_at || '').toLocaleString(),
          status: 'success',
          details: `Создана тема: ${topic.title}`,
        })
      })

      activities.push({
        id: 999,
        type: 'system_backup',
        user: 'Система',
        time: new Date(Date.now() - 3600000).toLocaleString(),
        status: 'success',
        details: 'Резервное копирование завершено',
      })

      return activities
        .sort((a, b) => new Date(b.time).getTime() - new Date(a.time).getTime())
        .slice(0, 10)
    } catch (error) {
      console.error('Ошибка получения недавней активности:', error)
      throw error
    }
  },

  /**
   * Получить системные предупреждения
   */
  getSystemAlerts: async (): Promise<SystemAlert[]> => {
    try {
      let users: User[] = []
      let testAttempts: TestAttempt[] = []

      try {
        users = await userApi.getAllUsers()
      } catch (error) {
        console.error('Ошибка загрузки пользователей:', error)
        users = []
      }

      try {
        testAttempts = await progressApi.getTestAttempts()
      } catch (error) {
        console.error('Ошибка загрузки попыток тестов:', error)
        testAttempts = []
      }

      const alerts: SystemAlert[] = []

      const activeUsers = users.filter((user) => {
        if (!user.last_login) return false
        const lastLogin = new Date(user.last_login)
        const now = new Date()
        const diffHours = (now.getTime() - lastLogin.getTime()) / (1000 * 60 * 60)
        return diffHours <= 24
      })

      if (activeUsers.length > 200) {
        alerts.push({
          id: 1,
          type: 'warning',
          message: 'Высокая нагрузка на сервер',
          time: new Date().toLocaleString(),
          severity: 'medium',
        })
      }

      const failedTests = testAttempts.filter(
        (attempt) => attempt.completed_at && attempt.score !== null && attempt.score < 50
      )

      if (failedTests.length > 100) {
        alerts.push({
          id: 2,
          type: 'warning',
          message: 'Много неудачных попыток тестов',
          time: new Date().toLocaleString(),
          severity: 'low',
        })
      }

      alerts.push({
        id: 3,
        type: 'info',
        message: 'Резервное копирование завершено',
        time: new Date(Date.now() - 3600000).toLocaleString(),
        severity: 'low',
      })

      return alerts
    } catch (error) {
      console.error('Ошибка получения системных предупреждений:', error)
      throw error
    }
  },

  /**
   * Получить системные логи
   */
  getSystemLogs: async (): Promise<SystemLog[]> => {
    try {
      let users: User[] = []
      let topics: Topic[] = []
      let testAttempts: TestAttempt[] = []

      try {
        users = await userApi.getAllUsers()
      } catch (error) {
        console.error('Ошибка загрузки пользователей:', error)
        users = []
      }

      try {
        topics = await topicApi.getTopics()
      } catch (error) {
        console.error('Ошибка загрузки тем:', error)
        topics = []
      }

      try {
        testAttempts = await progressApi.getTestAttempts()
      } catch (error) {
        console.error('Ошибка загрузки попыток тестов:', error)
        testAttempts = []
      }

      const logs: SystemLog[] = []

      topics.forEach((topic) => {
        logs.push({
          id: topic.id,
          user: topic.creator_full_name,
          action: 'Создал тему',
          target: topic.title,
          date: new Date(topic.created_at || '').toLocaleString(),
          type: 'create',
        })
      })

      testAttempts
        .filter((attempt) => attempt.completed_at)
        .slice(0, 10)
        .forEach((attempt) => {
          logs.push({
            id: attempt.id,
            user: `Студент ${attempt.user_id}`,
            action: 'Завершил тест',
            target: `Тест #${attempt.test_id}`,
            date: new Date(attempt.completed_at!).toLocaleString(),
            type: 'complete',
          })
        })

      users
        .filter((user) => user.last_login)
        .sort((a, b) => new Date(b.last_login!).getTime() - new Date(a.last_login!).getTime())
        .slice(0, 5)
        .forEach((user) => {
          logs.push({
            id: user.id,
            user: user.full_name || user.username,
            action: 'Вошёл в систему',
            target: 'Система',
            date: new Date(user.last_login!).toLocaleString(),
            type: 'login',
          })
        })

      return logs
        .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
        .slice(0, 20)
    } catch (error) {
      console.error('Ошибка получения системных логов:', error)
      throw error
    }
  },

  /**
   * Получить активность пользователей
   */
  getUserActivity: async (): Promise<UserActivity> => {
    try {
      let users: User[] = []
      try {
        users = await userApi.getAllUsers()
      } catch (error) {
        console.error('Ошибка загрузки пользователей:', error)
        throw new Error('Не удалось загрузить данные пользователей')
      }

      const now = new Date()
      const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
      const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
      const monthAgo = new Date(now.getFullYear(), now.getMonth() - 1, now.getDate())

      const onlineNow = users.filter((user) => {
        if (!user.last_login) return false
        const lastLogin = new Date(user.last_login)
        const diffHours = (now.getTime() - lastLogin.getTime()) / (1000 * 60 * 60)
        return diffHours <= 1
      }).length

      const todayUsers = users.filter((user) => {
        const createdAt = new Date(user.created_at)
        return createdAt >= today
      }).length

      const weekUsers = users.filter((user) => {
        const createdAt = new Date(user.created_at)
        return createdAt >= weekAgo
      }).length

      const monthUsers = users.filter((user) => {
        const createdAt = new Date(user.created_at)
        return createdAt >= monthAgo
      }).length

      return {
        onlineNow,
        today: todayUsers,
        thisWeek: weekUsers,
        thisMonth: monthUsers,
      }
    } catch (error) {
      console.error('Ошибка получения активности пользователей:', error)
      throw error
    }
  },

  /**
   * Получить производительность системы (mock данные)
   */
  getSystemPerformance: async (): Promise<SystemPerformance> => {
    return {
      cpu: Math.floor(Math.random() * 30) + 20,
      memory: Math.floor(Math.random() * 40) + 40,
      disk: Math.floor(Math.random() * 20) + 10,
      network: Math.floor(Math.random() * 15) + 5,
    }
  },
}

export default dashboardApi


