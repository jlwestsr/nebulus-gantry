import { useState, useEffect, useCallback } from 'react';
import { overlordApi } from '../../services/api';
import type {
  OverlordDashboard,
  OverlordProjectStatus,
  OverlordGraph,
} from '../../types/api';

export function EcosystemTab() {
  const [dashboard, setDashboard] = useState<OverlordDashboard | null>(null);
  const [graph, setGraph] = useState<OverlordGraph | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [dashData, graphData] = await Promise.all([
        overlordApi.getDashboard(),
        overlordApi.getGraph(),
      ]);
      setDashboard(dashData);
      setGraph(graphData);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-gray-400">Scanning ecosystem...</div>
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

  if (!dashboard) return null;

  return (
    <div className="space-y-6">
      {/* Top row: Daemon status + Refresh */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <DaemonBadge
            running={dashboard.daemon.running}
            pid={dashboard.daemon.pid}
          />
          <span className="text-sm text-gray-400">
            {dashboard.projects.length} project{dashboard.projects.length !== 1 ? 's' : ''}
          </span>
        </div>
        <button
          onClick={refresh}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-300 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Refresh
        </button>
      </div>

      {/* Project cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {dashboard.projects.map((project) => (
          <ProjectCard key={project.name} project={project} />
        ))}
      </div>

      {/* Dependency graph */}
      {graph && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-gray-300">Dependency Graph</h3>
          <pre className="bg-gray-800 border border-gray-700 rounded-lg p-4 text-sm text-gray-300 overflow-x-auto font-mono">
            {graph.ascii || 'No dependencies configured'}
          </pre>
        </div>
      )}

      {/* Config summary */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Autonomy levels */}
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-300 mb-3">Autonomy Levels</h3>
          <div className="space-y-2">
            {Object.entries(dashboard.config.autonomy_levels).map(([name, level]) => (
              <div key={name} className="flex items-center justify-between">
                <span className="text-sm text-gray-400">{name}</span>
                <AutonomyBadge level={level} />
              </div>
            ))}
            {Object.keys(dashboard.config.autonomy_levels).length === 0 && (
              <p className="text-sm text-gray-500">No autonomy levels configured</p>
            )}
          </div>
        </div>

        {/* Scheduled tasks */}
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-300 mb-3">Scheduled Tasks</h3>
          <div className="space-y-2">
            {dashboard.config.scheduled_tasks.map((task, i) => (
              <div key={i} className="flex items-center justify-between">
                <span className="text-sm text-gray-400">{task.name as string}</span>
                <div className="flex items-center gap-2">
                  <code className="text-xs text-gray-500 bg-gray-700 px-1.5 py-0.5 rounded">
                    {task.cron as string}
                  </code>
                  <span className={`w-2 h-2 rounded-full ${task.enabled ? 'bg-green-500' : 'bg-gray-600'}`} />
                </div>
              </div>
            ))}
            {dashboard.config.scheduled_tasks.length === 0 && (
              <p className="text-sm text-gray-500">No scheduled tasks</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function DaemonBadge({ running, pid }: { running: boolean; pid: number | null }) {
  return (
    <div className="flex items-center gap-2">
      <span className={`w-2.5 h-2.5 rounded-full ${running ? 'bg-green-500' : 'bg-red-500'}`} />
      <span className="text-sm font-medium text-gray-200">
        Daemon {running ? 'Running' : 'Stopped'}
      </span>
      {pid && (
        <span className="text-xs text-gray-500">PID {pid}</span>
      )}
    </div>
  );
}

function ProjectCard({ project }: { project: OverlordProjectStatus }) {
  const issueCount = project.issues.length;
  const isClean = project.git.clean;

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-100">{project.name}</h3>
        {project.role && (
          <span className="text-xs px-2 py-0.5 rounded-full bg-blue-900/50 text-blue-400 border border-blue-800">
            {project.role}
          </span>
        )}
      </div>

      {/* Git info */}
      <div className="space-y-1.5">
        <div className="flex items-center gap-2">
          <svg className="w-3.5 h-3.5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
          </svg>
          <span className="text-sm text-gray-300">{project.git.branch}</span>
          <span className={`w-2 h-2 rounded-full ${isClean ? 'bg-green-500' : 'bg-yellow-500'}`}
            title={isClean ? 'Clean' : 'Dirty'}
          />
        </div>

        {(project.git.ahead > 0 || project.git.behind > 0) && (
          <div className="flex items-center gap-3 text-xs text-gray-500">
            {project.git.ahead > 0 && <span>+{project.git.ahead} ahead</span>}
            {project.git.behind > 0 && <span>-{project.git.behind} behind</span>}
          </div>
        )}
      </div>

      {/* Test health */}
      <div className="flex items-center gap-2">
        {project.tests.has_tests ? (
          <svg className="w-3.5 h-3.5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        ) : (
          <svg className="w-3.5 h-3.5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        )}
        <span className="text-xs text-gray-400">
          {project.tests.has_tests ? 'Tests configured' : 'No tests'}
        </span>
      </div>

      {/* Issues */}
      {issueCount > 0 && (
        <div className="border-t border-gray-700 pt-2">
          <span className="text-xs text-yellow-400">{issueCount} issue{issueCount !== 1 ? 's' : ''}</span>
          <ul className="mt-1 space-y-0.5">
            {project.issues.slice(0, 3).map((issue, i) => (
              <li key={i} className="text-xs text-gray-500 truncate">{issue}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function AutonomyBadge({ level }: { level: string }) {
  const colors: Record<string, string> = {
    cautious: 'bg-yellow-900/50 text-yellow-400 border-yellow-800',
    proactive: 'bg-blue-900/50 text-blue-400 border-blue-800',
    scheduled: 'bg-purple-900/50 text-purple-400 border-purple-800',
  };
  const cls = colors[level] || 'bg-gray-700 text-gray-400 border-gray-600';
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full border ${cls}`}>
      {level}
    </span>
  );
}
