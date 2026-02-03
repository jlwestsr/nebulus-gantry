import { Sidebar } from '../components/Sidebar';
import { useChatStore } from '../stores/chatStore';

export function Chat() {
  const { currentConversationId } = useChatStore();

  return (
    <div className="flex h-[calc(100vh-57px)]">
      {/* Sidebar with conversations */}
      <Sidebar />

      {/* Chat area */}
      <div className="flex-1 flex flex-col items-center justify-center bg-gray-50">
        {currentConversationId ? (
          <div className="text-center">
            <h2 className="text-xl font-semibold text-gray-700">
              Conversation #{currentConversationId}
            </h2>
            <p className="mt-2 text-gray-500">
              Chat messages will appear here
            </p>
          </div>
        ) : (
          <div className="text-center">
            <h2 className="text-2xl font-semibold text-gray-700">
              Welcome to Nebulus Gantry
            </h2>
            <p className="mt-2 text-gray-500">
              Start a new conversation or select an existing one
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
