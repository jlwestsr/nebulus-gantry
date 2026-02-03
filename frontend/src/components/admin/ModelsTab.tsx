import { useEffect, useState, useCallback } from 'react';
import { adminApi } from '../../services/api';
import type { Model } from '../../types/api';

export function ModelsTab() {
  const [models, setModels] = useState<Model[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [switchingModel, setSwitchingModel] = useState<string | null>(null);

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

  const handleSwitch = async (modelId: string) => {
    setSwitchingModel(modelId);
    try {
      await adminApi.switchModel(modelId);
      await fetchModels();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSwitchingModel(null);
    }
  };

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
          <h3 className="text-lg font-medium text-gray-200">Available Models</h3>
          <p className="text-sm text-gray-400 mt-1">
            Switch between available language models
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

      <div className="grid gap-3">
        {models.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            No models available
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
                    onClick={() => handleSwitch(model.id)}
                    disabled={switchingModel === model.id}
                    className="px-3 py-1.5 text-xs font-medium text-blue-400 bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/30 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {switchingModel === model.id ? 'Switching...' : 'Switch'}
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
