import { useEffect, useState, useCallback } from 'react';
import { adminApi } from '../../services/api';
import type { Service } from '../../types/api';

export function ServicesTab() {
  const [services, setServices] = useState<Service[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [restartingService, setRestartingService] = useState<string | null>(null);

  const fetchServices = useCallback(async () => {
    try {
      setError(null);
      const data = await adminApi.listServices();
      setServices(data.services);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchServices();
  }, [fetchServices]);

  const handleRestart = async (serviceName: string) => {
    setRestartingService(serviceName);
    try {
      await adminApi.restartService(serviceName);
      // Refresh services after restart
      await fetchServices();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setRestartingService(null);
    }
  };

  const statusBadge = (status: string) => {
    const isRunning = status === 'running';
    const isStopped = ['exited', 'stopped', 'dead', 'created'].includes(status);
    const colorClass = isRunning
      ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
      : isStopped
        ? 'bg-red-500/20 text-red-400 border-red-500/30'
        : 'bg-amber-500/20 text-amber-400 border-amber-500/30';
    const dotClass = isRunning
      ? 'bg-emerald-400'
      : isStopped
        ? 'bg-red-400'
        : 'bg-amber-400';
    return (
      <span
        className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${colorClass}`}
      >
        <span className={`w-1.5 h-1.5 rounded-full ${dotClass}`} />
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    );
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-gray-400">Loading services...</div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-medium text-gray-200">Container Services</h3>
          <p className="text-sm text-gray-400 mt-1">
            Manage Nebulus container services
          </p>
        </div>
        <button
          onClick={fetchServices}
          className="px-3 py-1.5 text-sm text-gray-300 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
        >
          Refresh
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 text-sm text-red-300 bg-red-900/30 border border-red-800 rounded-lg">
          {error}
        </div>
      )}

      <div className="overflow-hidden rounded-lg border border-gray-700">
        <table className="w-full">
          <thead>
            <tr className="bg-gray-800/50">
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Service
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Status
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Container ID
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700">
            {services.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-gray-500">
                  No services found
                </td>
              </tr>
            ) : (
              services.map((service) => (
                <tr key={service.name} className="hover:bg-gray-800/30 transition-colors">
                  <td className="px-4 py-3 text-sm font-medium text-gray-200">
                    {service.name}
                  </td>
                  <td className="px-4 py-3 text-sm">
                    {statusBadge(service.status)}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-400 font-mono">
                    {service.container_id
                      ? service.container_id.substring(0, 12)
                      : '--'}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => handleRestart(service.name)}
                      disabled={restartingService === service.name}
                      className="px-3 py-1.5 text-xs font-medium text-amber-400 bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {restartingService === service.name
                        ? 'Restarting...'
                        : 'Restart'}
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
