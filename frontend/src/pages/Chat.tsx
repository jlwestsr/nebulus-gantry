import { useEffect, useState, useCallback, useRef } from 'react';
import { Sidebar } from '../components/Sidebar';
import { MessageList } from '../components/MessageList';
import { MessageInput } from '../components/MessageInput';
import { PersonaSelector } from '../components/PersonaSelector';
import { DocumentScopeSelector } from '../components/DocumentScopeSelector';
import { SituationMap } from '../components/SituationMap';
import { NotificationBlock } from '../components/NotificationBlock';
import { ExportActions } from '../components/ExportActions';
import { useChatStore } from '../stores/chatStore';
import { useAuthStore } from '../stores/authStore';
import { useDispatchStore } from '../stores/dispatchStore';
import { chatApi, dispatchApi } from '../services/api';
import type { Message, MessageMeta, Conversation, Persona, DocumentScope } from '../types/api';

const OVERLORD_ROUTING_ENABLED = false; // Direct LLM mode for appliance


export function Chat() {
  const { currentConversationId, updateConversationTitle, createConversation } = useChatStore();
  const { sidebarOpen, toggleSidebar, addEvent, clearEvents, events } = useDispatchStore();
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentConversation, setCurrentConversation] = useState<Conversation | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pendingMessageRef = useRef<{ content: string; model?: string } | null>(null);

  // Clear dispatch events when conversation changes
  useEffect(() => {
    clearEvents();
  }, [currentConversationId, clearEvents]);

  // Fetch messages when conversation changes
  useEffect(() => {
    if (!currentConversationId) {
      setMessages([]);
      setCurrentConversation(null);
      return;
    }

    const fetchMessages = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const data = await chatApi.getConversation(currentConversationId);
        setMessages(data.messages);
        setCurrentConversation(data.conversation);
      } catch (err) {
        setError((err as Error).message);
        setMessages([]);
        setCurrentConversation(null);
      } finally {
        setIsLoading(false);
      }
    };

    fetchMessages();
  }, [currentConversationId]);

  // Handle document scope change
  const handleScopeChange = useCallback((_scope: DocumentScope[] | null) => {
    // Scope is persisted server-side; no local state needed
  }, []);

  // Handle persona change
  const handlePersonaChange = useCallback((persona: Persona | null) => {
    setCurrentConversation((prev) =>
      prev
        ? {
            ...prev,
            persona_id: persona?.id ?? null,
            persona_name: persona?.name ?? null,
          }
        : null
    );
  }, []);

  // Handle sending a message with streaming response
  const handleSendMessage = useCallback(
    async (content: string, model?: string) => {
      if (!currentConversationId || isSending) return;

      setIsSending(true);
      setError(null);
      clearEvents();

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
        let fullContent = '';
        let streamMeta: MessageMeta | undefined;

        if (OVERLORD_ROUTING_ENABLED) {
          // Dispatch mode: route through Overlord
          const history = messages.map((m) => ({ role: m.role, content: m.content }));
          for await (const event of dispatchApi.sendMessage({
            user_message: content,
            conversation_history: history,
            role: 'default',
          })) {
            if (event.type === 'content') {
              fullContent += event.content;
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === tempAssistantMessageId
                    ? { ...msg, content: fullContent }
                    : msg
                )
              );
            } else if (event.type === 'error') {
              setError(event.content);
              addEvent(event);
            } else {
              // Route non-content events to dispatch store for sidebar + inline rendering
              addEvent(event);
            }
          }
        } else {
          // Direct LLM streaming via SSE
          for await (const event of chatApi.sendMessage(
            currentConversationId,
            content,
            model
          )) {
            if (event.type === 'content') {
              fullContent += event.content;
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === tempAssistantMessageId
                    ? { ...msg, content: fullContent }
                    : msg
                )
              );
            } else if (event.type === 'done') {
              streamMeta = event.meta;
            }
          }
        }

        // Apply final content and metadata from done event
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === tempAssistantMessageId
              ? { ...msg, content: fullContent, meta: streamMeta }
              : msg
          )
        );

        // Update conversation title if this was the first message
        // The backend should have auto-generated a title
        if (messages.length === 0) {
          // Fetch the updated conversation to get the new title
          try {
            const data = await chatApi.getConversation(currentConversationId);
            if (data.conversation.title !== 'New Thread') {
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
    [currentConversationId, isSending, messages.length, updateConversationTitle, clearEvents, addEvent]
  );

  // Auto-send pending message when a conversation is created from the welcome screen
  useEffect(() => {
    if (currentConversationId && pendingMessageRef.current) {
      const { content, model } = pendingMessageRef.current;
      pendingMessageRef.current = null;
      handleSendMessage(content, model);
    }
  }, [currentConversationId, handleSendMessage]);

  // Handle sending from the welcome screen — create conversation first, then send
  const handleWelcomeSend = useCallback(
    async (content: string, model?: string) => {
      pendingMessageRef.current = { content, model };
      try {
        await createConversation();
      } catch {
        pendingMessageRef.current = null;
      }
    },
    [createConversation]
  );

  // Filter non-content events for inline rendering
  const notificationEvents = events.filter(
    (e) => e.type !== 'content'
  );

  return (
    <div className="flex h-[calc(100vh-57px)]">
      {/* Sidebar with conversations */}
      <Sidebar />

      {/* Chat area */}
      <div className="flex-1 flex flex-col bg-gray-800 min-w-0">
        {currentConversationId ? (
          <>
            {/* Chat Header with Persona Selector and Situation Map toggle */}
            <div className="flex items-center justify-between px-4 py-2 border-b border-gray-700/50">
              <div className="text-sm text-gray-400 truncate">
                {currentConversation?.title || 'New Thread'}
              </div>
              <div className="flex items-center gap-2">
                <DocumentScopeSelector
                  conversationId={currentConversationId}
                  onScopeChange={handleScopeChange}
                />
                <PersonaSelector
                  conversationId={currentConversationId}
                  currentPersonaId={currentConversation?.persona_id ?? null}
                  currentPersonaName={currentConversation?.persona_name ?? null}
                  onPersonaChange={handlePersonaChange}
                />
                <ExportActions
                  conversationId={currentConversationId}
                  disabled={isSending || isLoading}
                />
                {!sidebarOpen && (
                  <button
                    onClick={toggleSidebar}
                    className="p-1.5 text-gray-500 hover:text-gray-300 transition-colors rounded"
                    aria-label="Open situation map"
                    title="Situation Map"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
                    </svg>
                  </button>
                )}
              </div>
            </div>

            {/* Error display */}
            {error && (
              <div className="px-4 py-2 bg-red-900/50 text-red-200 text-sm text-center border-b border-red-800/30">
                {error}
              </div>
            )}

            {/* Inline notification blocks */}
            {notificationEvents.length > 0 && (
              <div className="border-b border-gray-700/30">
                {notificationEvents.map((event, idx) => (
                  <NotificationBlock key={idx} event={event} />
                ))}
              </div>
            )}

            {/* Messages */}
            <MessageList
              messages={messages}
              isLoading={isLoading || (isSending && messages[messages.length - 1]?.content === '')}
            />

            {/* Message Input */}
            <MessageInput
              onSend={handleSendMessage}
              disabled={isSending}
              placeholder="Message Moto..."
            />
          </>
        ) : (
          /* Welcome screen with personalized greeting */
          <WelcomeScreen onSend={handleWelcomeSend} isSending={isSending} />
        )}
      </div>

      {/* Situation Map sidebar */}
      {sidebarOpen && <SituationMap />}
    </div>
  );
}

function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  return 'Good evening';
}

const QUICK_PROMPTS = [
  { label: 'Explain some code', prompt: 'Help me understand this code and suggest improvements for readability and performance.' },
  { label: 'Brainstorm ideas', prompt: 'Help me brainstorm creative solutions for a technical challenge I\'m working on.' },
  { label: 'Write documentation', prompt: 'Help me write clear, concise documentation for my project.' },
  { label: 'Debug an issue', prompt: 'I\'m running into a bug. Help me trace the issue and find the root cause.' },
];

function WelcomeScreen({ onSend, isSending }: { onSend: (content: string, model?: string) => void; isSending: boolean }) {
  const user = useAuthStore((state) => state.user);
  const firstName = user?.display_name?.split(' ')[0] || 'there';

  return (
    <div className="flex-1 flex flex-col">
      <div className="flex-1 flex items-center justify-center px-4">
        <div className="text-center max-w-2xl w-full">
          <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-gradient-to-br from-cyan-500/20 to-violet-500/20 border border-cyan-500/30 flex items-center justify-center">
            <span className="text-3xl">🏍️</span>
          </div>
          <h2 className="text-xl sm:text-2xl font-semibold text-gray-200 mb-2">
            {getGreeting()}, {firstName}.
          </h2>
          <p className="text-gray-400 text-sm sm:text-base max-w-md mx-auto mb-8">
            Your data stays on this device. Ask me anything.
          </p>

          {/* Quick-start suggestions */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-lg mx-auto">
            {QUICK_PROMPTS.map((item) => (
              <button
                key={item.label}
                onClick={() => onSend(item.prompt)}
                disabled={isSending}
                className="text-left px-4 py-3 rounded-xl bg-gray-700/50 border border-gray-600/50 hover:border-cyan-500/40 hover:bg-gray-700 text-sm text-gray-300 hover:text-gray-100 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Welcome screen input */}
      <MessageInput
        onSend={onSend}
        disabled={isSending}
        placeholder="Message Moto..."
      />
    </div>
  );
}
