import { create } from 'zustand';
import type { Job, Template } from '../api/orchestratorApi';
import { orchestratorApi } from '../api/orchestratorApi';

interface OrchestratorState {
  jobs: Job[];
  activeJobId: string | null;
  templates: Template[];
  isLoading: boolean;
  error: string | null;

  loadTemplates: () => Promise<void>;
  submitJob: (template: string, goal: string) => Promise<string>;
  pollJob: (jobId: string) => Promise<void>;
  loadJobs: () => Promise<void>;
  setActiveJob: (jobId: string | null) => void;
  cancelJob: (jobId: string) => Promise<void>;
}

export const useOrchestratorStore = create<OrchestratorState>((set, get) => ({
  jobs: [],
  activeJobId: null,
  templates: [],
  isLoading: false,
  error: null,

  loadTemplates: async () => {
    set({ isLoading: true, error: null });
    try {
      const templates = await orchestratorApi.listTemplates();
      set({ templates, isLoading: false });
    } catch (err) {
      set({ error: (err as Error).message, isLoading: false });
    }
  },

  submitJob: async (template: string, goal: string) => {
    set({ isLoading: true, error: null });
    try {
      const job = await orchestratorApi.submitJob(template, { goal });
      set((state) => ({
        jobs: [job, ...state.jobs],
        activeJobId: job.id,
        isLoading: false,
      }));
      return job.id;
    } catch (err) {
      set({ error: (err as Error).message, isLoading: false });
      throw err;
    }
  },

  pollJob: async (jobId: string) => {
    try {
      const job = await orchestratorApi.getJob(jobId);
      set((state) => ({
        jobs: state.jobs.map((j) => (j.id === jobId ? job : j)),
      }));
    } catch (err) {
      set({ error: (err as Error).message });
    }
  },

  loadJobs: async () => {
    set({ isLoading: true, error: null });
    try {
      const jobs = await orchestratorApi.listJobs();
      set({ jobs, isLoading: false });
    } catch (err) {
      set({ error: (err as Error).message, isLoading: false });
    }
  },

  setActiveJob: (jobId: string | null) => {
    set({ activeJobId: jobId });
  },

  cancelJob: async (jobId: string) => {
    try {
      await orchestratorApi.cancelJob(jobId);
      await get().pollJob(jobId);
    } catch (err) {
      set({ error: (err as Error).message });
      throw err;
    }
  },
}));
