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
  pinned: boolean;
  persona_id: number | null;
  persona_name: string | null;
  document_scope: string | null; // JSON string
  created_at: string;
  updated_at: string;
}

export interface MessageMeta {
  generation_time_ms?: number;
  prompt_tokens?: number;
  completion_tokens?: number;
  total_tokens?: number;
}

export interface Message {
  id: number;
  conversation_id: number;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
  meta?: MessageMeta;
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

export interface UpdateUserRequest {
  display_name?: string;
  role?: 'user' | 'admin';
  password?: string;
}

export interface Service {
  name: string;
  status: string;
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

// Knowledge Vault types
export interface Collection {
  id: number;
  name: string;
  description: string | null;
  is_default: boolean;
  document_count: number;
  created_at: string;
}

export interface Document {
  id: number;
  filename: string;
  content_type: string;
  file_size: number;
  chunk_count: number;
  status: 'processing' | 'ready' | 'failed';
  error_message: string | null;
  collection_id: number | null;
  created_at: string;
}

export interface DocumentSearchResult {
  document_id: number;
  filename: string;
  chunk_text: string;
  similarity: number;
}

export interface DocumentSearchResponse {
  results: DocumentSearchResult[];
}

// Persona types
export interface Persona {
  id: number;
  user_id: number | null;
  name: string;
  description: string | null;
  system_prompt: string;
  temperature: number;
  model_id: string | null;
  is_default: boolean;
  is_system: boolean;
  created_at: string;
}

export interface CreatePersonaRequest {
  name: string;
  description?: string;
  system_prompt: string;
  temperature?: number;
  model_id?: string;
}

export interface UpdatePersonaRequest {
  name?: string;
  description?: string;
  system_prompt?: string;
  temperature?: number;
  model_id?: string;
}

export interface CreateCollectionRequest {
  name: string;
  description?: string;
}

export interface UpdateCollectionRequest {
  name?: string;
  description?: string;
}

export interface DocumentScope {
  type: 'document' | 'collection';
  id: number;
}
