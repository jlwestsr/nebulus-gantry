import type {
  User,
  LoginRequest,
  Conversation,
  Message,
  AdminUser,
  CreateUserRequest,
  UpdateUserRequest,
  Service,
  Model,
  SearchResponse,
} from '../types/api';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || 'Request failed');
  }

  return response.json();
}

export const authApi = {
  login: (data: LoginRequest) =>
    fetchApi<{ message: string }>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  logout: () =>
    fetchApi<{ message: string }>('/api/auth/logout', {
      method: 'POST',
    }),

  me: () => fetchApi<User>('/api/auth/me'),

  changePassword: (currentPassword: string, newPassword: string) =>
    fetchApi<{ message: string }>('/api/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
      }),
    }),
};

export const chatApi = {
  getConversations: () => fetchApi<Conversation[]>('/api/chat/conversations'),

  getConversation: (id: number) =>
    fetchApi<{ conversation: Conversation; messages: Message[] }>(
      `/api/chat/conversations/${id}`
    ),

  createConversation: () =>
    fetchApi<Conversation>('/api/chat/conversations', {
      method: 'POST',
    }),

  deleteConversation: (id: number) =>
    fetchApi<{ message: string }>(`/api/chat/conversations/${id}`, {
      method: 'DELETE',
    }),

  search: (query: string) =>
    fetchApi<SearchResponse>(`/api/chat/search?q=${encodeURIComponent(query)}`),

  sendMessage: async function* (conversationId: number, content: string, model?: string) {
    const body: Record<string, string> = { content };
    if (model) body.model = model;

    const response = await fetch(
      `${API_URL}/api/chat/conversations/${conversationId}/messages`,
      {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      }
    );

    if (!response.ok) {
      throw new Error('Failed to send message');
    }

    const reader = response.body?.getReader();
    if (!reader) throw new Error('No response body');

    const decoder = new TextDecoder('utf-8');
    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        yield decoder.decode(value, { stream: true });
      }
    } finally {
      reader.releaseLock();
    }
  },
};

export const modelsApi = {
  list: () =>
    fetchApi<{ models: Model[] }>('/api/models'),

  getActive: () =>
    fetchApi<{ model: Model | null }>('/api/models/active'),
};

export const adminApi = {
  // Users
  listUsers: () =>
    fetchApi<{ users: AdminUser[] }>('/api/admin/users'),

  createUser: (data: CreateUserRequest) =>
    fetchApi<{ user: AdminUser; message: string }>('/api/admin/users', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateUser: (id: number, data: UpdateUserRequest) =>
    fetchApi<AdminUser>(`/api/admin/users/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  deleteUser: (id: number) =>
    fetchApi<{ message: string }>(`/api/admin/users/${id}`, {
      method: 'DELETE',
    }),

  // Services
  listServices: () =>
    fetchApi<{ services: Service[] }>('/api/admin/services'),

  restartService: (name: string) =>
    fetchApi<{ message: string }>(`/api/admin/services/${name}/restart`, {
      method: 'POST',
    }),

  // Models
  listModels: () =>
    fetchApi<{ models: Model[] }>('/api/admin/models'),

  switchModel: (modelId: string) =>
    fetchApi<{ message: string }>('/api/admin/models/switch', {
      method: 'POST',
      body: JSON.stringify({ model_id: modelId }),
    }),

  unloadModel: () =>
    fetchApi<{ message: string }>('/api/admin/models/unload', {
      method: 'POST',
    }),

  // Logs
  streamLogs: (serviceName: string): EventSource => {
    return new EventSource(`${API_URL}/api/admin/logs/${serviceName}`, {
      withCredentials: true,
    });
  },
};
