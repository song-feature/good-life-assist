import type { ChatMessage, ProgressStep } from '../../stores/chatStore';
import { MessageBubble } from './MessageBubble';

interface Props {
  messages: ChatMessage[];
  isStreaming: boolean;
  progressSteps?: ProgressStep[];
}

export function MessageList({ messages, isStreaming, progressSteps }: Props) {
  return (
    <div className="space-y-4">
      {messages.map((msg, i) => {
        const isLastAssistant = isStreaming && i === messages.length - 1 && msg.role === 'assistant';
        return (
          <MessageBubble
            key={msg.id}
            message={msg}
            isLast={i === messages.length - 1}
            isStreaming={isLastAssistant}
            progressSteps={isLastAssistant ? progressSteps : undefined}
          />
        );
      })}
    </div>
  );
}
