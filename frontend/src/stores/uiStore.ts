import { create } from 'zustand';

interface UIState {
  isSidebarOpen: boolean;
  overlordAvailable: boolean | null;
  toggleSidebar: () => void;
  openSidebar: () => void;
  closeSidebar: () => void;
  checkOverlord: () => Promise<void>;
}

export const useUIStore = create<UIState>((set) => ({
  isSidebarOpen: false,
  overlordAvailable: null,
  toggleSidebar: () => set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),
  openSidebar: () => set({ isSidebarOpen: true }),
  closeSidebar: () => set({ isSidebarOpen: false }),
  checkOverlord: async () => {
    try {
      const res = await fetch('/api/overlord/dashboard', { credentials: 'include' });
      set({ overlordAvailable: res.status !== 503 });
    } catch {
      set({ overlordAvailable: false });
    }
  },
}));
