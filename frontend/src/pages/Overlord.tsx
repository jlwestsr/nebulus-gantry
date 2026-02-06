import { useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { EcosystemTab } from '../components/overlord/EcosystemTab';
import { MemoryTab } from '../components/overlord/MemoryTab';
import { DispatchTab } from '../components/overlord/DispatchTab';
import { AuditTab } from '../components/overlord/AuditTab';

type TabId = 'ecosystem' | 'memory' | 'dispatch' | 'audit';

interface Tab {
  id: TabId;
  label: string;
  icon: ReactNode;
}

const TABS: Tab[] = [
  {
    id: 'ecosystem',
    label: 'Ecosystem',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
    ),
  },
  {
    id: 'memory',
    label: 'Memory',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"
        />
      </svg>
    ),
  },
  {
    id: 'dispatch',
    label: 'Dispatch',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M13 10V3L4 14h7v7l9-11h-7z"
        />
      </svg>
    ),
  },
  {
    id: 'audit',
    label: 'Audit Log',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"
        />
      </svg>
    ),
  },
];

export function Overlord() {
  const [activeTab, setActiveTab] = useState<TabId>('ecosystem');
  const navigate = useNavigate();

  const renderTabContent = () => {
    switch (activeTab) {
      case 'ecosystem':
        return <EcosystemTab />;
      case 'memory':
        return <MemoryTab />;
      case 'dispatch':
        return <DispatchTab />;
      case 'audit':
        return <AuditTab />;
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
                  Overlord Control Plane
                </h1>
                <p className="hidden sm:block text-sm text-gray-400 mt-0.5">
                  Cross-project orchestration dashboard
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
