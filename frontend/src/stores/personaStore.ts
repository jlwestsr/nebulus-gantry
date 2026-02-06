import { create } from 'zustand';
import type { Persona, CreatePersonaRequest, UpdatePersonaRequest } from '../types/api';
import { personaApi } from '../services/api';

interface PersonaState {
  personas: Persona[];
  isLoading: boolean;
  error: string | null;

  // Actions
  fetchPersonas: () => Promise<void>;
  createPersona: (data: CreatePersonaRequest) => Promise<Persona>;
  updatePersona: (id: number, data: UpdatePersonaRequest) => Promise<void>;
  deletePersona: (id: number) => Promise<void>;
  setConversationPersona: (conversationId: number, personaId: number | null) => Promise<void>;
}

export const usePersonaStore = create<PersonaState>((set) => ({
  personas: [],
  isLoading: false,
  error: null,

  fetchPersonas: async () => {
    set({ isLoading: true, error: null });
    try {
      const personas = await personaApi.list();
      set({ personas, isLoading: false });
    } catch (err) {
      set({ error: (err as Error).message, isLoading: false });
    }
  },

  createPersona: async (data: CreatePersonaRequest) => {
    set({ isLoading: true, error: null });
    try {
      const persona = await personaApi.create(data);
      set((state) => ({
        personas: [persona, ...state.personas],
        isLoading: false,
      }));
      return persona;
    } catch (err) {
      set({ error: (err as Error).message, isLoading: false });
      throw err;
    }
  },

  updatePersona: async (id: number, data: UpdatePersonaRequest) => {
    try {
      const updated = await personaApi.update(id, data);
      set((state) => ({
        personas: state.personas.map((p) => (p.id === id ? updated : p)),
      }));
    } catch (err) {
      set({ error: (err as Error).message });
      throw err;
    }
  },

  deletePersona: async (id: number) => {
    try {
      await personaApi.delete(id);
      set((state) => ({
        personas: state.personas.filter((p) => p.id !== id),
      }));
    } catch (err) {
      set({ error: (err as Error).message });
      throw err;
    }
  },

  setConversationPersona: async (conversationId: number, personaId: number | null) => {
    try {
      await personaApi.setConversationPersona(conversationId, personaId);
    } catch (err) {
      set({ error: (err as Error).message });
      throw err;
    }
  },
}));
