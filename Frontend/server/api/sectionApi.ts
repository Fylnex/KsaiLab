/**
 * API клиент для управления секциями и подсекциями
 * Использует правильный httpClient из app/utils/
 */

import { getHttpClient } from '@/utils/httpClient'

export interface Section {
  id: number
  topic_id: number
  title: string
  content?: string
  description?: string
  order: number
  created_at?: string
  is_archived: boolean
  tests?: unknown[]
}

export interface Subsection {
  id: number
  section_id: number
  title: string
  content?: string
  file_path?: string
  type: 'text' | 'pdf' | 'presentation' | 'video'
  order: number
  created_at?: string
  is_archived: boolean
  required_time_minutes?: number | null
  min_time_seconds?: number | null
}

export interface SectionWithSubsections extends Section {
  subsections: Subsection[]
}

export const sectionApi = {
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
   * Получить секцию по ID
   */
  getSection: async (sectionId: number): Promise<Section> => {
    const http = getHttpClient()
    const { data } = await http.get<Section>(`/sections/read/${sectionId}`)
    return data
  },

  /**
   * Создать секцию
   */
  createSection: async (data: Partial<Section>): Promise<Section> => {
    const http = getHttpClient()
    const { data: result } = await http.post<Section>('/sections/create', data)
    return result
  },

  /**
   * Обновить секцию
   */
  updateSection: async (id: number, data: Partial<Section>): Promise<Section> => {
    const http = getHttpClient()
    const { data: result } = await http.put<Section>(`/sections/update/${id}`, data)
    return result
  },

  /**
   * Удалить секцию
   */
  deleteSection: async (id: number): Promise<void> => {
    const http = getHttpClient()
    await http.delete(`/sections/${id}`)
  },

  /**
   * Архивировать секцию
   */
  archiveSection: async (id: number): Promise<void> => {
    const http = getHttpClient()
    await http.post(`/sections/archive/${id}/archive`)
  },

  /**
   * Восстановить секцию из архива
   */
  restoreSection: async (id: number): Promise<void> => {
    const http = getHttpClient()
    await http.post(`/sections/archive/${id}/restore`)
  },

  /**
   * Удалить секцию навсегда
   */
  deleteSectionPermanently: async (id: number): Promise<void> => {
    const http = getHttpClient()
    await http.delete(`/sections/archive/${id}/permanent`)
  },

  /**
   * Получить подсекцию по ID
   */
  getSubsection: async (subsectionId: number): Promise<Subsection> => {
    const http = getHttpClient()
    const { data } = await http.get<Subsection>(`/subsections/read/${subsectionId}`)
    return data
  },

  /**
   * Получить секцию с подсекциями
   */
  getSectionSubsections: async (sectionId: number): Promise<SectionWithSubsections> => {
    const http = getHttpClient()
    const { data } = await http.get<SectionWithSubsections>(`/sections/${sectionId}/subsections`)
    return data
  },

  /**
   * Получить подсекции секции
   */
  getSubsectionsBySection: async (
    sectionId: number,
    options?: { include_archived?: boolean }
  ): Promise<Subsection[]> => {
    const http = getHttpClient()
    const params: any = {
      section_id: sectionId,
    }

    // Добавляем include_archived только если он явно указан
    if (options?.include_archived !== undefined) {
      params.include_archived = options.include_archived
    }

    const { data } = await http.get<Subsection[]>('/subsections/read', {
      params,
    })
    return data
  },

  /**
   * Создать подсекцию (multipart/form-data)
   */
  createSubsection: async (formData: FormData): Promise<Subsection> => {
    const http = getHttpClient()
    const { data } = await http.post<Subsection>('/subsections', formData)
    return data
  },

  /**
   * Создать текстовую подсекцию (JSON)
   */
  createSubsectionJson: async (payload: {
    section_id: number
    title: string
    content: string
    type: 'text'
    order?: number
    required_time_minutes?: number | null
    min_time_seconds?: number
  }): Promise<Subsection> => {
    const http = getHttpClient()
    const { data } = await http.post<Subsection>('/subsections/create/json', payload)
    return data
  },

  /**
   * Создать PDF подсекцию (FormData)
   */
  createSubsectionPdf: async (formData: FormData): Promise<Subsection> => {
    const http = getHttpClient()
    const { data } = await http.post<Subsection>('/subsections/create/pdf', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },

  /**
   * Создать видео подсекцию (FormData)
   */
  createSubsectionVideo: async (formData: FormData): Promise<Subsection> => {
    const http = getHttpClient()
    const { data } = await http.post<Subsection>('/subsections/create/video', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },

  /**
   * Создать презентацию подсекцию (FormData)
   */
  createSubsectionPresentation: async (formData: FormData): Promise<Subsection> => {
    const http = getHttpClient()
    const { data } = await http.post<Subsection>('/subsections/create/presentation', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },

  /**
   * Обновить подсекцию (JSON)
   */
  updateSubsectionJson: async (
    id: number,
    data: { title?: string; content?: string; type: 'text'; order?: number }
  ): Promise<Subsection> => {
    const http = getHttpClient()
    const { data: result } = await http.put<Subsection>(`/subsections/update/${id}/json`, data)
    return result
  },

  /**
   * Обновить подсекцию (PDF)
   */
  updateSubsectionPdf: async (id: number, formData: FormData): Promise<Subsection> => {
    const http = getHttpClient()
    const { data } = await http.put<Subsection>(`/subsections/update/${id}/pdf`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },

  /**
   * Обновить подсекцию (презентация)
   */
  updateSubsectionPresentation: async (id: number, formData: FormData): Promise<Subsection> => {
    const http = getHttpClient()
    const { data } = await http.put<Subsection>(`/subsections/update/${id}/presentation`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },

  /**
   * Обновить подсекцию (видео)
   */
  updateSubsectionVideo: async (id: number, formData: FormData): Promise<Subsection> => {
    const http = getHttpClient()
    const { data } = await http.put<Subsection>(`/subsections/update/${id}/video`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },

  /**
   * Удалить подсекцию
   */
  deleteSubsection: async (id: number): Promise<void> => {
    const http = getHttpClient()
    await http.delete(`/subsections/${id}`)
  },

  /**
   * Архивировать подсекцию
   */
  archiveSubsection: async (id: number): Promise<void> => {
    const http = getHttpClient()
    await http.post(`/subsections/archive/${id}/archive`)
  },

  /**
   * Восстановить подсекцию из архива
   */
  restoreSubsection: async (id: number): Promise<void> => {
    const http = getHttpClient()
    await http.post(`/subsections/archive/${id}/restore`)
  },

  /**
   * Удалить подсекцию навсегда
   */
  deleteSubsectionPermanently: async (id: number): Promise<void> => {
    const http = getHttpClient()
    await http.delete(`/subsections/archive/${id}/permanent`)
  },

  /**
   * Обновить порядок подсекций
   */
  reorderSubsections: async (
    sectionId: number,
    subsectionOrders: Array<{ id: number; order: number }>
  ): Promise<void> => {
    const http = getHttpClient()
    await http.put(`/sections/${sectionId}/subsections/reorder`, {
      subsection_orders: subsectionOrders,
    })
  },
}


