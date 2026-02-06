import { useState, useEffect, useCallback } from 'react';
import { overlordApi } from '../../services/api';
import type {
  OverlordProposal,
  OverlordDetection,
  OverlordNotificationStats,
} from '../../types/api';

const STATE_FILTERS = ['all', 'completed', 'failed', 'denied', 'expired'] as const;

export function AuditTab() {
  const [proposals, setProposals] = useState<OverlordProposal[]>([]);
  const [detections, setDetections] = useState<OverlordDetection[]>([]);
  const [notifStats, setNotifStats] = useState<OverlordNotificationStats | null>(null);
  const [stateFilter, setStateFilter] = useState<string>('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [proposalData, detectionData, statsData] = await Promise.all([
        overlordApi.getAuditProposals(stateFilter === 'all' ? undefined : stateFilter),
        overlordApi.getDetections(),
        overlordApi.getNotificationStats(),
      ]);
      setProposals(proposalData.proposals);
      setDetections(detectionData.detections);
      setNotifStats(statsData);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, [stateFilter]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-gray-400 text-sm">Loading audit data...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-800 bg-red-900/20 p-4">
        <p className="text-red-400 text-sm">{error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Notification stats */}
      {notifStats && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <StatCard label="Urgent" value={notifStats.urgent_count} color="red" />
          <StatCard label="Buffered" value={notifStats.buffered_count} color="yellow" />
          <StatCard
            label="Last Digest"
            value={notifStats.last_digest_time
              ? new Date(notifStats.last_digest_time).toLocaleString()
              : 'Never'}
            color="blue"
            isText
          />
        </div>
      )}

      {/* Proposal history */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium text-gray-300">Proposal History</h3>
          <button
            onClick={refresh}
            className="text-xs text-gray-400 hover:text-gray-200 transition-colors"
          >
            Refresh
          </button>
        </div>

        {/* State filter tabs */}
        <div className="flex gap-1 overflow-x-auto">
          {STATE_FILTERS.map((filter) => (
            <button
              key={filter}
              onClick={() => setStateFilter(filter)}
              className={`text-xs px-3 py-1.5 rounded-full transition-colors capitalize whitespace-nowrap ${
                stateFilter === filter
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
              }`}
            >
              {filter}
            </button>
          ))}
        </div>

        {/* Proposals table */}
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 border-b border-gray-700">
                <th className="pb-2 pr-3">ID</th>
                <th className="pb-2 pr-3">Task</th>
                <th className="pb-2 pr-3">Projects</th>
                <th className="pb-2 pr-3">Impact</th>
                <th className="pb-2 pr-3">State</th>
                <th className="pb-2 pr-3">Created</th>
                <th className="pb-2">Result</th>
              </tr>
            </thead>
            <tbody>
              {proposals.map((p) => (
                <tr key={p.id} className="border-b border-gray-700/50">
                  <td className="py-2 pr-3 text-gray-500 font-mono text-xs">{p.id.slice(0, 8)}</td>
                  <td className="py-2 pr-3 text-gray-300 max-w-[200px] truncate">{p.task}</td>
                  <td className="py-2 pr-3 text-gray-400 text-xs">{p.scope_projects.join(', ')}</td>
                  <td className="py-2 pr-3"><ImpactBadge impact={p.scope_impact} /></td>
                  <td className="py-2 pr-3"><StateBadge state={p.state} /></td>
                  <td className="py-2 pr-3 text-gray-500 text-xs whitespace-nowrap">
                    {p.created_at ? new Date(p.created_at).toLocaleString() : '-'}
                  </td>
                  <td className="py-2 text-gray-500 text-xs max-w-[150px] truncate">
                    {p.result_summary || '-'}
                  </td>
                </tr>
              ))}
              {proposals.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-gray-500">
                    No proposals found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Detection results */}
      <div className="space-y-3">
        <h3 className="text-sm font-medium text-gray-300">Detection Results</h3>
        {detections.length === 0 ? (
          <p className="text-sm text-gray-500">No issues detected</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {detections.map((d, i) => (
              <DetectionCard key={i} detection={d} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  color,
  isText = false,
}: {
  label: string;
  value: number | string;
  color: string;
  isText?: boolean;
}) {
  const borderColors: Record<string, string> = {
    red: 'border-red-800',
    yellow: 'border-yellow-800',
    blue: 'border-blue-800',
  };
  const textColors: Record<string, string> = {
    red: 'text-red-400',
    yellow: 'text-yellow-400',
    blue: 'text-blue-400',
  };
  return (
    <div className={`bg-gray-800 border ${borderColors[color] || 'border-gray-700'} rounded-lg p-4`}>
      <p className="text-xs text-gray-500">{label}</p>
      <p className={`mt-1 ${isText ? 'text-sm' : 'text-2xl font-semibold'} ${textColors[color] || 'text-gray-200'}`}>
        {value}
      </p>
    </div>
  );
}

function StateBadge({ state }: { state: string }) {
  const colors: Record<string, string> = {
    pending: 'bg-yellow-900/50 text-yellow-400 border-yellow-800',
    approved: 'bg-blue-900/50 text-blue-400 border-blue-800',
    executing: 'bg-purple-900/50 text-purple-400 border-purple-800',
    completed: 'bg-green-900/50 text-green-400 border-green-800',
    failed: 'bg-red-900/50 text-red-400 border-red-800',
    denied: 'bg-gray-700 text-gray-400 border-gray-600',
    expired: 'bg-gray-700 text-gray-500 border-gray-600',
  };
  const cls = colors[state] || 'bg-gray-700 text-gray-400 border-gray-600';
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full border ${cls}`}>{state}</span>
  );
}

function ImpactBadge({ impact }: { impact: string }) {
  const colors: Record<string, string> = {
    low: 'bg-blue-900/50 text-blue-400 border-blue-800',
    medium: 'bg-yellow-900/50 text-yellow-400 border-yellow-800',
    high: 'bg-red-900/50 text-red-400 border-red-800',
  };
  const cls = colors[impact] || 'bg-gray-700 text-gray-400 border-gray-600';
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full border ${cls}`}>{impact}</span>
  );
}

function DetectionCard({ detection }: { detection: OverlordDetection }) {
  const severityColors: Record<string, string> = {
    low: 'border-l-blue-500',
    medium: 'border-l-yellow-500',
    high: 'border-l-red-500',
  };
  const borderCls = severityColors[detection.severity] || 'border-l-gray-500';

  return (
    <div className={`bg-gray-800 border border-gray-700 border-l-4 ${borderCls} rounded-lg p-4 space-y-2`}>
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-500">{detection.detector}</span>
        <span className="text-xs px-2 py-0.5 rounded-full bg-gray-700 text-gray-300 border border-gray-600">
          {detection.project}
        </span>
      </div>
      <p className="text-sm text-gray-300">{detection.description}</p>
      <p className="text-xs text-gray-500">
        Suggested: <span className="text-gray-400">{detection.proposed_action}</span>
      </p>
    </div>
  );
}
