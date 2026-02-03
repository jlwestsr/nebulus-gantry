import { create } from 'zustand';
import type { Conversation } from '../types/api';
import { chatApi } from '../services/api';

interface ChatState {
  conversations: Conversation[];
  currentConversationId: number | null;
  isLoading: boolean;
  error: string | null;

  fetchConversations: () => Promise<void>;
  createConversation: () => Promise<number>;
  selectConversation: (id: number | null) => void;
  deleteConversation: (id: number) => Promise<void>;
  updateConversationTitle: (id: number, title: string) => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  conversations: [],
  currentConversationId: null,
  isLoading: false,
  error: null,

  fetchConversations: async () => {
    set({ isLoading: true, error: null });
    try {
      const conversations = await chatApi.getConversations();
      set({ conversations, isLoading: false });
    } catch (err) {
      set({ error: (err as Error).message, isLoading: false });
    }
  },

  createConversation: async () => {
    set({ isLoading: true, error: null });
    try {
      const conversation = await chatApi.createConversation();
      set((state) => ({
        conversations: [conversation, ...state.conversations],
        currentConversationId: conversation.id,
        isLoading: false,
      }));
      return conversation.id;
    } catch (err) {
      set({ error: (err as Error).message, isLoading: false });
      throw err;
    }
  },

  selectConversation: (id: number | null) => {
    set({ currentConversationId: id });
  },

  deleteConversation: async (id: number) => {
    try {
      await chatApi.deleteConversation(id);
      const { currentConversationId } = get();
      set((state) => ({
        conversations: state.conversations.filter((c) => c.id !== id),
        currentConversationId: currentConversationId === id ? null : currentConversationId,
      }));
    } catch (err) {
      set({ error: (err as Error).message });
      throw err;
    }
  },

  updateConversationTitle: (id: number, title: string) => {
    set((state) => ({
      conversations: state.conversations.map((c) =>
        c.id === id ? { ...c, title } : c
      ),
    }));
  },
}));
