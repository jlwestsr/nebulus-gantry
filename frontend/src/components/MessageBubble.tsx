import type { Message } from '../types/api';

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';

  // Format timestamp for hover display
  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div
      className={`flex ${isUser ? 'justify-end' : 'justify-start'} group`}
    >
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 ${
          isUser
            ? 'bg-blue-600 text-white'
            : 'bg-gray-700 text-gray-100'
        }`}
      >
        {/* Message content */}
        <div className="whitespace-pre-wrap break-words text-sm leading-relaxed">
          {message.content}
        </div>

        {/* Timestamp - shows on hover */}
        <div
          className={`mt-1 text-xs opacity-0 group-hover:opacity-100 transition-opacity ${
            isUser ? 'text-blue-200' : 'text-gray-400'
          }`}
        >
          {formatTime(message.created_at)}
        </div>
      </div>
    </div>
  );
}
