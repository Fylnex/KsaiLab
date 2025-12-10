/**
 * Общие типы для API сервисов
 */

export interface User {
  id: number
  username: string
  full_name: string
  patronymic?: string
  role: 'admin' | 'student' | 'teacher'
  is_active: boolean
  created_at: string
  updated_at: string
  last_login?: string
  refresh_token?: string
  is_archived: boolean
  group?: string  // Название активной группы студента
}

export interface Group {
  id: number
  name: string
  description?: string
  start_year: number
  creator_id: number
  created_at: string
  updated_at: string
}

export interface Topic {
  id: number
  title: string
  description?: string
  created_at: string
  updated_at: string
}

export interface Section {
  id: number
  topic_id: number
  title: string
  description?: string
  order_index: number
  created_at: string
  updated_at: string
}

export interface Subsection {
  id: number
  section_id: number
  title: string
  content?: string
  order_index: number
  created_at: string
  updated_at: string
}

export interface Test {
  id: number
  title: string
  description?: string
  section_id?: number
  time_limit?: number
  passing_score: number
  created_at: string
  updated_at: string
}

export interface Question {
  id: number
  test_id: number
  question_text: string
  question_type: 'single' | 'multiple' | 'text'
  points: number
  order_index: number
  created_at: string
  updated_at: string
}

export interface QuestionBankEntry {
  id: number
  topic_id: number
  section_id?: number
  question_text: string
  question_type: 'single' | 'multiple' | 'text'
  points: number
  created_at: string
  updated_at: string
}

export interface QuestionBankEntryPayload {
  topic_id: number
  section_id?: number
  question_text: string
  question_type: 'single' | 'multiple' | 'text'
  points: number
}

export interface TopicAuthorInfo {
  topic_id: number
  topic_title: string
  user_id: number
  username: string
  full_name: string
  author_type: string
}

export interface FileUploadResponse {
  file_id: string
  file_url: string
  file_name: string
  file_size: number
  content_type: string
}

export interface Progress {
  id: number
  user_id: number
  topic_id: number
  section_id?: number
  subsection_id?: number
  completion_percentage: number
  last_viewed_at: string
  created_at: string
  updated_at: string
}

export interface GroupStudent {
  id: number
  group_id: number
  user_id: number
  status: 'active' | 'inactive'
  joined_at: string
  left_at?: string
}


