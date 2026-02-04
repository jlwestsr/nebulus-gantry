import { describe, it, expect, beforeEach, vi } from 'vitest';

// Must mock before importing the module that reads import.meta.env at module scope
vi.stubEnv('VITE_API_URL', 'http://localhost:8000');

import { authApi, chatApi, adminApi } from '../api';

function mockFetch(data: unknown, ok = true, status = 200) {
  return vi.fn().mockResolvedValue({
    ok,
    status,
    json: () => Promise.resolve(data),
  });
}

describe('API service', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('fetchApi (via authApi)', () => {
    it('sends credentials: include', async () => {
      global.fetch = mockFetch({ id: 1, email: 'a@b.com', display_name: 'A', role: 'user' });

      await authApi.me();

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/auth/me',
        expect.objectContaining({ credentials: 'include' }),
      );
    });

    it('sends Content-Type: application/json', async () => {
      global.fetch = mockFetch({ message: 'ok' });

      await authApi.login({ email: 'a@b.com', password: 'pass' });

      const [, options] = vi.mocked(global.fetch).mock.calls[0];
      expect(options?.headers).toEqual(
        expect.objectContaining({ 'Content-Type': 'application/json' }),
      );
    });

    it('throws with detail message on non-ok response', async () => {
      global.fetch = mockFetch({ detail: 'Invalid credentials' }, false, 401);

      await expect(authApi.me()).rejects.toThrow('Invalid credentials');
    });

    it('throws generic message when response has no detail', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        json: () => Promise.reject(new Error('not json')),
      });

      await expect(authApi.me()).rejects.toThrow('Request failed');
    });
  });

  describe('authApi', () => {
    it('login POSTs to /api/auth/login', async () => {
      global.fetch = mockFetch({ message: 'ok' });

      await authApi.login({ email: 'a@b.com', password: 'pass' });

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/auth/login',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ email: 'a@b.com', password: 'pass' }),
        }),
      );
    });

    it('logout POSTs to /api/auth/logout', async () => {
      global.fetch = mockFetch({ message: 'ok' });
      await authApi.logout();
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/auth/logout',
        expect.objectContaining({ method: 'POST' }),
      );
    });
  });

  describe('chatApi', () => {
    it('getConversations GETs /api/chat/conversations', async () => {
      global.fetch = mockFetch([]);
      await chatApi.getConversations();
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/chat/conversations',
        expect.any(Object),
      );
    });

    it('createConversation POSTs to /api/chat/conversations', async () => {
      global.fetch = mockFetch({ id: 1, title: 'New', created_at: '', updated_at: '' });
      await chatApi.createConversation();
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/chat/conversations',
        expect.objectContaining({ method: 'POST' }),
      );
    });

    it('deleteConversation DELETEs correct URL', async () => {
      global.fetch = mockFetch({ message: 'ok' });
      await chatApi.deleteConversation(42);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/chat/conversations/42',
        expect.objectContaining({ method: 'DELETE' }),
      );
    });

    it('search encodes query parameter', async () => {
      global.fetch = mockFetch({ results: [] });
      await chatApi.search('hello world');
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/chat/search?q=hello%20world',
        expect.any(Object),
      );
    });
  });

  describe('adminApi', () => {
    it('listUsers GETs /api/admin/users', async () => {
      global.fetch = mockFetch({ users: [] });
      await adminApi.listUsers();
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/admin/users',
        expect.any(Object),
      );
    });

    it('createUser POSTs user data', async () => {
      global.fetch = mockFetch({ user: {}, message: 'ok' });
      const data = { email: 'new@test.com', password: 'pw', display_name: 'New', role: 'user' as const };
      await adminApi.createUser(data);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/admin/users',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(data),
        }),
      );
    });

    it('switchModel POSTs model_id', async () => {
      global.fetch = mockFetch({ message: 'ok' });
      await adminApi.switchModel('llama-70b');
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/admin/models/switch',
        expect.objectContaining({
          body: JSON.stringify({ model_id: 'llama-70b' }),
        }),
      );
    });
  });
});
