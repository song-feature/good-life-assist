import { create } from 'zustand';
import { fetchSSE } from '../api/client';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
}

interface ChatState {
  messages: ChatMessage[];
  isStreaming: boolean;
  sendMessage: (
    content: string,
    onUICommand?: (cmd: { module: string; action: string; data: Record<string, unknown> }) => void,
  ) => Promise<void>;
  clearMessages: () => void;
}

let messageCounter = 0;
const nextId = () => `msg-${++messageCounter}-${Date.now()}`;

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  isStreaming: false,

  sendMessage: async (content, onUICommand) => {
    const userMsg: ChatMessage = {
      id: nextId(),
      role: 'user',
      content,
      timestamp: Date.now(),
    };

    const assistantId = nextId();
    const assistantMsg: ChatMessage = {
      id: assistantId,
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
    };

    set((s) => ({
      messages: [...s.messages, userMsg, assistantMsg],
      isStreaming: true,
    }));

    try {
      await fetchSSE(
        '/chat/stream',
        { message: content },
        {
          onMessage: (data) => {
            set((s) => ({
              messages: s.messages.map((m) =>
                m.id === assistantId
                  ? { ...m, content: m.content + data.content }
                  : m,
              ),
            }));
          },
          onUICommand: (cmd) => {
            onUICommand?.(cmd);
          },
          onError: (data) => {
            set((s) => ({
              messages: s.messages.map((m) =>
                m.id === assistantId
                  ? { ...m, content: m.content + `\n[错误] ${data.message}` }
                  : m,
              ),
            }));
          },
          onDone: () => {
            set({ isStreaming: false });
          },
        },
      );
    } catch (e) {
      set((s) => ({
        isStreaming: false,
        messages: s.messages.map((m) =>
          m.id === assistantId
            ? { ...m, content: `连接失败: ${e}` }
            : m,
        ),
      }));
    }
  },

  clearMessages: () => set({ messages: [] }),
}));
