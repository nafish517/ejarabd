import type { Client, ClientMatchesResponse, HealthStatus, TendersListResponse } from '../types';

const API_BASE = '/api';

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    let errorDetail = 'API request failed';
    try {
      const err = await response.json();
      errorDetail = err.detail || err.message || errorDetail;
    } catch {
      errorDetail = response.statusText;
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

export const api = {
  getHealth: () => request<HealthStatus>('/health'),

  getClients: (params?: { status?: string; is_demo?: boolean; search?: string }) => {
    const q = new URLSearchParams();
    if (params?.status) q.append('status', params.status);
    if (params?.is_demo !== undefined) q.append('is_demo', String(params.is_demo));
    if (params?.search) q.append('search', params.search);
    const qs = q.toString() ? `?${q.toString()}` : '';
    return request<Client[]>(`/clients${qs}`);
  },

  getClient: (id: number) => request<Client>(`/clients/${id}`),

  createClient: (payload: Partial<Client>) =>
    request<{ status: string; message: string; client: Client }>('/clients', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  updateClient: (id: number, payload: Partial<Client>) =>
    request<{ status: string; message: string; client: Client }>(`/clients/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),

  updateClientStatus: (id: number, client_status: 'active' | 'paused' | 'draft') =>
    request<{ status: string; message: string; client_status: string }>(`/clients/${id}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ client_status }),
    }),

  runMatching: (clientId?: number) => {
    const qs = clientId ? `?client_id=${clientId}` : '';
    return request<{ status: string; message: string; evaluated: number }>(`/match/run${qs}`, {
      method: 'POST',
    });
  },

  getClientMatches: (clientId: number, fitStatus?: string) => {
    const q = new URLSearchParams();
    if (fitStatus) q.append('fit_status', fitStatus);
    const qs = q.toString() ? `?${q.toString()}` : '';
    return request<ClientMatchesResponse>(`/clients/${clientId}/matches${qs}`);
  },

  getTenders: (params?: { search?: string; district?: string; category?: string; limit?: number; offset?: number }) => {
    const q = new URLSearchParams();
    if (params?.search) q.append('search', params.search);
    if (params?.district) q.append('district', params.district);
    if (params?.category) q.append('category', params.category);
    if (params?.limit) q.append('limit', String(params.limit));
    if (params?.offset) q.append('offset', String(params.offset));
    const qs = q.toString() ? `?${q.toString()}` : '';
    return request<TendersListResponse>(`/tenders${qs}`);
  },

  sendTestEmail: (clientId: number, recipientEmail?: string, tenderId?: number, force: boolean = false) =>
    request<{
      status: string;
      message: string;
      recipient: string;
      tender_title: string;
      record_id: number;
    }>(`/clients/${clientId}/test-email`, {
      method: 'POST',
      body: JSON.stringify({
        recipient_email: recipientEmail,
        tender_id: tenderId,
        force,
      }),
    }),
};
