import { useEffect, useMemo, useState, useCallback } from 'react';
import { useChatStore } from '../stores/chatStore';
import { useUIStore } from '../stores/uiStore';
import { chatApi } from '../services/api';
import type { Conversation, SearchResult } from '../types/api';

// Group conversations by date category, with Pinned at top
function groupConversationsByDate(conversations: Conversation[]) {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 24 * 60 * 60 * 1000);
  const lastWeek = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
  const lastMonth = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);

  const groups: { [key: string]: Conversation[] } = {
    Pinned: [],
    Today: [],
    Yesterday: [],
    'Previous 7 Days': [],
    'Previous 30 Days': [],
    Older: [],
  };

  conversations.forEach((conv) => {
    // Pinned conversations go to the Pinned group
    if (conv.pinned) {
      groups['Pinned'].push(conv);
      return;
    }

    const convDate = new Date(conv.updated_at || conv.created_at);

    if (convDate >= today) {
      groups['Today'].push(conv);
    } else if (convDate >= yesterday) {
      groups['Yesterday'].push(conv);
    } else if (convDate >= lastWeek) {
      groups['Previous 7 Days'].push(conv);
    } else if (convDate >= lastMonth) {
      groups['Previous 30 Days'].push(conv);
    } else {
      groups['Older'].push(conv);
    }
  });

  // Return only non-empty groups in the correct order
  const order = ['Pinned', 'Today', 'Yesterday', 'Previous 7 Days', 'Previous 30 Days', 'Older'];
  return order
    .filter((key) => groups[key].length > 0)
    .map((key) => [key, groups[key]] as [string, Conversation[]]);
}

interface ConversationItemProps {
  conversation: Conversation;
  isActive: boolean;
  onSelect: () => void;
  onDelete: () => void;
  onPin: () => void;
  onExport: (format: 'json' | 'pdf') => void;
}

function ConversationItem({
  conversation,
  isActive,
  onSelect,
  onDelete,
  onPin,
  onExport,
}: ConversationItemProps) {
  const [showExportMenu, setShowExportMenu] = useState(false);

  return (
    <div
      className={`group flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer transition-colors duration-200 ${
        isActive
          ? 'bg-gray-700 text-white'
          : 'text-gray-300 hover:bg-gray-800 hover:text-white'
      }`}
      onClick={onSelect}
    >
      {/* Chat icon */}
      <svg
        className="w-4 h-4 flex-shrink-0 text-gray-500"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
        />
      </svg>

      {/* Title */}
      <span className="flex-1 truncate text-sm">
        {conversation.title || 'New conversation'}
      </span>

      {/* Pin button - shows on hover or when pinned */}
      <button
        className={`p-1 rounded hover:bg-gray-600 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500/50 ${
          conversation.pinned
            ? 'opacity-100 text-yellow-400'
            : 'opacity-0 group-hover:opacity-100 text-gray-400 hover:text-yellow-400'
        }`}
        onClick={(e) => {
          e.stopPropagation();
          onPin();
        }}
        title={conversation.pinned ? 'Unpin conversation' : 'Pin conversation'}
      >
        <svg
          className="w-4 h-4"
          fill={conversation.pinned ? 'currentColor' : 'none'}
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z"
          />
        </svg>
      </button>

      {/* Export dropdown */}
      <div className="relative">
        <button
          className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-gray-600 transition-all duration-200 focus:outline-none focus:opacity-100 focus:ring-2 focus:ring-blue-500/50"
          onClick={(e) => {
            e.stopPropagation();
            setShowExportMenu(!showExportMenu);
          }}
          title="Export conversation"
        >
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
            />
          </svg>
        </button>
        {showExportMenu && (
          <div
            className="absolute right-0 top-8 z-50 w-36 bg-gray-800 border border-gray-700 rounded-lg shadow-lg py-1"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              className="w-full px-3 py-2 text-left text-sm text-gray-300 hover:bg-gray-700 hover:text-white"
              onClick={() => {
                onExport('json');
                setShowExportMenu(false);
              }}
            >
              Export as JSON
            </button>
            <button
              className="w-full px-3 py-2 text-left text-sm text-gray-300 hover:bg-gray-700 hover:text-white"
              onClick={() => {
                onExport('pdf');
                setShowExportMenu(false);
              }}
            >
              Export as PDF
            </button>
          </div>
        )}
      </div>

      {/* Delete button - shows on hover */}
      <button
        className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-gray-600 transition-all duration-200 focus:outline-none focus:opacity-100 focus:ring-2 focus:ring-blue-500/50"
        onClick={(e) => {
          e.stopPropagation();
          onDelete();
        }}
        title="Delete conversation"
      >
        <svg
          className="w-4 h-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
          />
        </svg>
      </button>
    </div>
  );
}

interface SearchResultItemProps {
  result: SearchResult;
  onSelect: () => void;
}

function SearchResultItem({ result, onSelect }: SearchResultItemProps) {
  return (
    <div
      className="px-3 py-2 rounded-lg cursor-pointer transition-colors duration-200 text-gray-300 hover:bg-gray-800 hover:text-white"
      onClick={onSelect}
    >
      <div className="text-sm font-medium truncate">{result.conversation_title}</div>
      <div className="text-xs text-gray-500 mt-1 line-clamp-2">
        <span className={result.role === 'assistant' ? 'text-blue-400' : 'text-green-400'}>
          {result.role === 'assistant' ? 'AI: ' : 'You: '}
        </span>
        {result.message_snippet}
      </div>
    </div>
  );
}

export function Sidebar() {
  const {
    conversations,
    currentConversationId,
    isLoading,
    fetchConversations,
    createConversation,
    selectConversation,
    deleteConversation,
    pinConversation,
    searchQuery,
    searchResults,
    isSearching,
    setSearchQuery,
    performSearch,
    clearSearch,
  } = useChatStore();

  const { isSidebarOpen, closeSidebar } = useUIStore();

  // Local state for the input value (for debouncing)
  const [inputValue, setInputValue] = useState('');

  // Fetch conversations on mount
  useEffect(() => {
    fetchConversations();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Debounced search effect
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearchQuery(inputValue);
      if (inputValue.trim()) {
        performSearch(inputValue);
      } else {
        clearSearch();
      }
    }, 300);

    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inputValue]);

  // Group conversations by date
  const groupedConversations = useMemo(
    () => groupConversationsByDate(conversations),
    [conversations]
  );

  const handleNewChat = async () => {
    try {
      await createConversation();
      closeSidebar();
      clearSearch();
      setInputValue('');
    } catch {
      // Error is already set in store
    }
  };

  const handleSelect = useCallback((id: number) => {
    selectConversation(id);
    closeSidebar();
    clearSearch();
    setInputValue('');
  }, [selectConversation, closeSidebar, clearSearch]);

  const handleDelete = async (id: number) => {
    // Simple confirmation before delete
    if (window.confirm('Delete this conversation?')) {
      try {
        await deleteConversation(id);
      } catch {
        // Error is already set in store
      }
    }
  };

  const handlePin = async (id: number) => {
    try {
      await pinConversation(id);
    } catch {
      // Error is already set in store
    }
  };

  const handleClearSearch = () => {
    setInputValue('');
    clearSearch();
  };

  const showSearchResults = searchQuery.trim().length > 0;

  return (
    <aside
      className={`
        w-64 h-full bg-gray-900 flex flex-col border-r border-gray-700/50
        fixed md:relative z-50 md:z-auto
        transition-transform duration-300 ease-in-out
        ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
      `}
    >
      {/* New Chat Button */}
      <div className="p-3">
        <button
          onClick={handleNewChat}
          disabled={isLoading}
          className="w-full flex items-center justify-center gap-2 py-2.5 px-4 border border-gray-600 text-gray-200 rounded-lg hover:bg-gray-800 transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-blue-500/50"
        >
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 4v16m8-8H4"
            />
          </svg>
          <span className="text-sm font-medium">New Chat</span>
        </button>
      </div>

      {/* Search Input */}
      <div className="px-3 pb-3">
        <div className="relative">
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
          <input
            type="text"
            placeholder="Search conversations..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            className="w-full pl-9 pr-8 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-transparent"
          />
          {inputValue && (
            <button
              onClick={handleClearSearch}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-gray-500 hover:text-gray-300"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* Conversation List or Search Results */}
      <div className="flex-1 overflow-y-auto px-2 pb-4 scrollbar-thin">
        {showSearchResults ? (
          // Search Results View
          <div>
            <h3 className="px-3 py-2 text-xs font-medium text-gray-500 uppercase tracking-wider">
              {isSearching ? 'Searching...' : `${searchResults.length} Results`}
            </h3>
            {isSearching ? (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-gray-400"></div>
              </div>
            ) : searchResults.length === 0 ? (
              <div className="text-center py-8 text-sm text-gray-500">
                No matches found
              </div>
            ) : (
              <div className="space-y-1">
                {searchResults.map((result, idx) => (
                  <SearchResultItem
                    key={`${result.conversation_id}-${idx}`}
                    result={result}
                    onSelect={() => handleSelect(result.conversation_id)}
                  />
                ))}
              </div>
            )}
          </div>
        ) : (
          // Normal Conversation List View
          <>
            {isLoading && conversations.length === 0 ? (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-gray-400"></div>
              </div>
            ) : groupedConversations.length === 0 ? (
              <div className="text-center py-8 text-sm text-gray-500">
                No conversations yet
              </div>
            ) : (
              groupedConversations.map(([group, convs]) => (
                <div key={group} className="mb-4">
                  <h3 className="px-3 py-2 text-xs font-medium text-gray-500 uppercase tracking-wider flex items-center gap-1">
                    {group === 'Pinned' && (
                      <svg className="w-3 h-3 text-yellow-400" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
                      </svg>
                    )}
                    {group}
                  </h3>
                  <div className="space-y-0.5">
                    {convs.map((conv) => (
                      <ConversationItem
                        key={conv.id}
                        conversation={conv}
                        isActive={currentConversationId === conv.id}
                        onSelect={() => handleSelect(conv.id)}
                        onDelete={() => handleDelete(conv.id)}
                        onPin={() => handlePin(conv.id)}
                        onExport={(format) => chatApi.exportConversation(conv.id, format)}
                      />
                    ))}
                  </div>
                </div>
              ))
            )}
          </>
        )}
      </div>
    </aside>
  );
}
