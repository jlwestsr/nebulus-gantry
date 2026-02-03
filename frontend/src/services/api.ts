import type { User, LoginRequest, Conversation, Message } from '../types/api';

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

  sendMessage: async function* (conversationId: number, content: string) {
    const response = await fetch(
      `${API_URL}/api/chat/conversations/${conversationId}/messages`,
      {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      }
    );

    if (!response.ok) {
      throw new Error('Failed to send message');
    }

    const reader = response.body?.getReader();
    if (!reader) throw new Error('No response body');

    const decoder = new TextDecoder();
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      yield decoder.decode(value);
    }
  },
};
