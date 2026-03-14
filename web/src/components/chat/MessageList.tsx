import type { ChatMessage } from '../../stores/chatStore';
import { MessageBubble } from './MessageBubble';

interface Props {
  messages: ChatMessage[];
  isStreaming: boolean;
  progressMessage?: string;
}

export function MessageList({ messages, isStreaming, progressMessage }: Props) {
  return (
    <div className="space-y-4">
      {messages.map((msg, i) => (
        <MessageBubble
          key={msg.id}
          message={msg}
          isLast={i === messages.length - 1}
          isStreaming={isStreaming && i === messages.length - 1 && msg.role === 'assistant'}
          progressMessage={isStreaming && i === messages.length - 1 && msg.role === 'assistant' ? progressMessage : undefined}
        />
      ))}
    </div>
  );
}
