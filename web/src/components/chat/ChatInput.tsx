import { useState, useRef, type KeyboardEvent } from 'react';
import { Send, RotateCcw } from 'lucide-react';

interface Props {
  onSend: (content: string) => void;
  disabled: boolean;
}

export function ChatInput({ onSend, disabled }: Props) {
  const [input, setInput] = useState('');
  const lastMessageRef = useRef('');

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || disabled) return;
    lastMessageRef.current = trimmed;
    setInput('');
    onSend(trimmed);
  };

  const handleResend = () => {
    if (!lastMessageRef.current || disabled) return;
    onSend(lastMessageRef.current);
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="p-3 border-t border-gray-100 bg-white">
      <div className="flex gap-2 items-end">
        <textarea
          className="flex-1 resize-none rounded-xl border border-gray-200 px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-400 transition-all placeholder:text-gray-400"
          rows={1}
          placeholder="输入消息..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
        />
        <button
          className="shrink-0 w-10 h-10 rounded-xl border border-gray-200 text-gray-400 flex items-center justify-center hover:text-blue-600 hover:border-blue-300 hover:bg-blue-50 disabled:opacity-30 disabled:cursor-not-allowed transition-all duration-150"
          onClick={handleResend}
          disabled={disabled || !lastMessageRef.current}
          title="重发上一条消息"
        >
          <RotateCcw className="w-4 h-4" />
        </button>
        <button
          className="shrink-0 w-10 h-10 rounded-xl bg-blue-600 text-white flex items-center justify-center hover:bg-blue-700 disabled:opacity-30 disabled:cursor-not-allowed shadow-sm hover:shadow transition-all duration-150"
          onClick={handleSend}
          disabled={disabled || !input.trim()}
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
