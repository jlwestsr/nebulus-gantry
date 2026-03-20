const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface StepResult {
  status: 'pending' | 'waiting' | 'running' | 'completed' | 'failed' | 'skipped';
  output?: string;
  error?: string;
  duration_seconds?: number;
  model_used?: string;
}

export interface Job {
  id: string;
  workflow: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  inputs: Record<string, string>;
  steps: Record<string, StepResult>;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  error?: string;
}

export interface Template {
  name: string;
  description: string;
  steps: string[];
}

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

export const orchestratorApi = {
  submitJob: (template: string, inputs: { goal: string }) =>
    fetchApi<Job>('/api/orchestrator/jobs', {
      method: 'POST',
      body: JSON.stringify({ template, inputs }),
    }),

  getJob: (jobId: string) =>
    fetchApi<Job>(`/api/orchestrator/jobs/${jobId}`),

  listJobs: () =>
    fetchApi<Job[]>('/api/orchestrator/jobs'),

  listTemplates: () =>
    fetchApi<Template[]>('/api/orchestrator/templates'),

  cancelJob: (jobId: string) =>
    fetchApi<{ message: string }>(`/api/orchestrator/jobs/${jobId}`, {
      method: 'DELETE',
    }),
};
