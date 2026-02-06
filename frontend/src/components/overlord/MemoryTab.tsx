import { useState, useEffect, useCallback, type FormEvent } from 'react';
import { overlordApi } from '../../services/api';
import type { OverlordMemoryEntry } from '../../types/api';

const CATEGORIES = ['pattern', 'preference', 'relation', 'decision', 'failure', 'release'] as const;

export function MemoryTab() {
  const [entries, setEntries] = useState<OverlordMemoryEntry[]>([]);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [filterCategory, setFilterCategory] = useState<string>('');
  const [filterProject, setFilterProject] = useState<string>('');

  // Add modal
  const [showAddModal, setShowAddModal] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await overlordApi.listMemory({
        query: searchQuery || undefined,
        category: filterCategory || undefined,
        project: filterProject || undefined,
      });
      setEntries(data.entries);
      setCount(data.count);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, [searchQuery, filterCategory, filterProject]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handleDelete = async (id: string) => {
    try {
      await overlordApi.deleteMemory(id);
      setEntries((prev) => prev.filter((e) => e.id !== id));
      setCount((prev) => prev - 1);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <div className="space-y-4">
      {/* Search + filters */}
      <div className="space-y-3">
        <div className="flex gap-3">
          <div className="flex-1 relative">
            <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="text"
              placeholder="Search memories..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && refresh()}
              className="w-full pl-10 pr-3 py-2 text-sm text-gray-200 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 placeholder-gray-500"
            />
          </div>
          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Add
          </button>
        </div>

        {/* Filter row */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs text-gray-500">Category:</span>
          <button
            onClick={() => setFilterCategory('')}
            className={`text-xs px-2 py-1 rounded-full transition-colors ${
              filterCategory === '' ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
            }`}
          >
            All
          </button>
          {CATEGORIES.map((cat) => (
            <button
              key={cat}
              onClick={() => setFilterCategory(filterCategory === cat ? '' : cat)}
              className={`text-xs px-2 py-1 rounded-full transition-colors ${
                filterCategory === cat ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-800 bg-red-900/20 p-3">
          <p className="text-red-400 text-sm">{error}</p>
        </div>
      )}

      {/* Result count */}
      <p className="text-xs text-gray-500">{count} memor{count !== 1 ? 'ies' : 'y'}</p>

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-8">
          <div className="text-gray-400 text-sm">Loading memories...</div>
        </div>
      )}

      {/* Memory entries */}
      {!loading && (
        <div className="space-y-3">
          {entries.map((entry) => (
            <MemoryCard key={entry.id} entry={entry} onDelete={handleDelete} />
          ))}
          {entries.length === 0 && (
            <p className="text-sm text-gray-500 text-center py-8">No memories found</p>
          )}
        </div>
      )}

      {/* Add modal */}
      {showAddModal && (
        <AddMemoryModal
          onClose={() => setShowAddModal(false)}
          onSuccess={() => {
            setShowAddModal(false);
            refresh();
          }}
        />
      )}
    </div>
  );
}

function MemoryCard({
  entry,
  onDelete,
}: {
  entry: OverlordMemoryEntry;
  onDelete: (id: string) => void;
}) {
  const categoryColors: Record<string, string> = {
    pattern: 'bg-purple-900/50 text-purple-400 border-purple-800',
    preference: 'bg-blue-900/50 text-blue-400 border-blue-800',
    relation: 'bg-cyan-900/50 text-cyan-400 border-cyan-800',
    decision: 'bg-green-900/50 text-green-400 border-green-800',
    failure: 'bg-red-900/50 text-red-400 border-red-800',
    release: 'bg-yellow-900/50 text-yellow-400 border-yellow-800',
  };
  const cls = categoryColors[entry.category] || 'bg-gray-700 text-gray-400 border-gray-600';

  const relativeTime = getRelativeTime(entry.timestamp);

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={`text-xs px-2 py-0.5 rounded-full border ${cls}`}>
            {entry.category}
          </span>
          {entry.project && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-gray-700 text-gray-300 border border-gray-600">
              {entry.project}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">{relativeTime}</span>
          <button
            onClick={() => onDelete(entry.id)}
            className="p-1 text-gray-500 hover:text-red-400 transition-colors rounded"
            title="Delete memory"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      </div>
      <p className="text-sm text-gray-300">{entry.content}</p>
    </div>
  );
}

function AddMemoryModal({
  onClose,
  onSuccess,
}: {
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [category, setCategory] = useState('decision');
  const [content, setContent] = useState('');
  const [project, setProject] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await overlordApi.addMemory({
        category,
        content,
        project: project || undefined,
      });
      onSuccess();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-md bg-gray-800 border border-gray-700 rounded-xl shadow-2xl p-6">
        <div className="flex items-center justify-between mb-5">
          <h4 className="text-lg font-medium text-gray-200">Add Memory</h4>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-200 transition-colors">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {error && (
          <div className="rounded-lg border border-red-800 bg-red-900/20 p-3 mb-4">
            <p className="text-red-400 text-sm">{error}</p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Category</label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full px-3 py-2 text-sm text-gray-200 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {CATEGORIES.map((cat) => (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Content</label>
            <textarea
              required
              rows={3}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              className="w-full px-3 py-2 text-sm text-gray-200 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 placeholder-gray-500"
              placeholder="Observation, decision, or pattern..."
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Project (optional)</label>
            <input
              type="text"
              value={project}
              onChange={(e) => setProject(e.target.value)}
              className="w-full px-3 py-2 text-sm text-gray-200 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 placeholder-gray-500"
              placeholder="e.g. nebulus-core"
            />
          </div>

          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-300 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting || !content.trim()}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {submitting ? 'Saving...' : 'Save Memory'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function getRelativeTime(timestamp: string): string {
  try {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 1) return 'just now';
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHrs = Math.floor(diffMin / 60);
    if (diffHrs < 24) return `${diffHrs}h ago`;
    const diffDays = Math.floor(diffHrs / 24);
    if (diffDays < 30) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  } catch {
    return timestamp;
  }
}
