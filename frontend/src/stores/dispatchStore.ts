import { create } from 'zustand';
import type { ActiveDispatch, BudgetStatus, DispatchEvent } from '../types/api';
import { overlordApi } from '../services/api';

interface DispatchState {
  activeDispatches: ActiveDispatch[];
  budget: BudgetStatus | null;
  events: DispatchEvent[];
  sidebarOpen: boolean;

  fetchActiveDispatches: () => Promise<void>;
  fetchBudget: () => Promise<void>;
  addEvent: (event: DispatchEvent) => void;
  clearEvents: () => void;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  haltAll: () => Promise<{ message: string; tasks_cancelled: number }>;
}

const SIDEBAR_KEY = 'gantry-situation-map-open';

function loadSidebarState(): boolean {
  try {
    const stored = localStorage.getItem(SIDEBAR_KEY);
    return stored === 'true';
  } catch {
    return false;
  }
}

export const useDispatchStore = create<DispatchState>((set, get) => ({
  activeDispatches: [],
  budget: null,
  events: [],
  sidebarOpen: loadSidebarState(),

  fetchActiveDispatches: async () => {
    try {
      const data = await overlordApi.getActiveDispatches();
      set({ activeDispatches: data.dispatches });
    } catch {
      // Silently fail — sidebar shows empty state
    }
  },

  fetchBudget: async () => {
    try {
      const budget = await overlordApi.getBudget();
      set({ budget });
    } catch {
      // Silently fail — budget shows as unavailable
    }
  },

  addEvent: (event: DispatchEvent) => {
    set((state) => ({ events: [...state.events, event] }));
  },

  clearEvents: () => {
    set({ events: [] });
  },

  toggleSidebar: () => {
    const newState = !get().sidebarOpen;
    try {
      localStorage.setItem(SIDEBAR_KEY, String(newState));
    } catch {
      // localStorage unavailable
    }
    set({ sidebarOpen: newState });
  },

  setSidebarOpen: (open: boolean) => {
    try {
      localStorage.setItem(SIDEBAR_KEY, String(open));
    } catch {
      // localStorage unavailable
    }
    set({ sidebarOpen: open });
  },

  haltAll: async () => {
    const result = await overlordApi.haltAll();
    // Refresh dispatches after halt
    get().fetchActiveDispatches();
    return result;
  },
}));
