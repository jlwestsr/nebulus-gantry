import { useState, useEffect } from 'react';
import { adminApi } from '../../services/api';
import type { AdminUser } from '../../types/api';

export function DataTab() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<string>('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadUsers() {
      try {
        const response = await adminApi.listUsers();
        setUsers(response.users);
      } catch (err) {
        setError('Failed to load users');
      }
    }
    loadUsers();
  }, []);

  const handleExport = () => {
    setIsLoading(true);
    setError(null);
    try {
      adminApi.bulkExport(
        selectedUserId ? parseInt(selectedUserId, 10) : undefined,
        dateFrom || undefined,
        dateTo || undefined
      );
      // The export is handled via form submission, so we can't detect completion
      // Just reset loading after a short delay
      setTimeout(() => setIsLoading(false), 1000);
    } catch (err) {
      setError('Export failed');
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Section header */}
      <div>
        <h2 className="text-lg font-medium text-gray-100">Data Export</h2>
        <p className="mt-1 text-sm text-gray-400">
          Export conversation data as a ZIP file containing JSON files.
        </p>
      </div>

      {/* Export form */}
      <div className="bg-gray-800/50 rounded-lg border border-gray-700 p-4 sm:p-6 space-y-4">
        {/* User filter */}
        <div>
          <label htmlFor="user-filter" className="block text-sm font-medium text-gray-300 mb-2">
            Filter by User
          </label>
          <select
            id="user-filter"
            value={selectedUserId}
            onChange={(e) => setSelectedUserId(e.target.value)}
            className="w-full sm:w-64 bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-transparent"
          >
            <option value="">All users</option>
            {users.map((user) => (
              <option key={user.id} value={user.id}>
                {user.display_name} ({user.email})
              </option>
            ))}
          </select>
        </div>

        {/* Date range */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label htmlFor="date-from" className="block text-sm font-medium text-gray-300 mb-2">
              From Date
            </label>
            <input
              type="datetime-local"
              id="date-from"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-transparent"
            />
          </div>
          <div>
            <label htmlFor="date-to" className="block text-sm font-medium text-gray-300 mb-2">
              To Date
            </label>
            <input
              type="datetime-local"
              id="date-to"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-transparent"
            />
          </div>
        </div>

        {/* Error message */}
        {error && (
          <div className="p-3 bg-red-900/30 border border-red-700 rounded-lg text-red-300 text-sm">
            {error}
          </div>
        )}

        {/* Export button */}
        <div className="pt-2">
          <button
            onClick={handleExport}
            disabled={isLoading}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-blue-500/50"
          >
            {isLoading ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                Exporting...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                  />
                </svg>
                Export Conversations
              </>
            )}
          </button>
        </div>

        {/* Help text */}
        <p className="text-xs text-gray-500">
          The export will download a ZIP file containing one JSON file per conversation.
          Each JSON file includes the conversation metadata and all messages.
        </p>
      </div>
    </div>
  );
}
