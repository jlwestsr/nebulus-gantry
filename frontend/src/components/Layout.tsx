import { type ReactNode, useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { useUIStore } from '../stores/uiStore';
import { SearchModal } from './SearchModal';

interface LayoutProps {
  children: ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const { user, logout } = useAuthStore();
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const { isSidebarOpen, toggleSidebar, closeSidebar } = useUIStore();

  const openSearch = useCallback(() => setIsSearchOpen(true), []);
  const closeSearch = useCallback(() => setIsSearchOpen(false), []);

  // Close sidebar when resizing to desktop
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth >= 768) {
        closeSidebar();
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [closeSidebar]);

  // Global keyboard shortcut: Ctrl+K / Cmd+K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsSearchOpen((prev) => !prev);
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <div className="min-h-screen bg-gray-900">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            {/* Hamburger menu for mobile */}
            <button
              onClick={toggleSidebar}
              className="md:hidden p-1.5 text-gray-400 hover:text-gray-200 rounded-lg hover:bg-gray-700 transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
              aria-label="Toggle sidebar"
            >
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                {isSidebarOpen ? (
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                ) : (
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 6h16M4 12h16M4 18h16"
                  />
                )}
              </svg>
            </button>

            <h1 className="text-xl font-semibold text-gray-100">
              Nebulus Gantry
            </h1>
          </div>

          <div className="flex items-center gap-3">
            {/* Search button */}
            <button
              onClick={openSearch}
              className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-400 bg-gray-700 border border-gray-600 rounded-lg hover:bg-gray-600 hover:text-gray-200 transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
              title="Search conversations (Ctrl+K)"
            >
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
              <span className="hidden sm:inline">Search</span>
              <kbd className="hidden sm:inline-block px-1.5 py-0.5 text-xs text-gray-500 bg-gray-800 rounded border border-gray-600">
                Ctrl+K
              </kbd>
            </button>

            {user && (
              <>
                {user.role === 'admin' && (
                  <>
                    <Link
                      to="/overlord"
                      className="text-sm text-gray-400 hover:text-gray-200 transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500/50 rounded px-2 py-1"
                    >
                      Overlord
                    </Link>
                    <Link
                      to="/admin"
                      className="text-sm text-gray-400 hover:text-gray-200 transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500/50 rounded px-2 py-1"
                    >
                      Admin
                    </Link>
                  </>
                )}
                <Link
                  to="/settings"
                  className="flex items-center gap-1.5 text-sm text-gray-400 hover:text-gray-200 transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500/50 rounded px-2 py-1"
                  title={user.display_name}
                >
                  <span className="w-6 h-6 rounded-full bg-blue-600 flex items-center justify-center text-xs font-medium text-white">
                    {user.display_name.charAt(0).toUpperCase()}
                  </span>
                  <span className="hidden sm:inline">
                    {user.display_name}
                  </span>
                </Link>
                <button
                  onClick={() => logout()}
                  className="text-sm text-gray-400 hover:text-gray-200 transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500/50 rounded px-2 py-1"
                >
                  Logout
                </button>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Mobile sidebar overlay */}
      {isSidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm md:hidden"
          onClick={closeSidebar}
        />
      )}

      {/* Main content */}
      <main>{children}</main>

      {/* Search Modal */}
      <SearchModal isOpen={isSearchOpen} onClose={closeSearch} />
    </div>
  );
}
