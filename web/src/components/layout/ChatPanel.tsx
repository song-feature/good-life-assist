import { useRef, useState, useEffect } from 'react';
import { useChatStore } from '../../stores/chatStore';
import { useModuleStore } from '../../stores/moduleStore';
import { useStockStore } from '../../stores/stockStore';
import { MessageList } from '../chat/MessageList';
import { ChatInput } from '../chat/ChatInput';
import { Bot, Settings } from 'lucide-react';
import { Link } from 'react-router-dom';

export function ChatPanel() {
  const { messages, isStreaming, sendMessage } = useChatStore();
  const handleUICommand = useModuleStore((s) => s.handleUICommand);
  const { setPortfolio, setTrend, setOptionsChain, setAnalysis } = useStockStore();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (content: string) => {
    await sendMessage(content, (cmd) => {
      handleUICommand(cmd);
      // Also populate stock store from ui_command data
      const data = cmd.data as Record<string, unknown>;
      if (cmd.module === 'stock') {
        switch (cmd.action) {
          case 'show_portfolio':
            setPortfolio(data as any);
            break;
          case 'show_trend':
            if (data.ticker) {
              setTrend(data.ticker as string, data as any);
            }
            break;
          case 'show_options':
            setOptionsChain(data as any);
            break;
          case 'show_analysis':
            setAnalysis(data as any);
            break;
        }
      }
    });
  };

  return (
    <>
      <div className="px-4 py-3.5 border-b border-gray-100 flex items-center justify-between bg-white">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-blue-600 flex items-center justify-center shadow-sm">
            <Bot className="w-4.5 h-4.5 text-white" />
          </div>
          <h1 className="text-base font-bold text-gray-900">生活助手</h1>
        </div>
        <Link
          to="/admin"
          className="p-2 rounded-xl text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-all duration-150"
          title="系统管理"
        >
          <Settings className="w-4.5 h-4.5" />
        </Link>
      </div>
      <div className="flex-1 overflow-y-auto px-4 py-4 bg-gray-50/50">
        {messages.length === 0 && (
          <div className="text-center text-gray-400 mt-24">
            <div className="w-14 h-14 rounded-2xl bg-gray-100 flex items-center justify-center mx-auto mb-4">
              <Bot className="w-7 h-7 text-gray-300" />
            </div>
            <p className="text-sm font-medium text-gray-500">你好！我是你的生活助手</p>
            <p className="text-xs mt-1.5 text-gray-400">试试说"帮我看看我的持仓"</p>
          </div>
        )}
        <MessageList messages={messages} isStreaming={isStreaming} />
        <div ref={bottomRef} />
      </div>
      <ChatInput onSend={handleSend} disabled={isStreaming} />
    </>
  );
}
