import { useState } from 'react';
import type { DispatchEvent } from '../types/api';
import { overlordApi } from '../services/api';

interface NotificationBlockProps {
  event: DispatchEvent;
}

export function NotificationBlock({ event }: NotificationBlockProps) {
  switch (event.type) {
    case 'thinking':
      return <ThinkingBlock content={event.content} />;
    case 'status':
      return <StatusBlock content={event.content} />;
    case 'result':
      return <ResultBlock event={event} />;
    case 'approval_request':
      return <ApprovalBlock event={event} />;
    case 'error':
      return <ErrorBlock content={event.content} />;
    default:
      return null;
  }
}

function ThinkingBlock({ content }: { content: string }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="my-1 mx-2">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1.5 text-[11px] text-gray-500 hover:text-gray-400 transition-colors"
      >
        <svg
          className={`w-3 h-3 transition-transform ${expanded ? 'rotate-90' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
        <span className="inline-flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-gray-500 animate-pulse" />
          {content || 'Thinking...'}
        </span>
      </button>
      {expanded && (
        <div className="mt-1 ml-5 px-2 py-1 bg-gray-800/50 rounded text-[11px] text-gray-400 border-l-2 border-gray-600">
          {content}
        </div>
      )}
    </div>
  );
}

function StatusBlock({ content }: { content: string }) {
  return (
    <div className="my-1 mx-2 px-3 py-1.5 bg-blue-900/20 border border-blue-800/30 rounded text-xs text-blue-300 flex items-center gap-2">
      <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      {content}
    </div>
  );
}

function ResultBlock({ event }: { event: DispatchEvent }) {
  const meta = event.metadata || {};
  return (
    <div className="my-1 mx-2 px-3 py-2 bg-gray-800 border border-gray-700/50 rounded text-xs">
      {event.content && (
        <p className="text-gray-300 mb-1">{event.content}</p>
      )}
      <div className="flex flex-wrap gap-2 text-[10px] text-gray-500">
        {meta.worker && (
          <span className="px-1.5 py-0.5 bg-gray-700/50 rounded">
            Worker: {String(meta.worker)}
          </span>
        )}
        {meta.tokens_used && (
          <span className="px-1.5 py-0.5 bg-gray-700/50 rounded">
            Tokens: {Number(meta.tokens_used).toLocaleString()}
          </span>
        )}
        {meta.status && (
          <span className="px-1.5 py-0.5 bg-gray-700/50 rounded">
            {String(meta.status)}
          </span>
        )}
      </div>
    </div>
  );
}

function ApprovalBlock({ event }: { event: DispatchEvent }) {
  const [resolved, setResolved] = useState<'approved' | 'denied' | null>(null);
  const [loading, setLoading] = useState(false);
  const proposalId = String(event.metadata?.proposal_id || '');

  const handleApprove = async () => {
    if (!proposalId) return;
    setLoading(true);
    try {
      await overlordApi.approveProposal(proposalId);
      setResolved('approved');
    } catch {
      // Approval failed — keep buttons visible
    } finally {
      setLoading(false);
    }
  };

  const handleDeny = async () => {
    if (!proposalId) return;
    setLoading(true);
    try {
      await overlordApi.denyProposal(proposalId);
      setResolved('denied');
    } catch {
      // Denial failed — keep buttons visible
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="my-1 mx-2 px-3 py-2 bg-yellow-900/20 border border-yellow-700/40 rounded">
      <div className="flex items-start gap-2">
        <svg className="w-4 h-4 text-yellow-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
        </svg>
        <div className="flex-1">
          <p className="text-xs text-yellow-300 mb-2">{event.content}</p>
          {resolved ? (
            <span className={`text-[10px] font-medium ${
              resolved === 'approved' ? 'text-green-400' : 'text-red-400'
            }`}>
              {resolved === 'approved' ? 'Approved' : 'Denied'}
            </span>
          ) : (
            <div className="flex gap-2">
              <button
                onClick={handleApprove}
                disabled={loading}
                className="px-2.5 py-1 bg-green-700/50 hover:bg-green-600/50 border border-green-600/40 text-green-300 text-[10px] font-medium rounded transition-colors disabled:opacity-50"
                aria-label="Approve proposal"
              >
                Approve
              </button>
              <button
                onClick={handleDeny}
                disabled={loading}
                className="px-2.5 py-1 bg-red-700/50 hover:bg-red-600/50 border border-red-600/40 text-red-300 text-[10px] font-medium rounded transition-colors disabled:opacity-50"
                aria-label="Deny proposal"
              >
                Deny
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ErrorBlock({ content }: { content: string }) {
  return (
    <div className="my-1 mx-2 px-3 py-1.5 bg-red-900/20 border border-red-800/30 rounded text-xs text-red-300 flex items-center gap-2">
      <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      {content}
    </div>
  );
}
