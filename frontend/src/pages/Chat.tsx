import { useEffect, useState, useCallback } from 'react';
import { Sidebar } from '../components/Sidebar';
import { MessageList } from '../components/MessageList';
import { MessageInput } from '../components/MessageInput';
import { useChatStore } from '../stores/chatStore';
import { chatApi } from '../services/api';
import type { Message } from '../types/api';

export function Chat() {
  const { currentConversationId, updateConversationTitle } = useChatStore();
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSending, setIsSending] = useState(false);
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

  // Handle sending a message with streaming response
  const handleSendMessage = useCallback(
    async (content: string) => {
      if (!currentConversationId || isSending) return;

      setIsSending(true);
      setError(null);

      // Create a temporary ID for the user message (will be replaced after refresh)
      const tempUserMessageId = Date.now();
      const tempAssistantMessageId = tempUserMessageId + 1;

      // Add user message immediately to the UI
      const userMessage: Message = {
        id: tempUserMessageId,
        conversation_id: currentConversationId,
        role: 'user',
        content,
        created_at: new Date().toISOString(),
      };

      // Add placeholder assistant message for streaming
      const assistantMessage: Message = {
        id: tempAssistantMessageId,
        conversation_id: currentConversationId,
        role: 'assistant',
        content: '',
        created_at: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, userMessage, assistantMessage]);

      try {
        // Stream the response
        let fullContent = '';
        for await (const chunk of chatApi.sendMessage(
          currentConversationId,
          content
        )) {
          fullContent += chunk;
          // Update the assistant message content as chunks arrive
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === tempAssistantMessageId
                ? { ...msg, content: fullContent }
                : msg
            )
          );
        }

        // Update conversation title if this was the first message
        // The backend should have auto-generated a title
        if (messages.length === 0) {
          // Fetch the updated conversation to get the new title
          try {
            const data = await chatApi.getConversation(currentConversationId);
            if (data.conversation.title !== 'New Conversation') {
              updateConversationTitle(
                currentConversationId,
                data.conversation.title
              );
            }
            // Also refresh messages to get proper IDs
            setMessages(data.messages);
          } catch {
            // Silently fail on title update - not critical
          }
        } else {
          // Refresh messages to get proper IDs from the database
          try {
            const data = await chatApi.getConversation(currentConversationId);
            setMessages(data.messages);
          } catch {
            // Keep the streamed content if refresh fails
          }
        }
      } catch (err) {
        setError((err as Error).message);
        // Remove the placeholder messages on error
        setMessages((prev) =>
          prev.filter(
            (msg) =>
              msg.id !== tempUserMessageId && msg.id !== tempAssistantMessageId
          )
        );
      } finally {
        setIsSending(false);
      }
    },
    [currentConversationId, isSending, messages.length, updateConversationTitle]
  );

  return (
    <div className="flex h-[calc(100vh-57px)]">
      {/* Sidebar with conversations */}
      <Sidebar />

      {/* Chat area */}
      <div className="flex-1 flex flex-col bg-gray-800 min-w-0">
        {currentConversationId ? (
          <>
            {/* Error display */}
            {error && (
              <div className="px-4 py-2 bg-red-900/50 text-red-200 text-sm text-center border-b border-red-800/30">
                {error}
              </div>
            )}

            {/* Messages */}
            <MessageList
              messages={messages}
              isLoading={isLoading || (isSending && messages.length > 0 && messages[messages.length - 1]?.content === '')}
            />

            {/* Message Input */}
            <MessageInput
              onSend={handleSendMessage}
              disabled={isSending}
              placeholder="Message Nebulus..."
            />
          </>
        ) : (
          /* Welcome screen when no conversation selected */
          <div className="flex-1 flex items-center justify-center px-4">
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
              <h2 className="text-xl sm:text-2xl font-semibold text-gray-200 mb-2">
                Welcome to Nebulus Gantry
              </h2>
              <p className="text-gray-400 text-sm sm:text-base max-w-md">
                Start a new conversation or select an existing one from the
                sidebar
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
