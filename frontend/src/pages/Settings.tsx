import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { adminApi } from '../services/api';
import type { Model } from '../types/api';

const THEME_KEY = 'nebulus-theme';
const APP_VERSION = '2.0.0';

type Theme = 'dark' | 'light';

function getStoredTheme(): Theme {
  return (localStorage.getItem(THEME_KEY) as Theme) || 'dark';
}

export function Settings() {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const [theme, setTheme] = useState<Theme>(getStoredTheme);
  const [activeModel, setActiveModel] = useState<Model | null>(null);
  const [modelsLoading, setModelsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function fetchActiveModel() {
      try {
        const { models } = await adminApi.listModels();
        if (!cancelled) {
          const active = models.find((m) => m.active) || null;
          setActiveModel(active);
        }
      } catch {
        // Non-critical: user may not have admin access
      } finally {
        if (!cancelled) setModelsLoading(false);
      }
    }
    fetchActiveModel();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleThemeChange = (newTheme: Theme) => {
    setTheme(newTheme);
    localStorage.setItem(THEME_KEY, newTheme);
  };

  return (
    <div className="min-h-[calc(100vh-57px)] bg-gray-900">
      {/* Page header */}
      <div className="border-b border-gray-700 bg-gray-800/50">
        <div className="max-w-3xl mx-auto px-6 py-4">
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/')}
              className="p-1.5 text-gray-400 hover:text-gray-200 rounded-lg hover:bg-gray-700 transition-colors"
              title="Back to Chat"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M10 19l-7-7m0 0l7-7m-7 7h18"
                />
              </svg>
            </button>
            <div>
              <h1 className="text-xl font-semibold text-gray-100">Settings</h1>
              <p className="text-sm text-gray-400 mt-0.5">
                Manage your preferences
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Settings sections */}
      <div className="max-w-3xl mx-auto px-6 py-6 space-y-6">
        {/* Profile Section */}
        <section className="bg-gray-800/50 border border-gray-700 rounded-lg">
          <div className="px-6 py-4 border-b border-gray-700">
            <h2 className="text-base font-medium text-gray-100 flex items-center gap-2">
              <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                />
              </svg>
              Profile
            </h2>
          </div>
          <div className="px-6 py-4 space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1">
                Display Name
              </label>
              <input
                type="text"
                value={user?.display_name || ''}
                readOnly
                className="w-full px-3 py-2 bg-gray-700/50 border border-gray-600 rounded-lg text-gray-200 text-sm focus:outline-none cursor-default"
              />
              <p className="text-xs text-gray-500 mt-1">
                Contact an admin to change your display name.
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1">
                Email
              </label>
              <input
                type="text"
                value={user?.email || ''}
                readOnly
                className="w-full px-3 py-2 bg-gray-700/50 border border-gray-600 rounded-lg text-gray-300 text-sm focus:outline-none cursor-default"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1">
                Role
              </label>
              <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium bg-gray-700 text-gray-300 border border-gray-600 capitalize">
                {user?.role || 'user'}
              </span>
            </div>
          </div>
        </section>

        {/* Appearance Section */}
        <section className="bg-gray-800/50 border border-gray-700 rounded-lg">
          <div className="px-6 py-4 border-b border-gray-700">
            <h2 className="text-base font-medium text-gray-100 flex items-center gap-2">
              <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01"
                />
              </svg>
              Appearance
            </h2>
          </div>
          <div className="px-6 py-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-200">Theme</p>
                <p className="text-xs text-gray-500 mt-0.5">
                  Choose your preferred color scheme
                </p>
              </div>
              <div className="flex items-center gap-1 bg-gray-700/50 border border-gray-600 rounded-lg p-0.5">
                <button
                  onClick={() => handleThemeChange('dark')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm transition-colors ${
                    theme === 'dark'
                      ? 'bg-gray-600 text-gray-100 shadow-sm'
                      : 'text-gray-400 hover:text-gray-200'
                  }`}
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.5}
                      d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
                    />
                  </svg>
                  Dark
                </button>
                <button
                  onClick={() => handleThemeChange('light')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm transition-colors ${
                    theme === 'light'
                      ? 'bg-gray-600 text-gray-100 shadow-sm'
                      : 'text-gray-400 hover:text-gray-200'
                  }`}
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.5}
                      d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
                    />
                  </svg>
                  Light
                </button>
              </div>
            </div>
            {theme === 'light' && (
              <p className="text-xs text-amber-400/80 mt-3">
                Light theme is not yet available. Dark mode will remain active.
              </p>
            )}
          </div>
        </section>

        {/* Model Section */}
        <section className="bg-gray-800/50 border border-gray-700 rounded-lg">
          <div className="px-6 py-4 border-b border-gray-700">
            <h2 className="text-base font-medium text-gray-100 flex items-center gap-2">
              <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                />
              </svg>
              Model
            </h2>
          </div>
          <div className="px-6 py-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-200">Active Model</p>
                <p className="text-xs text-gray-500 mt-0.5">
                  The AI model currently serving responses
                </p>
              </div>
              <div>
                {modelsLoading ? (
                  <span className="text-sm text-gray-500">Loading...</span>
                ) : activeModel ? (
                  <span className="inline-flex items-center px-3 py-1.5 rounded-md text-sm font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20">
                    {activeModel.name}
                  </span>
                ) : (
                  <span className="text-sm text-gray-500">Not available</span>
                )}
              </div>
            </div>
            <p className="text-xs text-gray-500 mt-3">
              Model selection is managed by administrators via the Admin Panel.
            </p>
          </div>
        </section>

        {/* About Section */}
        <section className="bg-gray-800/50 border border-gray-700 rounded-lg">
          <div className="px-6 py-4 border-b border-gray-700">
            <h2 className="text-base font-medium text-gray-100 flex items-center gap-2">
              <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              About
            </h2>
          </div>
          <div className="px-6 py-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-400">Application</span>
                <span className="text-sm text-gray-200">Nebulus Gantry</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-400">Version</span>
                <span className="text-sm font-mono text-gray-200">{APP_VERSION}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-400">Frontend</span>
                <span className="text-sm font-mono text-gray-200">React 19 + Vite 7</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-400">Backend</span>
                <span className="text-sm font-mono text-gray-200">FastAPI + Python 3.12</span>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
