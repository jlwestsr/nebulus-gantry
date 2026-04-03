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
      const apiUrl = import.meta.env.VITE_API_URL ?? '';
      const res = await fetch(`${apiUrl}/api/overlord/available`);
      if (res.ok) {
        const data = await res.json();
        set({ overlordAvailable: data.available === true });
      } else {
        set({ overlordAvailable: false });
      }
    } catch {
      set({ overlordAvailable: false });
    }
  },
}));
