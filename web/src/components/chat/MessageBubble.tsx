import type { ChatMessage, ProgressStep, UsageInfo } from '../../stores/chatStore';
import { User, Bot, Loader2, Check } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface Props {
  message: ChatMessage;
  isLast: boolean;
  isStreaming: boolean;
  progressSteps?: ProgressStep[];
}

function StepList({ steps, isStreaming }: { steps: ProgressStep[]; isStreaming: boolean }) {
  return (
    <div className="space-y-1.5 py-0.5">
      {steps.map((s, i) => {
        const isLatest = i === steps.length - 1;
        const isDone = !isLatest || !isStreaming;
        return (
          <div key={i} className="flex items-center gap-2">
            {isDone ? (
              <Check className="w-3.5 h-3.5 text-green-500 shrink-0" />
            ) : (
              <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-500 shrink-0" />
            )}
            <span className={`text-xs ${isDone ? 'text-gray-400' : 'text-gray-600'}`}>
              {s.detail}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function UsageBadge({ info }: { info: UsageInfo }) {
  const tokens = info.usage;
  const hasTokens = tokens && tokens.total_tokens;
  return (
    <div className="flex items-center gap-1.5 mt-1.5 ml-1 text-[10px] text-gray-400/70">
      <span className="inline-flex items-center gap-1 bg-gray-50 rounded px-1.5 py-0.5">
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400/60" />
        {info.model}
      </span>
      {hasTokens && (
        <span className="bg-gray-50 rounded px-1.5 py-0.5 tabular-nums">
          {tokens.total_tokens} tokens
        </span>
      )}
    </div>
  );
}

export function MessageBubble({ message, isStreaming, progressSteps }: Props) {
  const isUser = message.role === 'user';
  const hasSteps = progressSteps && progressSteps.length > 0;

  const renderContent = () => {
    // No content yet — show steps or loading dots
    if (!message.content) {
      if (!isStreaming) return null;
      if (hasSteps) {
        return <StepList steps={progressSteps} isStreaming={isStreaming} />;
      }
      return (
        <div className="flex items-center gap-1 py-0.5">
          <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:0ms]" />
          <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:150ms]" />
          <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:300ms]" />
        </div>
      );
    }

    if (isUser) {
      return <span className="whitespace-pre-wrap">{message.content}</span>;
    }

    // Assistant message with content — show completed steps above if any
    return (
      <>
        {hasSteps && (
          <div className="mb-2 pb-2 border-b border-gray-100">
            <StepList steps={progressSteps} isStreaming={false} />
          </div>
        )}
        <div className="markdown-body">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {message.content}
          </ReactMarkdown>
        </div>
      </>
    );
  };

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
      <div className="max-w-[85%]">
        <div
          className={`rounded-2xl px-4 py-2.5 text-[13px] leading-[1.7] ${
            isUser
              ? 'bg-blue-600 text-white rounded-tr-sm'
              : 'bg-white text-gray-700 border border-gray-100 shadow-[0_1px_3px_rgba(0,0,0,0.04)] rounded-tl-sm'
          }`}
        >
          {renderContent()}
        </div>
        {!isUser && !isStreaming && message.usageInfo && (
          <UsageBadge info={message.usageInfo} />
        )}
      </div>
    </div>
  );
}
