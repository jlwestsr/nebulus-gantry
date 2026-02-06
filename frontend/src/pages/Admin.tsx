import { useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { ServicesTab } from '../components/admin/ServicesTab';
import { ModelsTab } from '../components/admin/ModelsTab';
import { LogsTab } from '../components/admin/LogsTab';
import { UsersTab } from '../components/admin/UsersTab';
import { DataTab } from '../components/admin/DataTab';
import { PersonasTab } from '../components/admin/PersonasTab';

type TabId = 'services' | 'models' | 'logs' | 'users' | 'data' | 'personas';

interface Tab {
  id: TabId;
  label: string;
  icon: ReactNode;
}

const TABS: Tab[] = [
  {
    id: 'services',
    label: 'Services',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01"
        />
      </svg>
    ),
  },
  {
    id: 'models',
    label: 'Models',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
        />
      </svg>
    ),
  },
  {
    id: 'logs',
    label: 'Logs',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
        />
      </svg>
    ),
  },
  {
    id: 'users',
    label: 'Users',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"
        />
      </svg>
    ),
  },
  {
    id: 'data',
    label: 'Data',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
        />
      </svg>
    ),
  },
  {
    id: 'personas',
    label: 'Personas',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
        />
      </svg>
    ),
  },
];

export function Admin() {
  const [activeTab, setActiveTab] = useState<TabId>('services');
  const navigate = useNavigate();

  const renderTabContent = () => {
    switch (activeTab) {
      case 'services':
        return <ServicesTab />;
      case 'models':
        return <ModelsTab />;
      case 'logs':
        return <LogsTab />;
      case 'users':
        return <UsersTab />;
      case 'data':
        return <DataTab />;
      case 'personas':
        return <PersonasTab />;
    }
  };

  return (
    <div className="min-h-[calc(100vh-57px)] bg-gray-900">
      {/* Page header */}
      <div className="border-b border-gray-700 bg-gray-800/50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <button
                onClick={() => navigate('/')}
                className="p-1.5 text-gray-400 hover:text-gray-200 rounded-lg hover:bg-gray-700 transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
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
                <h1 className="text-lg sm:text-xl font-semibold text-gray-100">
                  Admin Panel
                </h1>
                <p className="hidden sm:block text-sm text-gray-400 mt-0.5">
                  Manage services, models, and users
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Tab navigation */}
      <div className="border-b border-gray-700 bg-gray-800/30">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <nav className="flex gap-0 sm:gap-1 overflow-x-auto scrollbar-none" role="tablist">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                role="tab"
                aria-selected={activeTab === tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-1.5 sm:gap-2 px-3 sm:px-4 py-3 text-sm font-medium border-b-2 transition-colors duration-200 whitespace-nowrap ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-400'
                    : 'border-transparent text-gray-400 hover:text-gray-200 hover:border-gray-600'
                }`}
              >
                {tab.icon}
                {tab.label}
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Tab content */}
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-4 sm:py-6">
        {renderTabContent()}
      </div>
    </div>
  );
}
