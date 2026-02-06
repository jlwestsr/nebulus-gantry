import { useState, useRef, useEffect, useCallback } from 'react';
import type { KeyboardEvent, ChangeEvent } from 'react';
import { modelsApi } from '../services/api';
import type { Model } from '../types/api';
import { useChatStore } from '../stores/chatStore';

interface MessageInputProps {
  onSend: (content: string, model?: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function MessageInput({
  onSend,
  disabled = false,
  placeholder = 'Message Nebulus...',
}: MessageInputProps) {
  const [content, setContent] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [models, setModels] = useState<Model[]>([]);
  const [selectedModel, setSelectedModel] = useState<string | null>(null);
  const [showModelPicker, setShowModelPicker] = useState(false);
  const modelPickerRef = useRef<HTMLDivElement>(null);

  const { isModelSwitching, targetModel, setModelSwitching } = useChatStore();

  const fetchModels = useCallback(async () => {
    try {
      const data = await modelsApi.list();
      setModels(data.models);
      // Auto-select the active model, or fall back to the first available
      if (!selectedModel && data.models.length > 0) {
        const active = data.models.find((m) => m.active);
        setSelectedModel(active ? active.id : data.models[0].id);
      }
    } catch {
      // Non-critical
    }
  }, [selectedModel]);

  useEffect(() => {
    fetchModels();
  }, [fetchModels]);

  // Close model picker when clicking outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (modelPickerRef.current && !modelPickerRef.current.contains(e.target as Node)) {
        setShowModelPicker(false);
      }
    }
    if (showModelPicker) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [showModelPicker]);

  const activeModel = models.find((m) => m.id === selectedModel);
  const modelLabel = activeModel?.name || 'No model';

  // Auto-resize textarea based on content
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      // Reset height to auto to get the correct scrollHeight
      textarea.style.height = 'auto';
      // Set height to scrollHeight, with min and max constraints
      const newHeight = Math.min(Math.max(textarea.scrollHeight, 44), 200);
      textarea.style.height = `${newHeight}px`;
    }
  }, [content]);

  const handleChange = (e: ChangeEvent<HTMLTextAreaElement>) => {
    setContent(e.target.value);
  };

  const handleSubmit = async () => {
    const trimmed = content.trim();
    if (trimmed && !disabled) {
      // Check if model needs switching
      const activeModel = models.find((m) => m.active);
      if (selectedModel && activeModel && selectedModel !== activeModel.id) {
        setModelSwitching(true, selectedModel);
      }

      onSend(trimmed, selectedModel || undefined);
      setContent('');
      // Reset textarea height after clearing
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }

      // Refresh models after a short delay to reflect the switch
      if (isModelSwitching) {
        setTimeout(() => {
          fetchModels();
          setModelSwitching(false);
        }, 1000);
      }
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Submit on Enter, allow Shift+Enter for newline
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const canSubmit = content.trim().length > 0 && !disabled;

  return (
    <div className="p-3 sm:p-4 border-t border-gray-700">
      <div className="max-w-3xl mx-auto">
        {/* Model selector */}
        <div className="relative mb-2" ref={modelPickerRef}>
          <button
            onClick={() => setShowModelPicker(!showModelPicker)}
            className="flex items-center gap-1.5 px-2.5 py-1 text-xs text-gray-400 hover:text-gray-200 rounded-md hover:bg-gray-700/50 transition-colors"
            title="Select model"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
            <span className="font-mono truncate max-w-[200px]">{modelLabel}</span>
            <svg className={`w-3 h-3 transition-transform ${showModelPicker ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          {showModelPicker && models.length > 0 && (
            <div className="absolute bottom-full left-0 mb-1 w-72 bg-gray-800 border border-gray-600 rounded-lg shadow-xl z-50 py-1 max-h-48 overflow-y-auto">
              {models.map((m) => (
                <button
                  key={m.id}
                  onClick={() => {
                    setSelectedModel(m.id);
                    setShowModelPicker(false);
                  }}
                  className={`w-full text-left px-3 py-2 text-sm transition-colors ${
                    m.id === selectedModel
                      ? 'bg-blue-500/15 text-blue-400'
                      : 'text-gray-300 hover:bg-gray-700'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs truncate">{m.name}</span>
                    {m.active && (
                      <span className="text-[10px] text-green-400 bg-green-500/10 px-1.5 py-0.5 rounded">loaded</span>
                    )}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
        <div className="flex items-end gap-2 sm:gap-3 bg-gray-700 rounded-xl px-3 sm:px-4 py-2.5 sm:py-3 focus-within:ring-2 focus-within:ring-blue-500/50 transition-shadow duration-200">
          <textarea
            ref={textareaRef}
            value={content}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled}
            rows={1}
            className="flex-1 bg-transparent text-gray-100 placeholder-gray-400 outline-none text-sm resize-none leading-relaxed min-h-[22px] max-h-[200px] disabled:text-gray-500 disabled:cursor-not-allowed"
            style={{ height: 'auto' }}
          />
          <button
            onClick={handleSubmit}
            disabled={!canSubmit}
            className={`p-2 rounded-lg transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500/50 ${
              canSubmit
                ? 'text-white bg-blue-600 hover:bg-blue-500 active:scale-95'
                : 'text-gray-500 cursor-not-allowed'
            }`}
            aria-label="Send message"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 10l7-7m0 0l7 7m-7-7v18"
              />
            </svg>
          </button>
        </div>
        {isModelSwitching && targetModel && (
          <div className="mt-2 text-center text-xs text-yellow-500/80 flex items-center justify-center gap-2">
            <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span>Switching to {targetModel}... (this may take 5-30 seconds)</span>
          </div>
        )}
        {disabled && !isModelSwitching && (
          <div className="mt-2 text-center text-xs text-gray-500">
            Generating response...
          </div>
        )}
      </div>
    </div>
  );
}
