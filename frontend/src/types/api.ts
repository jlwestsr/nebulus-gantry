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

// ── Overlord types ────────────────────────────────────────────────────────

export interface OverlordGitState {
  branch: string;
  clean: boolean;
  ahead: number;
  behind: number;
  last_commit: string;
  last_commit_date: string;
  stale_branches: string[];
}

export interface OverlordTestHealth {
  has_tests: boolean;
  test_command: string | null;
}

export interface OverlordProjectStatus {
  name: string;
  role: string;
  git: OverlordGitState;
  tests: OverlordTestHealth;
  issues: string[];
}

export interface OverlordDaemonStatus {
  running: boolean;
  pid: number | null;
}

export interface OverlordConfigSummary {
  autonomy_levels: Record<string, string>;
  scheduled_tasks: Array<{ name: string; cron: string; enabled: boolean }>;
}

export interface OverlordDashboard {
  projects: OverlordProjectStatus[];
  daemon: OverlordDaemonStatus;
  config: OverlordConfigSummary;
}

export interface OverlordGraph {
  adjacency: Record<string, string[]>;
  ascii: string;
}

export interface OverlordMemoryEntry {
  id: string;
  timestamp: string;
  category: string;
  project: string | null;
  content: string;
  metadata: Record<string, unknown>;
}

export interface OverlordMemoryList {
  entries: OverlordMemoryEntry[];
  count: number;
}

export interface OverlordScope {
  projects: string[];
  branches: string[];
  destructive: boolean;
  reversible: boolean;
  affects_remote: boolean;
  estimated_impact: string;
}

export interface OverlordStep {
  id: string;
  action: string;
  project: string;
  dependencies: string[];
  model_tier: string | null;
  timeout: number;
}

export interface OverlordPlan {
  task: string;
  steps: OverlordStep[];
  scope: OverlordScope;
  estimated_duration: number;
  requires_approval: boolean;
}

export interface OverlordStepResult {
  step_id: string;
  success: boolean;
  output: string;
  error: string | null;
  duration: number;
}

export interface OverlordDispatchResult {
  status: string;
  steps: OverlordStepResult[];
  reason: string;
}

export interface OverlordProposal {
  id: string;
  task: string;
  scope_projects: string[];
  scope_impact: string;
  affects_remote: boolean;
  reason: string;
  state: string;
  created_at: string;
  resolved_at: string | null;
  result_summary: string | null;
}

export interface OverlordDetection {
  detector: string;
  project: string;
  severity: string;
  description: string;
  proposed_action: string;
}

export interface OverlordNotificationStats {
  urgent_count: number;
  buffered_count: number;
  last_digest_time: string | null;
}
