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
  Collection,
  Document,
  DocumentSearchResponse,
  CreateCollectionRequest,
  UpdateCollectionRequest,
  DocumentScope,
  Persona,
  CreatePersonaRequest,
  UpdatePersonaRequest,
  OverlordDashboard,
  OverlordProjectStatus,
  OverlordGraph,
  OverlordMemoryList,
  OverlordMemoryEntry,
  OverlordPlan,
  OverlordDispatchResult,
  OverlordProposal,
  OverlordDetection,
  OverlordNotificationStats,
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

  pinConversation: (id: number) =>
    fetchApi<Conversation>(`/api/chat/conversations/${id}/pin`, { method: 'PATCH' }),

  exportConversation: (id: number, format: 'json' | 'pdf') => {
    // Trigger download via browser navigation
    window.location.href = `${API_URL}/api/chat/conversations/${id}/export?format=${format}`;
  },

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

// ─── Documents / Knowledge Vault ─────────────────────────────────────────────

export const documentApi = {
  // Collections
  listCollections: () => fetchApi<Collection[]>('/api/documents/collections'),

  createCollection: (data: CreateCollectionRequest) =>
    fetchApi<Collection>('/api/documents/collections', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getCollection: (id: number) => fetchApi<Collection>(`/api/documents/collections/${id}`),

  updateCollection: (id: number, data: UpdateCollectionRequest) =>
    fetchApi<Collection>(`/api/documents/collections/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  deleteCollection: (id: number) =>
    fetchApi<{ message: string }>(`/api/documents/collections/${id}`, {
      method: 'DELETE',
    }),

  // Documents
  listDocuments: (collectionId?: number) => {
    const url = collectionId
      ? `/api/documents?collection_id=${collectionId}`
      : '/api/documents';
    return fetchApi<Document[]>(url);
  },

  getDocument: (id: number) => fetchApi<Document>(`/api/documents/${id}`),

  deleteDocument: (id: number) =>
    fetchApi<{ message: string }>(`/api/documents/${id}`, {
      method: 'DELETE',
    }),

  uploadDocument: async (file: File, collectionId?: number): Promise<Document> => {
    const formData = new FormData();
    formData.append('file', file);
    if (collectionId !== undefined) {
      formData.append('collection_id', collectionId.toString());
    }

    const response = await fetch(`${API_URL}/api/documents/upload`, {
      method: 'POST',
      credentials: 'include',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(error.detail || 'Upload failed');
    }

    return response.json();
  },

  search: (query: string, collectionIds?: number[], topK?: number) =>
    fetchApi<DocumentSearchResponse>('/api/documents/search', {
      method: 'POST',
      body: JSON.stringify({
        query,
        collection_ids: collectionIds,
        top_k: topK ?? 5,
      }),
    }),

  // Conversation document scope
  setDocumentScope: (conversationId: number, documentScope: DocumentScope[] | null) =>
    fetchApi<Conversation>(`/api/chat/conversations/${conversationId}/document-scope`, {
      method: 'PATCH',
      body: JSON.stringify({ document_scope: documentScope }),
    }),
};

// ─── Personas ────────────────────────────────────────────────────────────────

export const personaApi = {
  list: () => fetchApi<Persona[]>('/api/personas'),

  get: (id: number) => fetchApi<Persona>(`/api/personas/${id}`),

  create: (data: CreatePersonaRequest) =>
    fetchApi<Persona>('/api/personas', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (id: number, data: UpdatePersonaRequest) =>
    fetchApi<Persona>(`/api/personas/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  delete: (id: number) =>
    fetchApi<{ message: string }>(`/api/personas/${id}`, {
      method: 'DELETE',
    }),

  // Conversation persona
  setConversationPersona: (conversationId: number, personaId: number | null) =>
    fetchApi<Conversation>(`/api/chat/conversations/${conversationId}/persona`, {
      method: 'PATCH',
      body: JSON.stringify({ persona_id: personaId }),
    }),
};

// ─── Admin ───────────────────────────────────────────────────────────────────

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

  // Export
  bulkExport: (userId?: number, dateFrom?: string, dateTo?: string) => {
    const params = new URLSearchParams();
    if (userId !== undefined) params.append('user_id', userId.toString());
    if (dateFrom) params.append('date_from', dateFrom);
    if (dateTo) params.append('date_to', dateTo);
    // Use POST via form submission to handle auth cookie
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = `${API_URL}/api/admin/export/bulk?${params.toString()}`;
    document.body.appendChild(form);
    form.submit();
    document.body.removeChild(form);
  },

  // System Personas (admin only)
  listSystemPersonas: () => fetchApi<Persona[]>('/api/admin/personas'),

  createSystemPersona: (data: CreatePersonaRequest) =>
    fetchApi<Persona>('/api/admin/personas', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateSystemPersona: (id: number, data: UpdatePersonaRequest) =>
    fetchApi<Persona>(`/api/admin/personas/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  deleteSystemPersona: (id: number) =>
    fetchApi<{ message: string }>(`/api/admin/personas/${id}`, {
      method: 'DELETE',
    }),
};

// ─── Overlord ─────────────────────────────────────────────────────────────

export const overlordApi = {
  // Tier 1: Dashboard
  getDashboard: () => fetchApi<OverlordDashboard>('/api/overlord/dashboard'),

  scanProject: (project: string) =>
    fetchApi<OverlordProjectStatus>(`/api/overlord/scan/${encodeURIComponent(project)}`),

  getGraph: () => fetchApi<OverlordGraph>('/api/overlord/graph'),

  // Tier 2: Memory
  listMemory: (params?: { query?: string; category?: string; project?: string; limit?: number }) => {
    const searchParams = new URLSearchParams();
    if (params?.query) searchParams.append('query', params.query);
    if (params?.category) searchParams.append('category', params.category);
    if (params?.project) searchParams.append('project', params.project);
    if (params?.limit) searchParams.append('limit', params.limit.toString());
    const qs = searchParams.toString();
    return fetchApi<OverlordMemoryList>(`/api/overlord/memory${qs ? `?${qs}` : ''}`);
  },

  addMemory: (data: { category: string; content: string; project?: string }) =>
    fetchApi<{ id: string; message: string }>('/api/overlord/memory', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  deleteMemory: (id: string) =>
    fetchApi<{ message: string }>(`/api/overlord/memory/${encodeURIComponent(id)}`, {
      method: 'DELETE',
    }),

  // Tier 3: Dispatch
  parseTask: (task: string) =>
    fetchApi<OverlordPlan>('/api/overlord/dispatch/parse', {
      method: 'POST',
      body: JSON.stringify({ task }),
    }),

  executeTask: (task: string, autoApprove = false) =>
    fetchApi<OverlordDispatchResult>('/api/overlord/dispatch/execute', {
      method: 'POST',
      body: JSON.stringify({ task, auto_approve: autoApprove }),
    }),

  listProposals: (state?: string) => {
    const qs = state ? `?state=${encodeURIComponent(state)}` : '';
    return fetchApi<{ proposals: OverlordProposal[] }>(`/api/overlord/proposals${qs}`);
  },

  approveProposal: (id: string) =>
    fetchApi<{ message: string; result?: OverlordDispatchResult }>(
      `/api/overlord/proposals/${encodeURIComponent(id)}/approve`,
      { method: 'POST' }
    ),

  denyProposal: (id: string, reason = '') =>
    fetchApi<{ message: string }>(
      `/api/overlord/proposals/${encodeURIComponent(id)}/deny`,
      { method: 'POST', body: JSON.stringify({ reason }) }
    ),

  // Tier 4: Audit
  getAuditProposals: (state?: string, limit?: number) => {
    const searchParams = new URLSearchParams();
    if (state) searchParams.append('state', state);
    if (limit) searchParams.append('limit', limit.toString());
    const qs = searchParams.toString();
    return fetchApi<{ proposals: OverlordProposal[] }>(`/api/overlord/audit/proposals${qs ? `?${qs}` : ''}`);
  },

  getDetections: () =>
    fetchApi<{ detections: OverlordDetection[] }>('/api/overlord/audit/detections'),

  getNotificationStats: () =>
    fetchApi<OverlordNotificationStats>('/api/overlord/audit/notifications'),
};
