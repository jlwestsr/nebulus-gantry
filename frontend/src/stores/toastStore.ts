import { create } from 'zustand';

export interface Toast {
  id: string;
  type: 'success' | 'error' | 'info' | 'warning';
  message: string;
  duration?: number;
}

interface ToastState {
  toasts: Toast[];
  addToast: (toast: Omit<Toast, 'id'>) => void;
  removeToast: (id: string) => void;
}

export const useToastStore = create<ToastState>((set) => ({
  toasts: [],

  addToast: (toast) => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
    set((state) => ({
      toasts: [...state.toasts, { ...toast, id }],
    }));

    const duration = toast.duration ?? 5000;
    if (duration > 0) {
      setTimeout(() => {
        set((state) => ({
          toasts: state.toasts.filter((t) => t.id !== id),
        }));
      }, duration);
    }
  },

  removeToast: (id) => {
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    }));
  },
}));

// Convenience functions for use outside of React components
export const showSuccess = (message: string, duration?: number) =>
  useToastStore.getState().addToast({ type: 'success', message, duration });

export const showError = (message: string, duration?: number) =>
  useToastStore.getState().addToast({ type: 'error', message, duration: duration ?? 8000 });

export const showInfo = (message: string, duration?: number) =>
  useToastStore.getState().addToast({ type: 'info', message, duration });

export const showWarning = (message: string, duration?: number) =>
  useToastStore.getState().addToast({ type: 'warning', message, duration });
