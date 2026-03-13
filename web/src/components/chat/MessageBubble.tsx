import type { ChatMessage } from '../../stores/chatStore';
import { User, Bot, Loader2 } from 'lucide-react';

interface Props {
  message: ChatMessage;
  isLast: boolean;
  isStreaming: boolean;
}

export function MessageBubble({ message, isStreaming }: Props) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex gap-2.5 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      <div
        className={`shrink-0 w-8 h-8 rounded-full flex items-center justify-center shadow-sm ${
          isUser ? 'bg-blue-600' : 'bg-white border border-gray-200'
        }`}
      >
        {isUser ? (
          <User className="w-4 h-4 text-white" />
        ) : (
          <Bot className="w-4 h-4 text-gray-500" />
        )}
      </div>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-[13px] leading-[1.7] whitespace-pre-wrap ${
          isUser
            ? 'bg-blue-600 text-white rounded-tr-sm'
            : 'bg-white text-gray-700 border border-gray-100 shadow-[0_1px_3px_rgba(0,0,0,0.04)] rounded-tl-sm'
        }`}
      >
        {message.content || (isStreaming ? (
          <div className="flex items-center gap-1 py-0.5">
            <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:0ms]" />
            <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:150ms]" />
            <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:300ms]" />
          </div>
        ) : null)}
      </div>
    </div>
  );
}
