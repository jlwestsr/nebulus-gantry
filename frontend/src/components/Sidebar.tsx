import { useEffect, useMemo } from 'react';
import { useChatStore } from '../stores/chatStore';
import { useUIStore } from '../stores/uiStore';
import type { Conversation } from '../types/api';

// Group conversations by date category
function groupConversationsByDate(conversations: Conversation[]) {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 24 * 60 * 60 * 1000);
  const lastWeek = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
  const lastMonth = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);

  const groups: { [key: string]: Conversation[] } = {
    Today: [],
    Yesterday: [],
    'Previous 7 Days': [],
    'Previous 30 Days': [],
    Older: [],
  };

  conversations.forEach((conv) => {
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

  // Return only non-empty groups
  return Object.entries(groups).filter(([, convs]) => convs.length > 0);
}

interface ConversationItemProps {
  conversation: Conversation;
  isActive: boolean;
  onSelect: () => void;
  onDelete: () => void;
}

function ConversationItem({
  conversation,
  isActive,
  onSelect,
  onDelete,
}: ConversationItemProps) {
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

export function Sidebar() {
  const {
    conversations,
    currentConversationId,
    isLoading,
    fetchConversations,
    createConversation,
    selectConversation,
    deleteConversation,
  } = useChatStore();

  const { isSidebarOpen, closeSidebar } = useUIStore();

  // Fetch conversations on mount
  useEffect(() => {
    fetchConversations();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Group conversations by date
  const groupedConversations = useMemo(
    () => groupConversationsByDate(conversations),
    [conversations]
  );

  const handleNewChat = async () => {
    try {
      await createConversation();
      closeSidebar();
    } catch {
      // Error is already set in store
    }
  };

  const handleSelect = (id: number) => {
    selectConversation(id);
    closeSidebar();
  };

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

      {/* Conversation List */}
      <div className="flex-1 overflow-y-auto px-2 pb-4 scrollbar-thin">
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
              <h3 className="px-3 py-2 text-xs font-medium text-gray-500 uppercase tracking-wider">
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
                  />
                ))}
              </div>
            </div>
          ))
        )}
      </div>
    </aside>
  );
}
