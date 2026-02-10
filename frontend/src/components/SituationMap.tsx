import { useEffect, useRef, useState, useCallback } from 'react';
import { useDispatchStore } from '../stores/dispatchStore';

const POLL_INTERVAL = 5000;

const STATUS_COLORS: Record<string, string> = {
  dispatched: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
  in_review: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
  completed: 'bg-green-500/20 text-green-300 border-green-500/30',
  failed: 'bg-red-500/20 text-red-300 border-red-500/30',
  active: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
};

const WORKER_COLORS: Record<string, { bg: string; text: string; label: string }> = {
  claude: { bg: 'bg-violet-500', text: 'text-violet-300', label: 'C' },
  gemini: { bg: 'bg-blue-500', text: 'text-blue-300', label: 'G' },
  local: { bg: 'bg-emerald-500', text: 'text-emerald-300', label: 'L' },
};

function getBudgetColor(pct: number): string {
  if (pct > 80) return 'bg-red-500';
  if (pct > 60) return 'bg-yellow-500';
  return 'bg-emerald-500';
}

function getBudgetTrackColor(pct: number): string {
  if (pct > 80) return 'bg-red-500/20';
  if (pct > 60) return 'bg-yellow-500/20';
  return 'bg-emerald-500/20';
}

export function SituationMap() {
  const {
    activeDispatches,
    budget,
    fetchActiveDispatches,
    fetchBudget,
    haltAll,
    toggleSidebar,
  } = useDispatchStore();

  const [showHaltConfirm, setShowHaltConfirm] = useState(false);
  const [haltResult, setHaltResult] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Poll for active dispatches and budget
  useEffect(() => {
    fetchActiveDispatches();
    fetchBudget();

    pollRef.current = setInterval(() => {
      fetchActiveDispatches();
      fetchBudget();
    }, POLL_INTERVAL);

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [fetchActiveDispatches, fetchBudget]);

  const handleHalt = useCallback(async () => {
    try {
      const result = await haltAll();
      setHaltResult(result.message);
      setShowHaltConfirm(false);
      setTimeout(() => setHaltResult(null), 5000);
    } catch (err) {
      setHaltResult(`Halt failed: ${(err as Error).message}`);
      setShowHaltConfirm(false);
      setTimeout(() => setHaltResult(null), 5000);
    }
  }, [haltAll]);

  return (
    <div className="w-72 flex-shrink-0 bg-gray-900 border-l border-gray-700/50 flex flex-col h-full max-md:absolute max-md:right-0 max-md:top-0 max-md:bottom-0 max-md:z-50 max-md:shadow-2xl">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-700/50">
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
          Situation Map
        </h3>
        <button
          onClick={toggleSidebar}
          className="p-1 text-gray-500 hover:text-gray-300 transition-colors"
          aria-label="Close situation map"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5l7 7-7 7M5 5l7 7-7 7" />
          </svg>
        </button>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto p-3 space-y-4">
        {/* Active Agents */}
        <section>
          <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
            Active Agents
          </h4>
          {activeDispatches.length === 0 ? (
            <div className="text-center py-4">
              <svg className="w-8 h-8 mx-auto text-gray-600 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
              </svg>
              <p className="text-xs text-gray-500">No active dispatches</p>
            </div>
          ) : (
            <div className="space-y-2">
              {activeDispatches.map((d) => {
                const worker = WORKER_COLORS[d.worker || 'local'] || WORKER_COLORS.local;
                const statusCls = STATUS_COLORS[d.status] || STATUS_COLORS.active;
                return (
                  <div
                    key={d.id}
                    className="bg-gray-800 rounded-md p-2 border border-gray-700/50"
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <span
                        className={`w-5 h-5 rounded-full ${worker.bg} flex items-center justify-center text-[10px] font-bold text-white flex-shrink-0`}
                      >
                        {worker.label}
                      </span>
                      <span className="text-xs text-gray-300 truncate flex-1">
                        {d.title}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 ml-7">
                      <span className="text-[10px] text-gray-500 truncate">
                        {d.project}
                      </span>
                      <span
                        className={`text-[10px] px-1.5 py-0.5 rounded border ${statusCls}`}
                      >
                        {d.status}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>

        {/* Daily Budget */}
        <section>
          <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
            Daily Budget
          </h4>
          {budget ? (
            <div className="bg-gray-800 rounded-md p-2 border border-gray-700/50 space-y-2">
              {/* Token bar */}
              <div>
                <div className="flex justify-between text-[10px] text-gray-400 mb-1">
                  <span>Tokens</span>
                  <span>
                    {budget.tokens_used_today.toLocaleString()} / {budget.token_ceiling.toLocaleString()}
                  </span>
                </div>
                <div className={`h-2 rounded-full ${getBudgetTrackColor(budget.usage_pct)}`}>
                  <div
                    className={`h-full rounded-full transition-all ${getBudgetColor(budget.usage_pct)}`}
                    style={{ width: `${Math.min(budget.usage_pct, 100)}%` }}
                  />
                </div>
              </div>
              {/* Cost */}
              <div className="flex justify-between text-[10px] text-gray-400">
                <span>Cost</span>
                <span>
                  ${budget.cost_usd_today.toFixed(2)} / ${budget.cost_ceiling_usd.toFixed(2)}
                </span>
              </div>
              {/* Percentage */}
              <div className="text-center">
                <span className={`text-sm font-semibold ${
                  budget.usage_pct > 80 ? 'text-red-400' :
                  budget.usage_pct > 60 ? 'text-yellow-400' :
                  'text-emerald-400'
                }`}>
                  {budget.usage_pct.toFixed(1)}%
                </span>
                <span className="text-[10px] text-gray-500 ml-1">used</span>
              </div>
            </div>
          ) : (
            <div className="bg-gray-800 rounded-md p-2 border border-gray-700/50">
              <p className="text-[10px] text-gray-500 text-center">Budget data unavailable</p>
            </div>
          )}
        </section>
      </div>

      {/* Halt Button — fixed at bottom */}
      <div className="p-3 border-t border-gray-700/50">
        {haltResult && (
          <div className="mb-2 px-2 py-1 bg-gray-800 rounded text-[10px] text-gray-300 text-center">
            {haltResult}
          </div>
        )}
        {showHaltConfirm ? (
          <div className="space-y-2">
            <p className="text-xs text-red-300 text-center">
              Cancel all dispatches and stop daemon?
            </p>
            <div className="flex gap-2">
              <button
                onClick={handleHalt}
                className="flex-1 px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white text-xs font-medium rounded transition-colors"
                aria-label="Confirm halt all"
              >
                Confirm
              </button>
              <button
                onClick={() => setShowHaltConfirm(false)}
                className="flex-1 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-gray-300 text-xs font-medium rounded transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <button
            onClick={() => setShowHaltConfirm(true)}
            className="w-full px-3 py-1.5 bg-red-900/50 hover:bg-red-800/50 border border-red-700/50 text-red-300 text-xs font-medium rounded transition-colors"
            aria-label="Halt all dispatches"
          >
            Halt All
          </button>
        )}
      </div>
    </div>
  );
}
