import { useEffect, useState } from 'react';
import { useOrchestratorStore } from '../stores/orchestratorStore';
import type { Job, StepResult } from '../api/orchestratorApi';

function StatusBadge({ status }: { status: Job['status'] | StepResult['status'] }) {
  const colors = {
    pending: 'bg-gray-700 text-gray-300',
    waiting: 'bg-yellow-900 text-yellow-300',
    running: 'bg-blue-900 text-blue-300',
    completed: 'bg-green-900 text-green-300',
    failed: 'bg-red-900 text-red-300',
    cancelled: 'bg-gray-700 text-gray-400',
    skipped: 'bg-gray-700 text-gray-500',
  };

  return (
    <span className={`px-2 py-1 rounded text-xs font-medium ${colors[status] || colors.pending}`}>
      {status}
    </span>
  );
}

function StepItem({ name, result }: { name: string; result: StepResult }) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="border border-gray-700 rounded-lg p-3">
      <div
        className="flex items-center justify-between cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-3 flex-1">
          <StatusBadge status={result.status} />
          <span className="text-sm text-gray-200 font-medium">{name}</span>
        </div>
        <div className="flex items-center gap-3 text-xs text-gray-500">
          {result.duration_seconds !== undefined && (
            <span>{result.duration_seconds.toFixed(1)}s</span>
          )}
          {result.model_used && <span className="text-gray-400">{result.model_used}</span>}
          <svg
            className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </div>

      {isExpanded && (
        <div className="mt-3 pt-3 border-t border-gray-700">
          {result.output && (
            <div className="mb-2">
              <div className="text-xs text-gray-500 mb-1">Output:</div>
              <pre className="text-xs text-gray-300 bg-gray-800 p-2 rounded overflow-x-auto whitespace-pre-wrap">
                {result.output}
              </pre>
            </div>
          )}
          {result.error && (
            <div>
              <div className="text-xs text-red-400 mb-1">Error:</div>
              <pre className="text-xs text-red-300 bg-red-950 p-2 rounded overflow-x-auto whitespace-pre-wrap">
                {result.error}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function JobDetail({ job }: { job: Job }) {
  const { pollJob, cancelJob } = useOrchestratorStore();
  const isActive = job.status === 'running' || job.status === 'pending';

  useEffect(() => {
    if (!isActive) return;

    const interval = setInterval(() => {
      pollJob(job.id);
    }, 2000);

    return () => clearInterval(interval);
  }, [job.id, isActive, pollJob]);

  const handleCancel = async () => {
    if (window.confirm('Cancel this job?')) {
      try {
        await cancelJob(job.id);
      } catch {
        // Error already set in store
      }
    }
  };

  return (
    <div className="space-y-4">
      {/* Job Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h3 className="text-lg font-medium text-gray-200">{job.workflow}</h3>
            <StatusBadge status={job.status} />
          </div>
          <p className="text-sm text-gray-400 mt-1">{job.inputs.goal}</p>
          <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
            <span>Created: {new Date(job.created_at).toLocaleString()}</span>
            {job.completed_at && (
              <span>Completed: {new Date(job.completed_at).toLocaleString()}</span>
            )}
          </div>
        </div>
        {isActive && (
          <button
            onClick={handleCancel}
            className="px-3 py-1.5 text-sm text-red-300 border border-red-800 rounded-lg hover:bg-red-950 transition-colors"
          >
            Cancel
          </button>
        )}
      </div>

      {/* Global Error */}
      {job.error && (
        <div className="bg-red-950 border border-red-800 rounded-lg p-3">
          <div className="text-sm text-red-300 font-medium mb-1">Job Error</div>
          <pre className="text-xs text-red-200 whitespace-pre-wrap">{job.error}</pre>
        </div>
      )}

      {/* Steps */}
      <div className="space-y-2">
        <h4 className="text-sm font-medium text-gray-400 uppercase tracking-wider">Steps</h4>
        {Object.entries(job.steps).map(([name, result]) => (
          <StepItem key={name} name={name} result={result} />
        ))}
      </div>
    </div>
  );
}

export function OrchestratorPanel() {
  const {
    jobs,
    activeJobId,
    templates,
    isLoading,
    error,
    loadTemplates,
    submitJob,
    loadJobs,
    setActiveJob,
  } = useOrchestratorStore();

  const [selectedTemplate, setSelectedTemplate] = useState('');
  const [goal, setGoal] = useState('');

  useEffect(() => {
    loadTemplates();
    loadJobs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTemplate || !goal.trim()) return;

    try {
      await submitJob(selectedTemplate, goal);
      setGoal('');
    } catch {
      // Error already set in store
    }
  };

  const activeJob = jobs.find((j) => j.id === activeJobId);

  return (
    <div className="min-h-screen bg-gray-900 flex">
      {/* Left Panel: Job Submission & List */}
      <div className="w-96 border-r border-gray-700 flex flex-col">
        {/* Submit Form */}
        <div className="p-4 border-b border-gray-700">
          <h2 className="text-lg font-semibold text-gray-200 mb-4">New Job</h2>
          <form onSubmit={handleSubmit} className="space-y-3">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Template</label>
              <select
                value={selectedTemplate}
                onChange={(e) => setSelectedTemplate(e.target.value)}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                disabled={isLoading}
              >
                <option value="">Select template...</option>
                {templates.map((t) => (
                  <option key={t.name} value={t.name}>
                    {t.name}
                  </option>
                ))}
              </select>
              {selectedTemplate && (
                <p className="mt-1 text-xs text-gray-500">
                  {templates.find((t) => t.name === selectedTemplate)?.description}
                </p>
              )}
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-1">Goal</label>
              <textarea
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
                placeholder="Describe what you want to build or fix..."
                rows={3}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 resize-none"
                disabled={isLoading}
              />
            </div>

            <button
              type="submit"
              disabled={!selectedTemplate || !goal.trim() || isLoading}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500/50"
            >
              {isLoading ? 'Submitting...' : 'Submit Job'}
            </button>
          </form>

          {error && (
            <div className="mt-3 p-2 bg-red-950 border border-red-800 rounded-lg">
              <p className="text-xs text-red-300">{error}</p>
            </div>
          )}
        </div>

        {/* Jobs List */}
        <div className="flex-1 overflow-y-auto p-4">
          <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">
            Recent Jobs
          </h3>
          {jobs.length === 0 ? (
            <p className="text-sm text-gray-500 text-center py-8">No jobs yet</p>
          ) : (
            <div className="space-y-2">
              {jobs.map((job) => (
                <div
                  key={job.id}
                  onClick={() => setActiveJob(job.id)}
                  className={`p-3 rounded-lg cursor-pointer transition-colors ${
                    activeJobId === job.id
                      ? 'bg-gray-700 border border-gray-600'
                      : 'bg-gray-800 border border-gray-700 hover:bg-gray-750'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-gray-200">{job.workflow}</span>
                    <StatusBadge status={job.status} />
                  </div>
                  <p className="text-xs text-gray-400 line-clamp-2">{job.inputs.goal}</p>
                  <div className="text-xs text-gray-500 mt-1">
                    {new Date(job.created_at).toLocaleString()}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Right Panel: Job Detail */}
      <div className="flex-1 p-6 overflow-y-auto">
        {activeJob ? (
          <JobDetail job={activeJob} />
        ) : (
          <div className="flex items-center justify-center h-full">
            <p className="text-gray-500">Select a job to view details</p>
          </div>
        )}
      </div>
    </div>
  );
}
