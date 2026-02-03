import { useState, useEffect, useRef, useCallback } from 'react';
import { adminApi } from '../../services/api';

const SERVICES = [
  { value: 'gantry-api', label: 'Gantry API' },
  { value: 'gantry-ui', label: 'Gantry UI' },
  { value: 'chromadb', label: 'ChromaDB' },
  { value: 'tabby', label: 'TabbyAPI' },
];

const MAX_LOG_LINES = 1000;

type ConnectionStatus = 'connecting' | 'connected' | 'disconnected';

export function LogsTab() {
  const [selectedService, setSelectedService] = useState(SERVICES[0].value);
  const [lines, setLines] = useState<string[]>([]);
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const [paused, setPaused] = useState(false);

  const scrollRef = useRef<HTMLDivElement>(null);
  const esRef = useRef<EventSource | null>(null);
  const userScrolledUpRef = useRef(false);

  // Determine if the user has scrolled away from the bottom
  const handleScroll = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 30;
    userScrolledUpRef.current = !atBottom;
  }, []);

  // Scroll to bottom if appropriate
  const scrollToBottom = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    if (!paused && !userScrolledUpRef.current) {
      el.scrollTop = el.scrollHeight;
    }
  }, [paused]);

  // Connect to SSE for the selected service
  useEffect(() => {
    // Close any previous connection
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }

    setStatus('connecting');
    setLines([]);
    setPaused(false);
    userScrolledUpRef.current = false;

    const es = adminApi.streamLogs(selectedService);
    esRef.current = es;

    es.onopen = () => {
      setStatus('connected');
    };

    es.onmessage = (event: MessageEvent) => {
      setLines((prev) => {
        const updated = [...prev, event.data];
        if (updated.length > MAX_LOG_LINES) {
          return updated.slice(updated.length - MAX_LOG_LINES);
        }
        return updated;
      });
    };

    es.onerror = () => {
      // EventSource will try to reconnect automatically for non-fatal errors,
      // but if the readyState is CLOSED, it won't reconnect.
      if (es.readyState === EventSource.CLOSED) {
        setStatus('disconnected');
      } else {
        setStatus('connecting');
      }
    };

    return () => {
      es.close();
      esRef.current = null;
    };
  }, [selectedService]);

  // Auto-scroll when new lines arrive
  useEffect(() => {
    scrollToBottom();
  }, [lines, scrollToBottom]);

  const handleClear = useCallback(() => {
    setLines([]);
  }, []);

  const handleTogglePause = useCallback(() => {
    setPaused((prev) => {
      const next = !prev;
      // When resuming, snap to bottom
      if (!next) {
        userScrolledUpRef.current = false;
        requestAnimationFrame(() => {
          const el = scrollRef.current;
          if (el) {
            el.scrollTop = el.scrollHeight;
          }
        });
      }
      return next;
    });
  }, []);

  const statusConfig: Record<
    ConnectionStatus,
    { color: string; label: string }
  > = {
    connected: { color: 'bg-green-500', label: 'Connected' },
    connecting: { color: 'bg-yellow-500 animate-pulse', label: 'Connecting...' },
    disconnected: { color: 'bg-red-500', label: 'Disconnected' },
  };

  const currentStatus = statusConfig[status];
  const currentServiceLabel = SERVICES.find(
    (s) => s.value === selectedService
  )?.label;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-medium text-gray-200">Service Logs</h3>
          <p className="text-sm text-gray-400 mt-1">
            View live logs from Nebulus services
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={selectedService}
            onChange={(e) => setSelectedService(e.target.value)}
            className="px-3 py-1.5 text-sm text-gray-300 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            {SERVICES.map((service) => (
              <option key={service.value} value={service.value}>
                {service.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="rounded-lg border border-gray-700 bg-gray-900/50 overflow-hidden">
        {/* Toolbar */}
        <div className="flex items-center justify-between px-4 py-2 border-b border-gray-700 bg-gray-800/50">
          <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">
            {currentServiceLabel} Logs
          </span>
          <div className="flex items-center gap-3">
            <span className="inline-flex items-center gap-1.5 text-xs text-gray-400">
              <span
                className={`w-1.5 h-1.5 rounded-full ${currentStatus.color}`}
              />
              {currentStatus.label}
            </span>
            <button
              onClick={handleTogglePause}
              className="px-2.5 py-1 text-xs text-gray-300 bg-gray-700 border border-gray-600 rounded hover:bg-gray-600 transition-colors"
            >
              {paused ? 'Resume' : 'Pause'}
            </button>
            <button
              onClick={handleClear}
              className="px-2.5 py-1 text-xs text-gray-300 bg-gray-700 border border-gray-600 rounded hover:bg-gray-600 transition-colors"
            >
              Clear
            </button>
          </div>
        </div>

        {/* Log viewer */}
        <div
          ref={scrollRef}
          onScroll={handleScroll}
          className="p-4 min-h-[400px] max-h-[600px] overflow-y-auto font-mono text-xs"
        >
          {lines.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-80 text-gray-500">
              <svg
                className="w-12 h-12 mb-4 text-gray-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
              <p className="text-sm font-sans">
                {status === 'connected'
                  ? 'Waiting for log output...'
                  : status === 'connecting'
                    ? 'Connecting to log stream...'
                    : 'Not connected'}
              </p>
              <p className="text-xs mt-1 font-sans text-gray-600">
                Logs from {currentServiceLabel} will appear here
              </p>
            </div>
          ) : (
            <div className="space-y-px">
              {lines.map((line, i) => (
                <div key={i} className="text-gray-300 whitespace-pre-wrap break-all leading-5">
                  {line}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer status bar */}
        {lines.length > 0 && (
          <div className="flex items-center justify-between px-4 py-1.5 border-t border-gray-700 bg-gray-800/50">
            <span className="text-xs text-gray-500">
              {lines.length} line{lines.length !== 1 ? 's' : ''}
              {lines.length >= MAX_LOG_LINES ? ' (buffer full, oldest lines trimmed)' : ''}
            </span>
            {paused && (
              <span className="text-xs text-yellow-500">
                Auto-scroll paused
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
