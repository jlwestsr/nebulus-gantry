import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useChatStore } from '../chatStore';

vi.mock('../../services/api', () => ({
  chatApi: {
    getConversations: vi.fn(),
    createConversation: vi.fn(),
    deleteConversation: vi.fn(),
  },
}));

import { chatApi } from '../../services/api';

const mockConversations = [
  { id: 1, title: 'First', created_at: '2026-01-01', updated_at: '2026-01-01' },
  { id: 2, title: 'Second', created_at: '2026-01-02', updated_at: '2026-01-02' },
];

describe('chatStore', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useChatStore.setState({
      conversations: [],
      currentConversationId: null,
      isLoading: false,
      error: null,
    });
  });

  describe('fetchConversations', () => {
    it('loads conversations from API', async () => {
      vi.mocked(chatApi.getConversations).mockResolvedValue(mockConversations);

      await useChatStore.getState().fetchConversations();

      const state = useChatStore.getState();
      expect(state.conversations).toEqual(mockConversations);
      expect(state.isLoading).toBe(false);
      expect(state.error).toBeNull();
    });

    it('sets error on failure', async () => {
      vi.mocked(chatApi.getConversations).mockRejectedValue(new Error('Network error'));

      await useChatStore.getState().fetchConversations();

      expect(useChatStore.getState().error).toBe('Network error');
      expect(useChatStore.getState().isLoading).toBe(false);
    });
  });

  describe('createConversation', () => {
    it('prepends new conversation and selects it', async () => {
      useChatStore.setState({ conversations: mockConversations });
      const newConv = { id: 3, title: 'New Conversation', created_at: '2026-01-03', updated_at: '2026-01-03' };
      vi.mocked(chatApi.createConversation).mockResolvedValue(newConv);

      const id = await useChatStore.getState().createConversation();

      const state = useChatStore.getState();
      expect(id).toBe(3);
      expect(state.conversations[0]).toEqual(newConv);
      expect(state.conversations).toHaveLength(3);
      expect(state.currentConversationId).toBe(3);
    });

    it('throws on failure', async () => {
      vi.mocked(chatApi.createConversation).mockRejectedValue(new Error('Server error'));

      await expect(useChatStore.getState().createConversation()).rejects.toThrow('Server error');
      expect(useChatStore.getState().error).toBe('Server error');
    });
  });

  describe('selectConversation', () => {
    it('sets currentConversationId', () => {
      useChatStore.getState().selectConversation(42);
      expect(useChatStore.getState().currentConversationId).toBe(42);
    });

    it('accepts null to deselect', () => {
      useChatStore.setState({ currentConversationId: 1 });
      useChatStore.getState().selectConversation(null);
      expect(useChatStore.getState().currentConversationId).toBeNull();
    });
  });

  describe('deleteConversation', () => {
    it('removes conversation from list', async () => {
      useChatStore.setState({ conversations: mockConversations, currentConversationId: 2 });
      vi.mocked(chatApi.deleteConversation).mockResolvedValue({ message: 'ok' });

      await useChatStore.getState().deleteConversation(1);

      const state = useChatStore.getState();
      expect(state.conversations).toHaveLength(1);
      expect(state.conversations[0].id).toBe(2);
      expect(state.currentConversationId).toBe(2); // unchanged
    });

    it('clears selection if deleted conversation was selected', async () => {
      useChatStore.setState({ conversations: mockConversations, currentConversationId: 1 });
      vi.mocked(chatApi.deleteConversation).mockResolvedValue({ message: 'ok' });

      await useChatStore.getState().deleteConversation(1);
      expect(useChatStore.getState().currentConversationId).toBeNull();
    });

    it('throws on failure', async () => {
      useChatStore.setState({ conversations: mockConversations });
      vi.mocked(chatApi.deleteConversation).mockRejectedValue(new Error('Forbidden'));

      await expect(useChatStore.getState().deleteConversation(1)).rejects.toThrow('Forbidden');
      expect(useChatStore.getState().error).toBe('Forbidden');
    });
  });

  describe('updateConversationTitle', () => {
    it('updates title for matching conversation', () => {
      useChatStore.setState({ conversations: mockConversations });
      useChatStore.getState().updateConversationTitle(1, 'Renamed');

      const conv = useChatStore.getState().conversations.find(c => c.id === 1);
      expect(conv?.title).toBe('Renamed');
    });

    it('does not affect other conversations', () => {
      useChatStore.setState({ conversations: mockConversations });
      useChatStore.getState().updateConversationTitle(1, 'Renamed');

      const conv2 = useChatStore.getState().conversations.find(c => c.id === 2);
      expect(conv2?.title).toBe('Second');
    });
  });
});
