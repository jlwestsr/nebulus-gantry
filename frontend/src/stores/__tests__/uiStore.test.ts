import { describe, it, expect, beforeEach } from 'vitest';
import { useUIStore } from '../uiStore';

describe('uiStore', () => {
  beforeEach(() => {
    useUIStore.setState({ isSidebarOpen: false });
  });

  it('starts with sidebar closed', () => {
    const state = useUIStore.getState();
    expect(state.isSidebarOpen).toBe(false);
  });

  it('toggleSidebar flips the state', () => {
    useUIStore.getState().toggleSidebar();
    expect(useUIStore.getState().isSidebarOpen).toBe(true);

    useUIStore.getState().toggleSidebar();
    expect(useUIStore.getState().isSidebarOpen).toBe(false);
  });

  it('openSidebar sets true', () => {
    useUIStore.getState().openSidebar();
    expect(useUIStore.getState().isSidebarOpen).toBe(true);
  });

  it('closeSidebar sets false', () => {
    useUIStore.getState().openSidebar();
    useUIStore.getState().closeSidebar();
    expect(useUIStore.getState().isSidebarOpen).toBe(false);
  });
});
