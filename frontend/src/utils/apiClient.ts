import type { ApiError } from '../types';

export class AppApiError extends Error {
  code: string;
  statusCode: number;
  retryable: boolean;
  details?: any;

  constructor(error: ApiError) {
    super(error.message || 'An unexpected error occurred');
    this.name = 'AppApiError';
    this.code = error.code || 'UNKNOWN_ERROR';
    this.statusCode = error.status_code || 500;
    this.retryable = Boolean(error.retryable);
    this.details = error.details;
  }
}

export async function safeFetchJson<T = any>(
  input: RequestInfo | URL,
  init?: RequestInit
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(input, init);
  } catch (networkErr: any) {
    throw new AppApiError({
      code: 'NETWORK_ERROR',
      message: networkErr.message || 'Failed to connect to backend server. Is the server running?',
      status_code: 0,
      retryable: true
    });
  }

  const contentType = response.headers.get('content-type') || '';
  const isJson = contentType.includes('application/json');

  let bodyData: any = null;
  if (isJson) {
    try {
      bodyData = await response.json();
    } catch {
      bodyData = null;
    }
  } else {
    try {
      const text = await response.text();
      bodyData = text;
    } catch {
      bodyData = null;
    }
  }

  if (!response.ok) {
    if (bodyData && typeof bodyData === 'object' && bodyData.error) {
      throw new AppApiError(bodyData.error);
    } else if (bodyData && typeof bodyData === 'object' && bodyData.detail) {
      throw new AppApiError({
        code: response.status === 429 ? 'UPSTREAM_RATE_LIMIT' : 'API_ERROR',
        message: typeof bodyData.detail === 'string' ? bodyData.detail : JSON.stringify(bodyData.detail),
        status_code: response.status,
        retryable: [429, 503, 504].includes(response.status)
      });
    } else {
      const textPreview = typeof bodyData === 'string' ? bodyData.slice(0, 200) : 'Internal Server Error';
      throw new AppApiError({
        code: response.status === 429 ? 'UPSTREAM_RATE_LIMIT' : 'SERVER_ERROR',
        message: textPreview || `Request failed with HTTP status ${response.status}`,
        status_code: response.status,
        retryable: [429, 503, 504].includes(response.status)
      });
    }
  }

  return bodyData as T;
}
