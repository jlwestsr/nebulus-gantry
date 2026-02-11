import { useState, useEffect, useRef, useCallback } from 'react';
import { documentApi } from '../services/api';
import type { Collection, DocumentScope } from '../types/api';

interface DocumentScopeSelectorProps {
  conversationId: number;
  onScopeChange: (scope: DocumentScope[] | null) => void;
}

export function DocumentScopeSelector({
  conversationId,
  onScopeChange,
}: DocumentScopeSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [collections, setCollections] = useState<Collection[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const dropdownRef = useRef<HTMLDivElement>(null);
  const hasFetched = useRef(false);

  // Close on click outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  // Fetch collections on first open
  const handleOpen = useCallback(async () => {
    if (isOpen) {
      setIsOpen(false);
      return;
    }
    setIsOpen(true);
    if (hasFetched.current) return;
    setIsLoading(true);
    try {
      const data = await documentApi.listCollections();
      setCollections(data);
      hasFetched.current = true;
    } catch {
      // Silently fail — collections are optional
    } finally {
      setIsLoading(false);
    }
  }, [isOpen]);

  // Toggle a collection in the scope
  const toggleCollection = useCallback(
    async (id: number) => {
      const next = new Set(selectedIds);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      setSelectedIds(next);

      const scope: DocumentScope[] | null =
        next.size > 0
          ? Array.from(next).map((cid) => ({ type: 'collection' as const, id: cid }))
          : null;

      try {
        await documentApi.setDocumentScope(conversationId, scope);
        onScopeChange(scope);
      } catch {
        // Revert on failure
        setSelectedIds(selectedIds);
      }
    },
    [conversationId, selectedIds, onScopeChange]
  );

  // Clear all selections
  const clearScope = useCallback(async () => {
    setSelectedIds(new Set());
    try {
      await documentApi.setDocumentScope(conversationId, null);
      onScopeChange(null);
    } catch {
      // Silently fail
    }
    setIsOpen(false);
  }, [conversationId, onScopeChange]);

  const hasScope = selectedIds.size > 0;

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={handleOpen}
        className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs transition-colors ${
          hasScope
            ? 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
            : 'text-gray-400 hover:text-gray-200 hover:bg-gray-700/50'
        }`}
        title="Filter documents for RAG"
      >
        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
          />
        </svg>
        {hasScope ? `${selectedIds.size} collection${selectedIds.size > 1 ? 's' : ''}` : 'Docs'}
      </button>

      {isOpen && (
        <div className="absolute right-0 top-full mt-1 w-56 bg-gray-800 border border-gray-700 rounded-lg shadow-xl z-50 py-1">
          {isLoading ? (
            <div className="px-3 py-2 text-xs text-gray-500">Loading...</div>
          ) : collections.length === 0 ? (
            <div className="px-3 py-2 text-xs text-gray-500">No collections</div>
          ) : (
            <>
              <button
                onClick={clearScope}
                className={`w-full text-left px-3 py-1.5 text-xs hover:bg-gray-700/50 transition-colors ${
                  !hasScope ? 'text-blue-300' : 'text-gray-400'
                }`}
              >
                All documents
              </button>
              <div className="border-t border-gray-700/50 my-0.5" />
              {collections.map((col) => (
                <button
                  key={col.id}
                  onClick={() => toggleCollection(col.id)}
                  className="w-full text-left px-3 py-1.5 text-xs text-gray-300 hover:bg-gray-700/50 transition-colors flex items-center justify-between"
                >
                  <span className="truncate">{col.name}</span>
                  {selectedIds.has(col.id) && (
                    <svg className="w-3.5 h-3.5 text-blue-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  )}
                </button>
              ))}
            </>
          )}
        </div>
      )}
    </div>
  );
}
