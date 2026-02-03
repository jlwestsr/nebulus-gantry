import { useState, useRef, useEffect } from 'react';
import type { KeyboardEvent, ChangeEvent } from 'react';

interface MessageInputProps {
  onSend: (content: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function MessageInput({
  onSend,
  disabled = false,
  placeholder = 'Message Nebulus...',
}: MessageInputProps) {
  const [content, setContent] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea based on content
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      // Reset height to auto to get the correct scrollHeight
      textarea.style.height = 'auto';
      // Set height to scrollHeight, with min and max constraints
      const newHeight = Math.min(Math.max(textarea.scrollHeight, 44), 200);
      textarea.style.height = `${newHeight}px`;
    }
  }, [content]);

  const handleChange = (e: ChangeEvent<HTMLTextAreaElement>) => {
    setContent(e.target.value);
  };

  const handleSubmit = () => {
    const trimmed = content.trim();
    if (trimmed && !disabled) {
      onSend(trimmed);
      setContent('');
      // Reset textarea height after clearing
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Submit on Enter, allow Shift+Enter for newline
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const canSubmit = content.trim().length > 0 && !disabled;

  return (
    <div className="p-3 sm:p-4 border-t border-gray-700">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-end gap-2 sm:gap-3 bg-gray-700 rounded-xl px-3 sm:px-4 py-2.5 sm:py-3 focus-within:ring-2 focus-within:ring-blue-500/50 transition-shadow duration-200">
          <textarea
            ref={textareaRef}
            value={content}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled}
            rows={1}
            className="flex-1 bg-transparent text-gray-100 placeholder-gray-400 outline-none text-sm resize-none leading-relaxed min-h-[22px] max-h-[200px] disabled:text-gray-500 disabled:cursor-not-allowed"
            style={{ height: 'auto' }}
          />
          <button
            onClick={handleSubmit}
            disabled={!canSubmit}
            className={`p-2 rounded-lg transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500/50 ${
              canSubmit
                ? 'text-white bg-blue-600 hover:bg-blue-500 active:scale-95'
                : 'text-gray-500 cursor-not-allowed'
            }`}
            aria-label="Send message"
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
                d="M5 10l7-7m0 0l7 7m-7-7v18"
              />
            </svg>
          </button>
        </div>
        {disabled && (
          <div className="mt-2 text-center text-xs text-gray-500">
            Generating response...
          </div>
        )}
      </div>
    </div>
  );
}
