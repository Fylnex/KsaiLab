/**
 * API клиент для управления файлами
 * Использует правильный httpClient из app/utils/
 */

import { getHttpClient } from '@/utils/httpClient'

export interface FileUploadResponse {
  file_id: string
  filename: string
  minio_path: string
  file_url?: string | null
  file_size?: number | null
  content_type?: string | null
  uploaded_at: string
}

export interface FileDeleteResponse {
  message: string
  file_id: string
}

export interface FileInfo {
  file_id: string
  filename: string
  file_url: string
  file_size?: number | null
  content_type?: string | null
  uploaded_at: string | null
  bucket: string
  object_name: string
}

export const fileApi = {
  /**
   * Загрузить изображение
   */
  uploadImage: async (file: File): Promise<FileUploadResponse> => {
    const http = getHttpClient()
    const formData = new FormData()
    formData.append('file', file)

    const { data } = await http.post<FileUploadResponse>('/files/upload/image', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return data
  },

  /**
   * Загрузить файл
   */
  uploadFile: async (file: File): Promise<FileUploadResponse> => {
    const http = getHttpClient()
    const formData = new FormData()
    formData.append('file', file)

    const { data } = await http.post<FileUploadResponse>('/files/upload/file', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return data
  },

  /**
   * Загрузить PDF
   */
  uploadPdf: async (file: File): Promise<FileUploadResponse> => {
    const http = getHttpClient()
    const formData = new FormData()
    formData.append('file', file)

    const { data } = await http.post<FileUploadResponse>('/files/upload/pdf', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return data
  },

  /**
   * Загрузить презентацию
   */
  uploadPresentation: async (file: File): Promise<FileUploadResponse> => {
    const http = getHttpClient()
    const formData = new FormData()
    formData.append('file', file)

    const { data } = await http.post<FileUploadResponse>('/files/upload/presentation', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return data
  },

  /**
   * Загрузить видео
   */
  uploadVideo: async (file: File): Promise<FileUploadResponse> => {
    const http = getHttpClient()
    const formData = new FormData()
    formData.append('file', file)

    const { data } = await http.post<FileUploadResponse>('/files/upload/video', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return data
  },

  /**
   * Получить информацию о файле
   */
  getFileInfo: async (fileId: string): Promise<FileInfo> => {
    const http = getHttpClient()
    const { data } = await http.get<FileInfo>(`/files/${fileId}`)
    return data
  },

  /**
   * Получить URL файла
   */
  getFileUrl: async (fileId: string): Promise<string> => {
    const http = getHttpClient()
    const { data } = await http.get<{ file_url: string }>(`/files/${fileId}/url`)
    return data.file_url
  },

  /**
   * Удалить файл
   */
  deleteFile: async (fileId: string): Promise<FileDeleteResponse> => {
    const http = getHttpClient()
    const { data } = await http.delete<FileDeleteResponse>(`/files/${fileId}`)
    return data
  },

  /**
   * Скачать файл
   */
  downloadFile: async (fileId: string): Promise<Blob> => {
    const http = getHttpClient()
    const { data } = await http.get<Blob>(`/files/${fileId}/download`, {
      responseType: 'blob',
    })
    return data
  },

  /**
   * Загрузить файл с прогрессом
   */
  uploadFileWithProgress: async (
    file: File,
    onProgress?: (progress: number) => void
  ): Promise<FileUploadResponse> => {
    const http = getHttpClient()
    const formData = new FormData()
    formData.append('file', file)

    const { data } = await http.post<FileUploadResponse>('/files/upload/file', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total && onProgress) {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          onProgress(percentCompleted)
        }
      },
    })
    return data
  },
}


