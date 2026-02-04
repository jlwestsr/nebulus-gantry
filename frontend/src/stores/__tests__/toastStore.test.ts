import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { useToastStore, showSuccess, showError, showInfo, showWarning } from '../toastStore';

describe('toastStore', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    useToastStore.setState({ toasts: [] });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('addToast adds a toast with generated id', () => {
    useToastStore.getState().addToast({ type: 'info', message: 'Hello' });
    const toasts = useToastStore.getState().toasts;
    expect(toasts).toHaveLength(1);
    expect(toasts[0].type).toBe('info');
    expect(toasts[0].message).toBe('Hello');
    expect(toasts[0].id).toBeTruthy();
  });

  it('removeToast removes by id', () => {
    useToastStore.getState().addToast({ type: 'info', message: 'One' });
    const id = useToastStore.getState().toasts[0].id;
    useToastStore.getState().removeToast(id);
    expect(useToastStore.getState().toasts).toHaveLength(0);
  });

  it('auto-removes toast after default duration (5000ms)', () => {
    useToastStore.getState().addToast({ type: 'info', message: 'Temp' });
    expect(useToastStore.getState().toasts).toHaveLength(1);

    vi.advanceTimersByTime(5000);
    expect(useToastStore.getState().toasts).toHaveLength(0);
  });

  it('auto-removes toast after custom duration', () => {
    useToastStore.getState().addToast({ type: 'info', message: 'Quick', duration: 1000 });
    vi.advanceTimersByTime(1000);
    expect(useToastStore.getState().toasts).toHaveLength(0);
  });

  it('does not auto-remove when duration is 0', () => {
    useToastStore.getState().addToast({ type: 'info', message: 'Sticky', duration: 0 });
    vi.advanceTimersByTime(60000);
    expect(useToastStore.getState().toasts).toHaveLength(1);
  });

  it('showSuccess convenience function works', () => {
    showSuccess('Saved!');
    const toasts = useToastStore.getState().toasts;
    expect(toasts[0].type).toBe('success');
    expect(toasts[0].message).toBe('Saved!');
  });

  it('showError uses 8000ms default duration', () => {
    showError('Oops');
    expect(useToastStore.getState().toasts).toHaveLength(1);

    vi.advanceTimersByTime(5000);
    expect(useToastStore.getState().toasts).toHaveLength(1); // still there

    vi.advanceTimersByTime(3000);
    expect(useToastStore.getState().toasts).toHaveLength(0); // gone at 8000ms
  });

  it('showInfo and showWarning work', () => {
    showInfo('FYI');
    showWarning('Watch out');
    const toasts = useToastStore.getState().toasts;
    expect(toasts).toHaveLength(2);
    expect(toasts[0].type).toBe('info');
    expect(toasts[1].type).toBe('warning');
  });
});
