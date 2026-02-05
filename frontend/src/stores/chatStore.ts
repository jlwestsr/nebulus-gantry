import { create } from 'zustand';
import type { Conversation, SearchResult } from '../types/api';
import { chatApi } from '../services/api';

interface ChatState {
  conversations: Conversation[];
  currentConversationId: number | null;
  isLoading: boolean;
  error: string | null;

  // Search state
  searchQuery: string;
  searchResults: SearchResult[];
  isSearching: boolean;

  fetchConversations: () => Promise<void>;
  createConversation: () => Promise<number>;
  selectConversation: (id: number | null) => void;
  deleteConversation: (id: number) => Promise<void>;
  updateConversationTitle: (id: number, title: string) => void;

  // Pin action
  pinConversation: (id: number) => Promise<void>;

  // Search actions
  setSearchQuery: (query: string) => void;
  performSearch: (query: string) => Promise<void>;
  clearSearch: () => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  conversations: [],
  currentConversationId: null,
  isLoading: false,
  error: null,

  // Search state
  searchQuery: '',
  searchResults: [],
  isSearching: false,

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

  pinConversation: async (id: number) => {
    try {
      const updated = await chatApi.pinConversation(id);
      set((state) => {
        // Update the conversation in place
        const conversations = state.conversations.map((c) =>
          c.id === id ? { ...c, pinned: updated.pinned } : c
        );
        // Re-sort: pinned first, then by updated_at desc
        conversations.sort((a, b) => {
          if (a.pinned !== b.pinned) return a.pinned ? -1 : 1;
          return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
        });
        return { conversations };
      });
    } catch (err) {
      set({ error: (err as Error).message });
      throw err;
    }
  },

  setSearchQuery: (query: string) => {
    set({ searchQuery: query });
  },

  performSearch: async (query: string) => {
    if (!query.trim()) {
      set({ searchResults: [], isSearching: false });
      return;
    }
    set({ isSearching: true });
    try {
      const response = await chatApi.search(query);
      set({ searchResults: response.results, isSearching: false });
    } catch (err) {
      set({ error: (err as Error).message, isSearching: false });
    }
  },

  clearSearch: () => {
    set({ searchQuery: '', searchResults: [], isSearching: false });
  },
}));
