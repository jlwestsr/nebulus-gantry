export interface User {
  id: number;
  email: string;
  display_name: string;
  role: 'user' | 'admin';
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface Conversation {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: number;
  conversation_id: number;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

export interface ApiError {
  detail: string;
}

// Admin types
export interface AdminUser {
  id: number;
  email: string;
  display_name: string;
  role: 'user' | 'admin';
  created_at?: string;
}

export interface CreateUserRequest {
  email: string;
  password: string;
  display_name: string;
  role: 'user' | 'admin';
}

export interface Service {
  name: string;
  status: 'running' | 'stopped' | 'error';
  container_id?: string;
}

export interface Model {
  id: string;
  name: string;
  active: boolean;
}

// Search types
export interface SearchResult {
  conversation_id: number;
  conversation_title: string;
  message_snippet: string;
  role: 'user' | 'assistant';
  created_at: string;
}

export interface SearchResponse {
  results: SearchResult[];
}
