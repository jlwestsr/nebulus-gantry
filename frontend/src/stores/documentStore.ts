import { create } from 'zustand';
import type { Collection, Document, DocumentSearchResult } from '../types/api';
import { documentApi } from '../services/api';

interface DocumentState {
  collections: Collection[];
  documents: Document[];
  selectedCollectionId: number | null;
  isLoading: boolean;
  error: string | null;

  // Search
  searchResults: DocumentSearchResult[];
  isSearching: boolean;

  // Actions
  fetchCollections: () => Promise<void>;
  createCollection: (name: string, description?: string) => Promise<Collection>;
  updateCollection: (id: number, name?: string, description?: string) => Promise<void>;
  deleteCollection: (id: number) => Promise<void>;
  selectCollection: (id: number | null) => void;

  fetchDocuments: (collectionId?: number) => Promise<void>;
  uploadDocument: (file: File, collectionId?: number) => Promise<Document>;
  deleteDocument: (id: number) => Promise<void>;

  searchDocuments: (query: string, collectionIds?: number[]) => Promise<void>;
  clearSearch: () => void;
}

export const useDocumentStore = create<DocumentState>((set, get) => ({
  collections: [],
  documents: [],
  selectedCollectionId: null,
  isLoading: false,
  error: null,
  searchResults: [],
  isSearching: false,

  fetchCollections: async () => {
    set({ isLoading: true, error: null });
    try {
      const collections = await documentApi.listCollections();
      set({ collections, isLoading: false });
    } catch (err) {
      set({ error: (err as Error).message, isLoading: false });
    }
  },

  createCollection: async (name: string, description?: string) => {
    set({ isLoading: true, error: null });
    try {
      const collection = await documentApi.createCollection({ name, description });
      set((state) => ({
        collections: [collection, ...state.collections],
        isLoading: false,
      }));
      return collection;
    } catch (err) {
      set({ error: (err as Error).message, isLoading: false });
      throw err;
    }
  },

  updateCollection: async (id: number, name?: string, description?: string) => {
    try {
      const updated = await documentApi.updateCollection(id, { name, description });
      set((state) => ({
        collections: state.collections.map((c) => (c.id === id ? updated : c)),
      }));
    } catch (err) {
      set({ error: (err as Error).message });
      throw err;
    }
  },

  deleteCollection: async (id: number) => {
    try {
      await documentApi.deleteCollection(id);
      const { selectedCollectionId } = get();
      set((state) => ({
        collections: state.collections.filter((c) => c.id !== id),
        selectedCollectionId: selectedCollectionId === id ? null : selectedCollectionId,
        documents: state.documents.filter((d) => d.collection_id !== id),
      }));
    } catch (err) {
      set({ error: (err as Error).message });
      throw err;
    }
  },

  selectCollection: (id: number | null) => {
    set({ selectedCollectionId: id });
    get().fetchDocuments(id ?? undefined);
  },

  fetchDocuments: async (collectionId?: number) => {
    set({ isLoading: true, error: null });
    try {
      const documents = await documentApi.listDocuments(collectionId);
      set({ documents, isLoading: false });
    } catch (err) {
      set({ error: (err as Error).message, isLoading: false });
    }
  },

  uploadDocument: async (file: File, collectionId?: number) => {
    set({ isLoading: true, error: null });
    try {
      const document = await documentApi.uploadDocument(file, collectionId);
      set((state) => ({
        documents: [document, ...state.documents],
        // Update collection document count
        collections: state.collections.map((c) =>
          c.id === collectionId
            ? { ...c, document_count: c.document_count + 1 }
            : c
        ),
        isLoading: false,
      }));
      return document;
    } catch (err) {
      set({ error: (err as Error).message, isLoading: false });
      throw err;
    }
  },

  deleteDocument: async (id: number) => {
    const document = get().documents.find((d) => d.id === id);
    try {
      await documentApi.deleteDocument(id);
      set((state) => ({
        documents: state.documents.filter((d) => d.id !== id),
        // Update collection document count
        collections: state.collections.map((c) =>
          c.id === document?.collection_id
            ? { ...c, document_count: Math.max(0, c.document_count - 1) }
            : c
        ),
      }));
    } catch (err) {
      set({ error: (err as Error).message });
      throw err;
    }
  },

  searchDocuments: async (query: string, collectionIds?: number[]) => {
    if (!query.trim()) {
      set({ searchResults: [], isSearching: false });
      return;
    }
    set({ isSearching: true });
    try {
      const response = await documentApi.search(query, collectionIds);
      set({ searchResults: response.results, isSearching: false });
    } catch (err) {
      set({ error: (err as Error).message, isSearching: false });
    }
  },

  clearSearch: () => {
    set({ searchResults: [], isSearching: false });
  },
}));
