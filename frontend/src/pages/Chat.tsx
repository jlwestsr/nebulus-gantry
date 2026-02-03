import { useEffect, useState } from 'react';
import { Sidebar } from '../components/Sidebar';
import { MessageList } from '../components/MessageList';
import { useChatStore } from '../stores/chatStore';
import { chatApi } from '../services/api';
import type { Message } from '../types/api';

export function Chat() {
  const { currentConversationId } = useChatStore();
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch messages when conversation changes
  useEffect(() => {
    if (!currentConversationId) {
      setMessages([]);
      return;
    }

    const fetchMessages = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const data = await chatApi.getConversation(currentConversationId);
        setMessages(data.messages);
      } catch (err) {
        setError((err as Error).message);
        setMessages([]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchMessages();
  }, [currentConversationId]);

  return (
    <div className="flex h-[calc(100vh-57px)]">
      {/* Sidebar with conversations */}
      <Sidebar />

      {/* Chat area */}
      <div className="flex-1 flex flex-col bg-gray-800">
        {currentConversationId ? (
          <>
            {/* Error display */}
            {error && (
              <div className="px-4 py-2 bg-red-900/50 text-red-200 text-sm text-center">
                {error}
              </div>
            )}

            {/* Messages */}
            <MessageList messages={messages} isLoading={isLoading} />

            {/* Input area placeholder - will be implemented in Task 19 */}
            <div className="p-4 border-t border-gray-700">
              <div className="max-w-3xl mx-auto">
                <div className="flex items-center gap-3 bg-gray-700 rounded-xl px-4 py-3">
                  <input
                    type="text"
                    placeholder="Message input coming in next task..."
                    disabled
                    className="flex-1 bg-transparent text-gray-400 placeholder-gray-500 outline-none text-sm cursor-not-allowed"
                  />
                  <button
                    disabled
                    className="p-2 text-gray-500 cursor-not-allowed"
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
                        d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                      />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          </>
        ) : (
          /* Welcome screen when no conversation selected */
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-gray-700 flex items-center justify-center">
                <svg
                  className="w-8 h-8 text-gray-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                  />
                </svg>
              </div>
              <h2 className="text-2xl font-semibold text-gray-200 mb-2">
                Welcome to Nebulus Gantry
              </h2>
              <p className="text-gray-400 max-w-md">
                Start a new conversation or select an existing one from the sidebar
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
