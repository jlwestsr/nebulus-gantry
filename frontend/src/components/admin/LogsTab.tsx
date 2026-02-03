import { useState } from 'react';

const SERVICES = [
  { value: 'gantry-api', label: 'Gantry API' },
  { value: 'gantry-ui', label: 'Gantry UI' },
  { value: 'chromadb', label: 'ChromaDB' },
  { value: 'ollama', label: 'Ollama' },
];

export function LogsTab() {
  const [selectedService, setSelectedService] = useState(SERVICES[0].value);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-medium text-gray-200">Service Logs</h3>
          <p className="text-sm text-gray-400 mt-1">
            View live logs from Nebulus services
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={selectedService}
            onChange={(e) => setSelectedService(e.target.value)}
            className="px-3 py-1.5 text-sm text-gray-300 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            {SERVICES.map((service) => (
              <option key={service.value} value={service.value}>
                {service.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Log viewer placeholder */}
      <div className="rounded-lg border border-gray-700 bg-gray-900/50 overflow-hidden">
        <div className="flex items-center justify-between px-4 py-2 border-b border-gray-700 bg-gray-800/50">
          <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">
            {SERVICES.find((s) => s.value === selectedService)?.label} Logs
          </span>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 text-xs text-gray-500">
              <span className="w-1.5 h-1.5 rounded-full bg-gray-600 animate-pulse" />
              Waiting for connection
            </span>
          </div>
        </div>
        <div className="p-4 min-h-[400px] font-mono text-xs">
          <div className="flex flex-col items-center justify-center h-80 text-gray-500">
            <svg
              className="w-12 h-12 mb-4 text-gray-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
            <p className="text-sm font-sans">Log streaming coming soon</p>
            <p className="text-xs mt-1 font-sans text-gray-600">
              SSE-based live log streaming will be available in a future update
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
