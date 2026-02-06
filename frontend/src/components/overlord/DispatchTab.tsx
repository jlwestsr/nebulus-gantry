import { useState, useEffect, useCallback } from 'react';
import { overlordApi } from '../../services/api';
import type {
  OverlordPlan,
  OverlordDispatchResult,
  OverlordProposal,
} from '../../types/api';

export function DispatchTab() {
  const [taskInput, setTaskInput] = useState('');
  const [plan, setPlan] = useState<OverlordPlan | null>(null);
  const [result, setResult] = useState<OverlordDispatchResult | null>(null);
  const [proposals, setProposals] = useState<OverlordProposal[]>([]);
  const [parsing, setParsing] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadProposals = useCallback(async () => {
    try {
      const data = await overlordApi.listProposals('pending');
      setProposals(data.proposals);
    } catch {
      // Silently fail for proposal list
    }
  }, []);

  useEffect(() => {
    loadProposals();
  }, [loadProposals]);

  const handleParse = async () => {
    if (!taskInput.trim()) return;
    setParsing(true);
    setError(null);
    setPlan(null);
    setResult(null);
    try {
      const data = await overlordApi.parseTask(taskInput);
      setPlan(data);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setParsing(false);
    }
  };

  const handleExecute = async () => {
    if (!taskInput.trim()) return;
    setExecuting(true);
    setError(null);
    setResult(null);
    try {
      const data = await overlordApi.executeTask(taskInput, true);
      setResult(data);
      loadProposals();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setExecuting(false);
    }
  };

  const handleApprove = async (id: string) => {
    try {
      await overlordApi.approveProposal(id);
      loadProposals();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const handleDeny = async (id: string) => {
    try {
      await overlordApi.denyProposal(id);
      loadProposals();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <div className="space-y-6">
      {/* Task input */}
      <div className="space-y-3">
        <label className="block text-sm font-medium text-gray-300">Task</label>
        <textarea
          rows={3}
          value={taskInput}
          onChange={(e) => setTaskInput(e.target.value)}
          placeholder='e.g. "run tests in Core", "merge develop to main in Prime"'
          className="w-full px-3 py-2 text-sm text-gray-200 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 placeholder-gray-500 resize-none"
        />
        <div className="flex gap-2">
          <button
            onClick={handleParse}
            disabled={parsing || !taskInput.trim()}
            className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-gray-200 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {parsing ? 'Parsing...' : 'Parse Plan'}
          </button>
          <button
            onClick={handleExecute}
            disabled={executing || !taskInput.trim()}
            className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            {executing ? 'Executing...' : 'Execute'}
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-800 bg-red-900/20 p-3">
          <p className="text-red-400 text-sm">{error}</p>
        </div>
      )}

      {/* Plan preview */}
      {plan && (
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-gray-200">Dispatch Plan</h3>
            {plan.requires_approval && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-yellow-900/50 text-yellow-400 border border-yellow-800">
                Requires Approval
              </span>
            )}
          </div>

          {/* Scope summary */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <MetricCard label="Projects" value={plan.scope.projects.join(', ') || 'none'} />
            <MetricCard label="Impact" value={plan.scope.estimated_impact} />
            <MetricCard label="Duration" value={`${plan.estimated_duration}s`} />
            <MetricCard label="Remote" value={plan.scope.affects_remote ? 'Yes' : 'No'} />
          </div>

          {/* Steps table */}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 border-b border-gray-700">
                  <th className="pb-2 pr-4">#</th>
                  <th className="pb-2 pr-4">Action</th>
                  <th className="pb-2 pr-4">Project</th>
                  <th className="pb-2 pr-4">Tier</th>
                  <th className="pb-2">Timeout</th>
                </tr>
              </thead>
              <tbody>
                {plan.steps.map((step, i) => (
                  <tr key={step.id} className="border-b border-gray-700/50">
                    <td className="py-2 pr-4 text-gray-500">{i + 1}</td>
                    <td className="py-2 pr-4 text-gray-300">{step.action}</td>
                    <td className="py-2 pr-4 text-gray-400">{step.project}</td>
                    <td className="py-2 pr-4 text-gray-500">{step.model_tier || '-'}</td>
                    <td className="py-2 text-gray-500">{step.timeout}s</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Execution result */}
      {result && (
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 space-y-3">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-medium text-gray-200">Execution Result</h3>
            <StatusBadge status={result.status} />
          </div>
          {result.reason && (
            <p className="text-sm text-gray-400">{result.reason}</p>
          )}
          <div className="space-y-2">
            {result.steps.map((step) => (
              <div key={step.step_id} className="flex items-center gap-3 text-sm">
                {step.success ? (
                  <svg className="w-4 h-4 text-green-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  <svg className="w-4 h-4 text-red-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                )}
                <span className="text-gray-300">{step.step_id}</span>
                <span className="text-gray-500">{step.duration.toFixed(1)}s</span>
                {step.error && <span className="text-red-400 text-xs">{step.error}</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Pending proposals */}
      {proposals.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-gray-300">Pending Proposals</h3>
          {proposals.map((p) => (
            <div key={p.id} className="bg-gray-800 border border-gray-700 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <p className="text-sm text-gray-200">{p.task}</p>
                  <div className="flex items-center gap-2 text-xs text-gray-500">
                    <span>{p.scope_projects.join(', ')}</span>
                    <span>|</span>
                    <ImpactBadge impact={p.scope_impact} />
                    <span>|</span>
                    <span>{new Date(p.created_at).toLocaleString()}</span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleApprove(p.id)}
                    className="px-3 py-1.5 text-xs font-medium text-green-400 bg-green-900/30 hover:bg-green-900/50 border border-green-800 rounded-lg transition-colors"
                  >
                    Approve
                  </button>
                  <button
                    onClick={() => handleDeny(p.id)}
                    className="px-3 py-1.5 text-xs font-medium text-red-400 bg-red-900/30 hover:bg-red-900/50 border border-red-800 rounded-lg transition-colors"
                  >
                    Deny
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-gray-700/50 rounded-lg p-2.5">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="text-sm text-gray-200 mt-0.5 truncate">{value}</p>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    success: 'bg-green-900/50 text-green-400 border-green-800',
    failed: 'bg-red-900/50 text-red-400 border-red-800',
    cancelled: 'bg-gray-700 text-gray-400 border-gray-600',
  };
  const cls = colors[status] || 'bg-gray-700 text-gray-400 border-gray-600';
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full border ${cls}`}>{status}</span>
  );
}

function ImpactBadge({ impact }: { impact: string }) {
  const colors: Record<string, string> = {
    low: 'text-blue-400',
    medium: 'text-yellow-400',
    high: 'text-red-400',
  };
  return <span className={colors[impact] || 'text-gray-400'}>{impact}</span>;
}
