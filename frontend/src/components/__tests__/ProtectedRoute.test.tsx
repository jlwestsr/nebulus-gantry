import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, beforeEach } from 'vitest';
import { useAuthStore } from '../../stores/authStore';
import { ProtectedRoute } from '../ProtectedRoute';

function renderProtected() {
  return render(
    <MemoryRouter initialEntries={['/']}>
      <ProtectedRoute>
        <div>Protected Content</div>
      </ProtectedRoute>
    </MemoryRouter>,
  );
}

describe('ProtectedRoute', () => {
  beforeEach(() => {
    useAuthStore.setState({ user: null, isLoading: false, error: null });
  });

  it('shows loading state when isLoading is true', () => {
    useAuthStore.setState({ isLoading: true });
    renderProtected();
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('redirects to /login when no user', () => {
    useAuthStore.setState({ user: null, isLoading: false });
    renderProtected();
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  it('renders children when user is authenticated', () => {
    useAuthStore.setState({
      user: { id: 1, email: 'a@b.com', display_name: 'A', role: 'user' },
      isLoading: false,
    });
    renderProtected();
    expect(screen.getByText('Protected Content')).toBeInTheDocument();
  });
});
