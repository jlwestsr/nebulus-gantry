import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useAuthStore } from '../authStore';

// Mock the API module
vi.mock('../../services/api', () => ({
  authApi: {
    login: vi.fn(),
    logout: vi.fn(),
    me: vi.fn(),
  },
}));

import { authApi } from '../../services/api';

const mockUser = { id: 1, email: 'test@test.com', display_name: 'Test', role: 'user' as const };

describe('authStore', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.setState({ user: null, isLoading: true, error: null });
  });

  describe('login', () => {
    it('sets user on successful login', async () => {
      vi.mocked(authApi.login).mockResolvedValue({ message: 'ok' });
      vi.mocked(authApi.me).mockResolvedValue(mockUser);

      await useAuthStore.getState().login('test@test.com', 'pass');

      const state = useAuthStore.getState();
      expect(state.user).toEqual(mockUser);
      expect(state.isLoading).toBe(false);
      expect(state.error).toBeNull();
    });

    it('sets isLoading during login', async () => {
      vi.mocked(authApi.login).mockImplementation(() => new Promise(() => {})); // never resolves

      useAuthStore.setState({ isLoading: false });
      useAuthStore.getState().login('test@test.com', 'pass');

      expect(useAuthStore.getState().isLoading).toBe(true);
    });

    it('sets error on login failure', async () => {
      vi.mocked(authApi.login).mockRejectedValue(new Error('Invalid credentials'));

      await expect(useAuthStore.getState().login('bad@test.com', 'wrong')).rejects.toThrow();

      const state = useAuthStore.getState();
      expect(state.user).toBeNull();
      expect(state.isLoading).toBe(false);
      expect(state.error).toBe('Invalid credentials');
    });

    it('clears previous error on new login attempt', async () => {
      useAuthStore.setState({ error: 'old error' });
      vi.mocked(authApi.login).mockResolvedValue({ message: 'ok' });
      vi.mocked(authApi.me).mockResolvedValue(mockUser);

      await useAuthStore.getState().login('test@test.com', 'pass');
      expect(useAuthStore.getState().error).toBeNull();
    });
  });

  describe('logout', () => {
    it('clears user on logout', async () => {
      useAuthStore.setState({ user: mockUser });
      vi.mocked(authApi.logout).mockResolvedValue({ message: 'ok' });

      await useAuthStore.getState().logout();
      expect(useAuthStore.getState().user).toBeNull();
    });

    it('clears user even if API call fails', async () => {
      useAuthStore.setState({ user: mockUser });
      vi.mocked(authApi.logout).mockRejectedValue(new Error('Network error'));

      await useAuthStore.getState().logout().catch(() => {});
      expect(useAuthStore.getState().user).toBeNull();
    });
  });

  describe('checkAuth', () => {
    it('sets user if session is valid', async () => {
      vi.mocked(authApi.me).mockResolvedValue(mockUser);

      await useAuthStore.getState().checkAuth();

      const state = useAuthStore.getState();
      expect(state.user).toEqual(mockUser);
      expect(state.isLoading).toBe(false);
    });

    it('clears user if session is invalid', async () => {
      vi.mocked(authApi.me).mockRejectedValue(new Error('Unauthorized'));

      await useAuthStore.getState().checkAuth();

      const state = useAuthStore.getState();
      expect(state.user).toBeNull();
      expect(state.isLoading).toBe(false);
    });
  });
});
