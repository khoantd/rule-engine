import axios, { AxiosInstance, AxiosError } from 'axios'
import { API_CONFIG } from '@/config/api'
import { ErrorResponse } from '@/types'

class ApiClient {
  private client: AxiosInstance
  private apiKey: string | undefined

  constructor() {
    this.apiKey = import.meta.env.VITE_API_KEY

    this.client = axios.create({
      baseURL: API_CONFIG.baseURL,
      timeout: API_CONFIG.timeout,
      headers: API_CONFIG.headers,
    })

    this.setupInterceptors()
  }

  private setupInterceptors() {
    this.client.interceptors.request.use(
      (config) => {
        if (this.apiKey) {
          config.headers['X-API-Key'] = this.apiKey
        }

        const correlationId = this.generateCorrelationId()
        config.headers['X-Correlation-ID'] = correlationId
        ;(config as any).metadata = { correlationId }

        return config
      },
      (error) => {
        return Promise.reject(error)
      },
    )

    this.client.interceptors.response.use(
      (response) => {
        return response
      },
      (error: AxiosError<ErrorResponse>) => {
        const correlationId = (error.config as any)?.metadata?.correlationId

        if (error.response?.data) {
          error.response.data.correlation_id = correlationId
        }

        return Promise.reject(error)
      },
    )
  }

  private generateCorrelationId(): string {
    return `req-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
  }

  public getInstance(): AxiosInstance {
    return this.client
  }

  public getError(error: any): ErrorResponse {
    if (error.response?.data) {
      return error.response.data as ErrorResponse
    }

    if (error.message) {
      return {
        error_type: 'NetworkError',
        message: error.message,
      }
    }

    return {
      error_type: 'UnknownError',
      message: 'An unexpected error occurred',
    }
  }
}

export const apiClient = new ApiClient()
export const api = apiClient.getInstance()
export const getApiError = apiClient.getError.bind(apiClient)
