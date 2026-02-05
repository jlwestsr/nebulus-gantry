import { useEffect, useState, useCallback } from 'react';
import { adminApi } from '../../services/api';
import type { Model } from '../../types/api';

export function ModelsTab() {
  const [models, setModels] = useState<Model[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionModel, setActionModel] = useState<string | null>(null);

  const fetchModels = useCallback(async () => {
    try {
      setError(null);
      const data = await adminApi.listModels();
      setModels(data.models);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchModels();
  }, [fetchModels]);

  const handleLoad = async (modelId: string) => {
    setActionModel(modelId);
    try {
      await adminApi.switchModel(modelId);
      await fetchModels();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setActionModel(null);
    }
  };

  const handleUnload = async () => {
    setActionModel('__unload__');
    try {
      await adminApi.unloadModel();
      await fetchModels();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setActionModel(null);
    }
  };

  const activeModel = models.find((m) => m.active);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-gray-400">Loading models...</div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-medium text-gray-200">Model Management</h3>
          <p className="text-sm text-gray-400 mt-1">
            Load, switch, and unload language models on the LLM host
          </p>
        </div>
        <button
          onClick={fetchModels}
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

      {/* Active model card */}
      {activeModel && (
        <div className="mb-6 p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-3 h-3 rounded-full bg-blue-400 animate-pulse" />
              <div>
                <div className="text-sm font-medium text-blue-300">Currently Loaded</div>
                <div className="text-base font-mono text-gray-200 mt-0.5">{activeModel.name}</div>
              </div>
            </div>
            <button
              onClick={handleUnload}
              disabled={actionModel === '__unload__'}
              className="px-3 py-1.5 text-xs font-medium text-red-400 bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {actionModel === '__unload__' ? 'Unloading...' : 'Unload'}
            </button>
          </div>
        </div>
      )}

      {/* Model list */}
      <div className="grid gap-3">
        {models.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            No models available. Ensure TabbyAPI is running and has models configured.
          </div>
        ) : (
          models.map((model) => (
            <div
              key={model.id}
              className={`flex items-center justify-between p-4 rounded-lg border transition-colors ${
                model.active
                  ? 'bg-blue-500/10 border-blue-500/30'
                  : 'bg-gray-800/50 border-gray-700 hover:border-gray-600'
              }`}
            >
              <div className="flex items-center gap-3">
                <div
                  className={`w-2.5 h-2.5 rounded-full ${
                    model.active ? 'bg-blue-400' : 'bg-gray-600'
                  }`}
                />
                <div>
                  <div className="text-sm font-medium text-gray-200">
                    {model.name}
                  </div>
                  <div className="text-xs text-gray-500 font-mono mt-0.5">
                    {model.id}
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-3">
                {model.active ? (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-500/20 text-blue-400 border border-blue-500/30">
                    Active
                  </span>
                ) : (
                  <button
                    onClick={() => handleLoad(model.id)}
                    disabled={actionModel === model.id}
                    className="px-3 py-1.5 text-xs font-medium text-blue-400 bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/30 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {actionModel === model.id ? 'Loading...' : 'Load'}
                  </button>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
