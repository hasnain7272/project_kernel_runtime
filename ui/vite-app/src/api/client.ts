/**
 * API client configuration.
 */

interface ApiResponse<T> {
  data?: T;
  error?: string;
  status: 'accepted' | 'success' | 'error';
}

export function getTenantId() {
  let tenantId = localStorage.getItem('tenant_id');
  if (!tenantId) {
    tenantId = 'usr_' + Math.random().toString(36).slice(2, 11);
    localStorage.setItem('tenant_id', tenantId);
  }
  return tenantId;
}

async function request<T>(
  method: string,
  endpoint: string,
  payload?: any,
): Promise<ApiResponse<T>> {
  try {
    const init: RequestInit = {
      method,
      headers: {
        'Content-Type': 'application/json',
        'X-Tenant-Id': getTenantId(),
      },
    };
    if (payload !== undefined) {
      init.body = JSON.stringify(payload);
    }
    const response = await fetch(`/api/v1${endpoint}`, init);
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || data.error || 'API Request Failed');
    return { data, status: response.status === 202 ? 'accepted' : 'success' };
  } catch (e: any) {
    return { error: e.message, status: 'error' };
  }
}

export const apiClient = {
  post<T>(endpoint: string, payload: any) {
    return request<T>('POST', endpoint, payload);
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
