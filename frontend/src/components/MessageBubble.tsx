import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
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
        className={`max-w-[85%] sm:max-w-[80%] rounded-2xl px-4 py-3 transition-shadow duration-200 ${
          isUser
            ? 'bg-blue-600 text-white'
            : 'bg-gray-700 text-gray-100'
        }`}
      >
        {/* Message content */}
        {isUser ? (
          <div className="whitespace-pre-wrap break-words text-sm leading-relaxed">
            {message.content}
          </div>
        ) : (
          <div className="prose prose-sm prose-invert max-w-none break-words [&>*:first-child]:mt-0 [&>*:last-child]:mb-0">
            <Markdown
              remarkPlugins={[remarkGfm]}
              components={{
                pre({ children }) {
                  return (
                    <pre className="bg-gray-900 rounded-lg p-3 overflow-x-auto text-sm">
                      {children}
                    </pre>
                  );
                },
                code({ children, className }) {
                  const isBlock = className?.startsWith('language-');
                  if (isBlock) {
                    return <code className={`${className} text-sm`}>{children}</code>;
                  }
                  return (
                    <code className="bg-gray-600 px-1.5 py-0.5 rounded text-sm">
                      {children}
                    </code>
                  );
                },
                a({ href, children }) {
                  return (
                    <a href={href} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">
                      {children}
                    </a>
                  );
                },
              }}
            >
              {message.content}
            </Markdown>
          </div>
        )}

        {/* Timestamp - shows on hover */}
        <div
          className={`mt-1 text-xs opacity-0 group-hover:opacity-100 transition-opacity duration-200 ${
            isUser ? 'text-blue-200' : 'text-gray-400'
          }`}
        >
          {formatTime(message.created_at)}
        </div>
      </div>
    </div>
  );
}
