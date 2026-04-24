/**
 * API client configuration.
 */

interface ApiResponse<T> {
  data?: T;
  error?: string;
  status: 'accepted' | 'success' | 'error';
}

export function getTenantId() {
  return localStorage.getItem('tenant_id') || '';
}

export function getAuthToken() {
  return localStorage.getItem('auth_token') || '';
}

async function request<T>(
  method: string,
  endpoint: string,
  payload?: any,
  options: { headers?: Record<string, string> } = {}
): Promise<ApiResponse<T>> {
  try {
    const token = getAuthToken();
    const tenantId = getTenantId();
    const isFormData = payload instanceof FormData;
    
    const init: RequestInit = {
      method,
      headers: {
        ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        ...(tenantId ? { 'X-Tenant-Id': tenantId } : {}),
        ...options.headers,
      },
    };
    
    if (payload !== undefined) {
      init.body = isFormData ? payload : JSON.stringify(payload);
    }
    const response = await fetch(`/api/v1${endpoint}`, init);
    
    // Global Auth Interceptor: Redirect to login on 401
    if (response.status === 401) {
      console.warn("[SaaS Auth] 401 Unauthorized. Redirecting to login...");
      localStorage.removeItem('auth_token');
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }

    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || data.error || 'API Request Failed');
    return { data, status: response.status === 202 ? 'accepted' : 'success' };
  } catch (e: any) {
    return { error: e.message, status: 'error' };
  }
}

export const apiClient = {
  post<T>(endpoint: string, payload: any, options: { headers?: Record<string, string> } = {}) {
    return request<T>('POST', endpoint, payload, options);
  },
  get<T>(endpoint: string) {
    return request<T>('GET', endpoint);
  },
  patch<T>(endpoint: string, payload: any) {
    return request<T>('PATCH', endpoint, payload);
  },
  delete<T>(endpoint: string) {
    return request<T>('DELETE', endpoint);
  },
};
